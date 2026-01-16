"""Simple Coding Agent with ReAct Loop.

This is the core agent implementation following the baby-code pattern:
- Single agent with ReAct (Reason, Act, Observe) loop
- Uses Gemini 3 Flash Preview for fast, capable responses
- Streams responses in real-time via WebSocket
- Handles all coding tasks with unified prompts

Replaces the complex multi-agent orchestration with simplicity.
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.tools import TOOLS, AgentContext, execute_tool
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# System prompt for the coding agent
SYSTEM_PROMPT = """You are Codi, an expert AI coding assistant that helps developers build applications solely built by Samuel Philip.

You have access to these tools:
- read_file: Read file contents (with line numbers, supports pagination)
- write_file: Create new files or overwrite existing ones
- edit_file: Make surgical edits to existing files (find and replace)
- list_files: List directory contents (supports recursive listing and patterns)
- search_files: Search for text patterns across files
- run_python: Execute Python code in a sandbox (for testing/calculations)
- run_bash: Execute shell commands (for builds, tests, git operations)
- git_commit: Commit changes to the local Git repository
- docker_preview: Build and deploy a preview container
- initial_deploy: Run initial npm install and Docker build (CRITICAL for new projects)

## How to Work

1. **Start right**: If this is a new project or you just pushed a starter template, YOU MUST run `initial_deploy` FIRST. This installs dependencies and verify the build.
2. **Explore first**: Use list_files and search_files to understand the codebase.
2. **Read before writing**: Always read a file before modifying it. Use the line numbers provided to reference specific sections.
3. **Surgical edits are MANDATORY**: Use `edit_file` for all modifications to existing files. DO NOT rewrite entire files with `write_file` unless you are creating a new file or the change is so extensive that `edit_file` is impractical (more than 80% of the file changing). Rewriting entire files for minor changes is a waste of resources and makes reviewing difficult.
4. **Test your changes**: Use run_bash to run tests or build commands.
5. **Commit your work**: Use git_commit to save your progress after meaningful changes.
6. **Always verify with a preview**: Before finishing, you MUST call docker_preview to ensure your changes are deployed and visible to the user at their preview URL. This is mandatory for any UI or application logic changes.

## Best Practices

- Keep changes minimal and focused
- Follow the existing code style and patterns
- Add helpful comments when writing new code
- Handle errors gracefully
- Explain what you're doing and why

## Supported Frameworks

You can work with any framework, including:
- Flutter/Dart (mobile and web apps)
- Next.js/React (web applications)
- React Native (cross-platform mobile)
- Python/FastAPI (backend services)
- And any other framework in the codebase

When generating code:
- Match the existing code style
- Use proper imports
- Follow framework best practices
- Create complete, working implementations"""


class CodingAgent:
    """Simple coding agent with ReAct loop.
    
    This replaces all the complex multi-agent orchestration with a single
    powerful agent that can handle any coding task.
    """
    
    def __init__(
        self,
        context: AgentContext,
        model: str = "gemini-3-flash-preview",
        max_iterations: int = 50,
        temperature: float = 1.0,
        tech_stack: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize the coding agent.
        
        Args:
            context: Agent context with project info
            model: LLM model to use (default: gemini-3-flash-preview)
            max_iterations: Maximum ReAct loop iterations
            temperature: LLM temperature for creativity
            tech_stack: Technology stack dict (e.g., {"frontend": "nextjs", "backend": "supabase"})
        """
        self.context = context
        self.model = model
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.tech_stack = tech_stack or {}
        
        # Initialize LLM
        self._llm = None
        
        # Conversation history for multi-turn interactions
        self.messages: List[BaseMessage] = []
        
        # WebSocket connection manager (lazy loaded)
        self._connection_manager = None
    
    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Get LLM instance (lazy initialization)."""
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=settings.gemini_api_key,
                temperature=self.temperature,
                convert_system_message_to_human=False,
            )
        return self._llm
    
    @property
    def connection_manager(self):
        """Get WebSocket connection manager (lazy load)."""
        if self._connection_manager is None:
            from app.api.websocket.connection_manager import connection_manager
            self._connection_manager = connection_manager
        return self._connection_manager
    
    async def _broadcast_status(self, status: str, message: str, details: Optional[Dict] = None) -> None:
        """Send status update via WebSocket."""
        try:
            await self.connection_manager.broadcast_to_project(
                self.context.project_id,
                {
                    "type": "agent_status",
                    "agent": "codi",
                    "status": status,
                    "message": message,
                    "details": details or {},
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast status: {e}")
    
    async def _broadcast_tool_execution(self, tool_name: str, message: str, tool_input: Optional[Dict] = None) -> None:
        """Send tool execution update via WebSocket."""
        try:
            # Generate a more descriptive message if possible
            display_message = message
            if tool_input:
                if tool_name == "read_file":
                    path = tool_input.get("path", "file")
                    display_message = f"Reading {path}"
                elif tool_name == "write_file":
                    path = tool_input.get("path", "file")
                    display_message = f"Writing to {path}"
                elif tool_name == "edit_file":
                    path = tool_input.get("path", "file")
                    display_message = f"Editing {path}"
                elif tool_name == "list_files":
                    path = tool_input.get("path", ".")
                    display_message = f"Listing files in {path}"
                elif tool_name == "search_files":
                    query = tool_input.get("query", "")
                    display_message = f"Searching for '{query}'"
                elif tool_name == "run_bash":
                    command = tool_input.get("command", "")
                    display_message = f"Running command: {command[:50]}..."
                elif tool_name == "run_python":
                    display_message = "Executing Python code"
                elif tool_name == "git_commit":
                    display_message = "Committing changes"
                elif tool_name == "docker_preview":
                    display_message = "Deploying preview container"

            await self.connection_manager.broadcast_to_project(
                self.context.project_id,
                {
                    "type": "tool_execution",
                    "agent": "codi",
                    "tool": tool_name,
                    "message": display_message,
                    "input": tool_input or {},
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast tool execution: {e}")

    async def _broadcast_tool_result(self, tool_name: str, result: str) -> None:
        """Send tool result update via WebSocket."""
        try:
            # Truncate result for broadcast
            display_result = result[:5000] + "..." if len(result) > 5000 else result
            
            await self.connection_manager.broadcast_to_project(
                self.context.project_id,
                {
                    "type": "tool_result",
                    "agent": "codi",
                    "tool": tool_name,
                    "result": display_result,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast tool result: {e}")
    
    def _extract_tool_calls(self, response: AIMessage) -> List[Dict[str, Any]]:
        """Extract tool calls from AI response.
        
        Args:
            response: AI message response
            
        Returns:
            List of tool call dicts with id, name, and args
        """
        tool_calls = []
        
        # Handle tool_calls attribute (standard LangChain format)
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append({
                    "id": tc.get("id", f"call_{len(tool_calls)}"),
                    "name": tc.get("name"),
                    "args": tc.get("args", {}),
                })
        
        # Handle additional_kwargs format
        elif hasattr(response, 'additional_kwargs'):
            kwargs = response.additional_kwargs
            if 'tool_calls' in kwargs:
                for tc in kwargs['tool_calls']:
                    tool_calls.append({
                        "id": tc.get("id", f"call_{len(tool_calls)}"),
                        "name": tc.get("function", {}).get("name"),
                        "args": json.loads(tc.get("function", {}).get("arguments", "{}")),
                    })
        
        return tool_calls
    
    async def run(self, user_message: str) -> str:
        """Run the agent with a user message using the ReAct loop.
        
        This is the main entry point that implements:
        Reason → Act → Observe → Repeat until done
        
        Args:
            user_message: The user's request
            
        Returns:
            Final response text
        """
        logger.info(f"Starting agent run for project {self.context.project_id}")
        
        # Build system prompt with knowledge pack context
        system_prompt = SYSTEM_PROMPT
        
        if self.tech_stack:
            try:
                from app.knowledge_packs.service import KnowledgePackService
                
                # Get knowledge pack context for this tech stack
                pack_context = KnowledgePackService.get_context_for_stack(
                    self.tech_stack,
                    include_examples=False,  # Keep context lightweight
                    include_pitfalls=True,   # Critical for avoiding mistakes
                )
                
                if pack_context:
                    system_prompt = f"{SYSTEM_PROMPT}\n\n# TECHNOLOGY-SPECIFIC GUIDANCE\n\n{pack_context}"
                    logger.info(f"Loaded knowledge packs for: {self.tech_stack}")
            except Exception as e:
                logger.warning(f"Failed to load knowledge packs: {e}")
                # Continue with base prompt
        
        # Initialize conversation with system prompt and user message
        self.messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        
        await self._broadcast_status("started", "Processing your request...")
        
        iteration = 0
        final_response = ""
        
        # Convert tools to LangChain format
        tool_schemas = self._convert_tools_to_langchain_format()
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"ReAct iteration {iteration}")
            
            try:
                # Call LLM with tools
                llm_with_tools = self.llm.bind_tools(tool_schemas)
                
                response = await llm_with_tools.ainvoke(self.messages)
                
                logger.info(f"LLM Response Raw: {response}")
                logger.info(f"LLM Content: {response.content}")
                logger.info(f"LLM Tool Calls: {getattr(response, 'tool_calls', 'N/A')}")
                
                # Add response to conversation
                self.messages.append(response)
                
                # Extract tool calls
                tool_calls = self._extract_tool_calls(response)
                
                if not tool_calls:
                    # No tool calls - agent is done, extract final response
                    if isinstance(response.content, str):
                        final_response = response.content
                    elif isinstance(response.content, list):
                        # Join text parts
                        final_response = " ".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in response.content
                        )
                    else:
                        final_response = str(response.content)
                    
                    logger.info(f"Agent completed after {iteration} iterations")
                    break
                
                # Execute tools (Act)
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    logger.info(f"Executing tool: {tool_name}")
                    await self._broadcast_tool_execution(
                        tool_name, 
                        f"Executing {tool_name}...",
                        tool_input=tool_args
                    )
                    
                    # Execute the tool
                    result = await execute_tool(tool_name, tool_args, self.context)
                    
                    # Broadcast result
                    await self._broadcast_tool_result(tool_name, result)
                    
                    # Add tool result to conversation (Observe)
                    self.messages.append(
                        ToolMessage(content=result, tool_call_id=tool_id)
                    )
                    
                    # Log result preview
                    preview = result[:200] + "..." if len(result) > 200 else result
                    logger.debug(f"Tool {tool_name} result: {preview}")
                
            except Exception as e:
                error_msg = f"Error in iteration {iteration}: {e}"
                logger.error(error_msg)
                await self._broadcast_status("error", error_msg)
                
                # Add error as tool result so agent can recover
                self.messages.append(
                    HumanMessage(content=f"An error occurred: {e}. Please try a different approach.")
                )
        
        if iteration >= self.max_iterations:
            logger.warning(f"Agent reached max iterations ({self.max_iterations})")
            final_response = "I've reached the maximum number of iterations. Here's what I've accomplished so far."
        
        # Send final response via WebSocket FIRST
        await self.connection_manager.broadcast_to_project(
            self.context.project_id,
            {
                "type": "agent_response",
                "message": final_response,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        
        await self._broadcast_status("completed", "Task completed!")
        
        return final_response
    
    def _convert_tools_to_langchain_format(self) -> List[Dict[str, Any]]:
        """Convert our tool definitions to LangChain format."""
        langchain_tools = []
        
        for tool in TOOLS:
            langchain_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })
        
        return langchain_tools


async def run_agent(
    user_message: str,
    project_id: int,
    user_id: int,
    project_folder: str,
    project_slug: Optional[str] = None,
    framework: Optional[str] = None,
    task_id: Optional[str] = None,
    tech_stack: Optional[Dict[str, str]] = None,
) -> str:
    """Convenience function to run the coding agent.
    
    Args:
        user_message: User's request message
        project_id: Project ID
        user_id: User ID
        project_folder: Path to project folder
        project_slug: Project slug for container naming
        framework: Detected framework (optional)
        task_id: Task ID for tracking
        tech_stack: Technology stack dict (e.g., {"frontend": "nextjs", "backend": "supabase"})
        
    Returns:
        Agent's final response
    """
    context = AgentContext(
        project_id=project_id,
        user_id=user_id,
        project_folder=project_folder,
        project_slug=project_slug,
        framework=framework,
        task_id=task_id,
    )
    
    agent = CodingAgent(context=context, tech_stack=tech_stack)
    return await agent.run(user_message)
