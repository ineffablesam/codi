"""Simple Coding Agent with ReAct Loop.

This is the core agent implementation following the baby-code pattern:
- Single agent with ReAct (Reason, Act, Observe) loop
- Uses Gemini 3 Flash Preview for fast, capable responses
- Streams responses in real-time via WebSocket
- Handles all coding tasks with unified prompts
- Creates implementation plans and waits for user approval

Replaces the complex multi-agent orchestration with simplicity.
"""
import asyncio
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
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
- docker_preview: Build and deploy a preview container (USE THIS FOR ALL UPDATES)
- initial_deploy: ONLY for brand new projects that have never been deployed

## CRITICAL DEPLOYMENT RULES

1. **initial_deploy** = ONLY use when the project has NEVER been deployed before (right after template creation)
2. **docker_preview** = Use for ALL subsequent deployments after code changes
3. **NEVER call initial_deploy multiple times** - it will be rejected after the first call
4. **Complete ALL code changes FIRST** - verify everything works, then deploy ONCE at the end

## How to Work

1. **FIRST - Check if deployed**: If this is a new project that needs first-time setup, call `initial_deploy` ONCE.
2. **Explore first**: Use list_files and search_files to understand the codebase.
3. **Read before writing**: Always read a file before modifying it.
4. **Make ALL changes**: Complete every task in the plan before deploying.
5. **Surgical edits are MANDATORY**: Use `edit_file` for modifications. DO NOT rewrite entire files.
6. **Test your changes**: Use run_bash to run tests or build commands.
7. **Commit your work**: Use git_commit to save your progress.
8. **DEPLOY ONCE AT THE END**: After ALL changes are complete and verified, call `docker_preview` exactly ONCE.

## Strict Workflow Order

1. Read/explore files
2. Make code changes (write_file, edit_file)
3. Test changes (run_bash)
4. Commit changes (git_commit)
5. Deploy ONCE (docker_preview) - DO NOT deploy after each file change!

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


# System prompt for the planning phase
PLANNING_SYSTEM_PROMPT = """You are Codi, an expert AI coding assistant. You are now in PLANNING MODE.

Your task is to analyze the user's request and create an implementation plan. Do NOT make any code changes yet.

## Instructions

1. **Analyze the request**: Understand what the user wants to achieve
2. **Explore the codebase**: Use list_files and read_file to understand the current structure
3. **Create a plan**: Generate a detailed implementation plan in markdown format

## Plan Format

Generate the plan in this exact markdown format:

```markdown
# Implementation Plan: [Brief Title]

## Goal
[One-line description of what will be achieved]

## Problem Analysis
[2-3 sentences explaining the current state and what needs to change]

## Proposed Changes

### [Component/File Group 1]
- **File**: `path/to/file.ext`
- **Action**: [CREATE/MODIFY/DELETE]
- **Changes**: [Brief description of changes]

### [Component/File Group 2]
...

## Tasks
1. [ ] Task 1 description
2. [ ] Task 2 description
3. [ ] ...

## Estimated Impact
- **Files affected**: [number]
- **Risk level**: [Low/Medium/High]

## Testing Plan
- [How the changes will be verified]
```

## Important Rules

- Do NOT use any write_file, edit_file, git_commit, or docker_preview tools
- ONLY use read_file, list_files, and search_files to explore the codebase
- After creating the plan, output it as your final response
- Be specific about which files will be modified and how
- Include all necessary steps in the Tasks section"""


WALKTHROUGH_SYSTEM_PROMPT = """You are Codi, an expert AI coding assistant. Generate a brief walkthrough summarizing what was accomplished.

Based on the conversation history and changes made, create a concise markdown walkthrough.

## Format

```markdown
# What Was Built

[1-2 sentence summary]

## Changes Made

- **[file1.ext]**: [Brief description]
- **[file2.ext]**: [Brief description]

## How to Test

1. [Step 1]
2. [Step 2]
```

## Rules

- Keep it VERY concise (under 200 words)
- Focus on practical next steps
- List the specific files that were modified
- Include any commands the user needs to run"""


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
        skip_planning: bool = False,
    ) -> None:
        """Initialize the coding agent.
        
        Args:
            context: Agent context with project info
            model: LLM model to use (default: gemini-3-flash-preview)
            max_iterations: Maximum ReAct loop iterations
            temperature: LLM temperature for creativity
            tech_stack: Technology stack dict (e.g., {"frontend": "nextjs", "backend": "supabase"})
            skip_planning: If True, skip planning phase and execute directly
        """
        self.context = context
        self.model = model
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.tech_stack = tech_stack or {}
        self.skip_planning = skip_planning
        
        # Initialize LLM
        self._llm = None
        
        # Conversation history for multi-turn interactions
        self.messages: List[BaseMessage] = []
        
        # WebSocket connection manager (lazy loaded)
        self._connection_manager = None
        
        # Planning state
        self._current_plan_id: Optional[int] = None
        self._plan_approved: Optional[bool] = None
        self._approval_event: Optional[asyncio.Event] = None
        
        # Memory service (lazy loaded)
        self._mem0_service = None

    @property
    def mem0_service(self):
        """Get Mem0 service (lazy load)."""
        if self._mem0_service is None:
            try:
                from app.services.memory.mem0_service import get_mem0_service
                self._mem0_service = get_mem0_service()
            except ImportError:
                logger.warning("Mem0Service not available")
                self._mem0_service = None
        return self._mem0_service

    async def _load_memories(self, user_message: str) -> str:
        """Load relevant memories for the conversation context.
        
        Args:
            user_message: Current user message to find relevant context for
            
        Returns:
            Formatted memory context string
        """
        if not self.mem0_service or not self.mem0_service.is_available:
            return ""
            
        try:
            # Generate Mem0 user ID
            mem0_user_id = f"user_{self.context.user_id}_project_{self.context.project_id}"
            
            # Get persistent context
            context = await self.mem0_service.get_session_context(
                session_id=self.context.session_id,
                user_id=mem0_user_id,
                query=user_message,
            )
            
            if context:
                logger.info("Loaded persistent memories from Mem0")
                return context
                
        except Exception as e:
            logger.warning(f"Failed to load memories: {e}")
            
        return ""

    async def _save_memory(self, content: str, memory_type: str = "task") -> None:
        """Save a new memory to Mem0.
        
        Args:
            content: Memory content
            memory_type: Type classification
        """
        if not self.mem0_service or not self.mem0_service.is_available:
            return
            
        try:
            mem0_user_id = f"user_{self.context.user_id}_project_{self.context.project_id}"
            
            await self.mem0_service.add_memory(
                content=content,
                user_id=mem0_user_id,
                session_id=self.context.session_id,
                project_id=self.context.project_id,
                memory_type=memory_type,
            )
            logger.info(f"Saved memory: {content[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")
    
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
                    pattern = tool_input.get("pattern", "")
                    display_message = f"Searching for '{pattern}'"
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
    
    async def _generate_status_message(self, context_type: str, context: str = "") -> str:
        """Generate a brief, professional status message via LLM.
        
        Args:
            context_type: Type of status (e.g., 'planning', 'approved', 'deployment')
            context: Additional context about what's happening
            
        Returns:
            A short, user-friendly status message
        """
        try:
            prompts = {
                "planning": "Generate a brief message telling the user you're analyzing their request and creating a development plan. Be confident and reassuring.",
                "approved": "Generate a brief message confirming the plan was approved and you're starting implementation. Be enthusiastic but professional.",
                "deployment": "Generate a brief message after successful deployment, mentioning the preview is ready. Be celebratory but brief.",
                "building": "Generate a brief message that you're building the application. Be reassuring about the process.",
            }
            
            base_prompt = prompts.get(context_type, f"Generate a brief status message for: {context_type}")
            
            full_prompt = f"""{base_prompt}

Context: {context if context else 'Standard development workflow'}

Rules:
- Keep it under 2 sentences
- Be specific about what you're doing
- Never use emojis
- Professional but friendly tone
- No technical jargon"""

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=settings.gemini_api_key,
                temperature=0.7,
            )
            
            response = await llm.ainvoke([HumanMessage(content=full_prompt)])
            message = response.content if isinstance(response.content, str) else str(response.content)
            
            # Clean up the message
            message = message.strip().strip('"').strip("'")
            return message
            
        except Exception as e:
            logger.warning(f"Failed to generate status message: {e}")
            # Fallback to simple messages
            fallbacks = {
                "planning": "Analyzing your request and creating a development plan...",
                "approved": "Plan approved! Starting implementation...",
                "deployment": "Deployment complete! Your preview is ready.",
                "building": "Building your application...",
            }
            return fallbacks.get(context_type, "Processing...")
    
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
    
    async def _run_planning_phase(self, user_message: str) -> Optional[str]:
        """Run the planning phase to generate an implementation plan.
        
        Args:
            user_message: The user's request
            
        Returns:
            The generated plan markdown, or None if planning failed
        """
        logger.info("Starting planning phase")
        planning_message = await self._generate_status_message("planning", user_message[:100])
        await self._broadcast_status("planning", planning_message)
        
        # Read-only tools for planning
        planning_tools = [t for t in TOOLS if t["name"] in ["read_file", "list_files", "search_files"]]
        tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in planning_tools
        ]
        
        # Initialize planning conversation
        messages: List[BaseMessage] = [
            SystemMessage(content=PLANNING_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
        
        plan_content = ""
        iteration = 0
        max_planning_iterations = 20  # Limit planning iterations
        
        while iteration < max_planning_iterations:
            iteration += 1
            
            try:
                llm_with_tools = self.llm.bind_tools(tool_schemas)
                response = await llm_with_tools.ainvoke(messages)
                messages.append(response)
                
                tool_calls = self._extract_tool_calls(response)
                
                if not tool_calls:
                    # Planning complete - extract the plan
                    if isinstance(response.content, str):
                        plan_content = response.content
                    elif isinstance(response.content, list):
                        plan_content = " ".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in response.content
                        )
                    else:
                        plan_content = str(response.content)
                    break
                
                # Execute read-only tools
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    await self._broadcast_tool_execution(
                        tool_name,
                        f"Exploring: {tool_name}",
                        tool_input=tool_args
                    )
                    
                    result = await execute_tool(tool_name, tool_args, self.context)
                    
                    messages.append(
                        ToolMessage(content=result, tool_call_id=tool_id)
                    )
                    
            except Exception as e:
                logger.error(f"Error in planning iteration {iteration}: {e}")
                messages.append(
                    HumanMessage(content=f"Error occurred: {e}. Continue with available information.")
                )
        
        if not plan_content:
            logger.warning("Planning phase produced no content")
            return None
            
        return plan_content
    
    async def _save_plan_to_file(self, plan_content: str, user_request: str) -> str:
        """Save the plan to the .codi folder in the project.
        
        Args:
            plan_content: The markdown plan content
            user_request: Original user request
            
        Returns:
            Path to the saved plan file
        """
        # Create .codi/plans directory
        codi_dir = Path(self.context.project_folder) / ".codi" / "plans"
        codi_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{timestamp}_plan.md"
        plan_path = codi_dir / filename
        
        # Write plan file
        plan_path.write_text(plan_content, encoding="utf-8")
        
        logger.info(f"Saved plan to {plan_path}")
        return str(plan_path)
    
    async def _create_plan_in_db(
        self, 
        plan_content: str, 
        user_request: str,
        plan_file_path: str
    ) -> Optional[int]:
        """Create a plan record in the database.
        
        Args:
            plan_content: The markdown plan content
            user_request: Original user request
            plan_file_path: Path where the plan file was saved
            
        Returns:
            The plan ID, or None if creation failed
        """
        try:
            from app.core.database import get_db_context
            from app.models.plan import ImplementationPlan, PlanStatus, PlanTask
            
            # Extract title from plan
            title_match = re.search(r'^#\s*(?:Implementation Plan:?\s*)?(.+)$', plan_content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else user_request[:50]
            
            # Parse tasks from plan
            tasks = self._parse_tasks_from_plan(plan_content)
            
            async with get_db_context() as session:
                plan = ImplementationPlan(
                    project_id=self.context.project_id,
                    title=title,
                    user_request=user_request,
                    markdown_content=plan_content,
                    file_path=plan_file_path,
                    status=PlanStatus.PENDING_REVIEW,
                    total_tasks=len(tasks),
                    completed_tasks=0,
                )
                session.add(plan)
                await session.flush()  # Get the plan ID
                
                # Create task records
                for idx, task_desc in enumerate(tasks):
                    task = PlanTask(
                        plan_id=plan.id,
                        category="implementation",
                        description=task_desc,
                        order_index=idx,
                        completed=False,
                    )
                    session.add(task)
                
                await session.commit()
                
                logger.info(f"Created plan in database: ID={plan.id}")
                return plan.id
                
        except Exception as e:
            logger.error(f"Failed to create plan in database: {e}")
            return None
    
    def _parse_tasks_from_plan(self, plan_content: str) -> List[str]:
        """Parse task descriptions from the plan markdown.
        
        Args:
            plan_content: The markdown plan content
            
        Returns:
            List of task descriptions
        """
        tasks = []
        
        # Look for tasks section
        tasks_section = re.search(
            r'##\s*Tasks\s*\n((?:[-*]?\s*\[[ x]\].*\n?)+)',
            plan_content,
            re.IGNORECASE | re.MULTILINE
        )
        
        if tasks_section:
            task_lines = tasks_section.group(1).strip().split('\n')
            for line in task_lines:
                # Extract task text from checkbox format
                match = re.match(r'^\s*[-*]?\s*\[[ x]\]\s*(.+)$', line.strip(), re.IGNORECASE)
                if match:
                    tasks.append(match.group(1).strip())
        
        # Also look for numbered list format (1. [ ] task)
        numbered_tasks = re.findall(
            r'^\s*\d+\.\s*\[[ x]\]\s*(.+)$',
            plan_content,
            re.MULTILINE
        )
        if numbered_tasks and not tasks:
            tasks = [t.strip() for t in numbered_tasks]
        
        return tasks
    
    def handle_approval_response(self, approved: bool) -> None:
        """Handle approval or rejection response from the frontend.
        
        Args:
            approved: True if plan was approved, False if rejected
        """
        self._plan_approved = approved
        if self._approval_event:
            self._approval_event.set()
    
    async def _wait_for_approval(self, timeout: float = 600.0) -> bool:
        """Wait for user to approve or reject the plan using Redis Pub/Sub + DB Polling.
        
        Args:
            timeout: Maximum seconds to wait for approval
            
        Returns:
            True if approved, False if rejected or timed out
        """
        if not self._current_plan_id:
            logger.warning("No plan ID to wait for approval")
            return False
            
        logger.info(f"Waiting for approval for plan {self._current_plan_id} via Redis & DB...")
        
        try:
            import redis.asyncio as aioredis
            from app.core.config import settings
            from app.core.database import get_db_context
            from app.models.plan import ImplementationPlan, PlanStatus
            from sqlalchemy import select
            
            # Connect to Redis
            redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            pubsub = redis_client.pubsub()
            channel = f"codi:project:{self.context.project_id}:signals"
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to signal channel: {channel}")
            
            start_time = asyncio.get_event_loop().time()
            last_db_poll = start_time
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                current_time = asyncio.get_event_loop().time()

                try:
                    # distinct wait with timeout for message
                    remaining = timeout - (current_time - start_time)
                    if remaining <= 0:
                        break
                        
                    # Wait for Redis message with short timeout to allow loop to rotate for DB poll
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=1.0 # Check every 1s to allow loop checks
                    )
                    
                    if message:
                        data = json.loads(message["data"])
                        signal_type = data.get("type")
                        signal_data = data.get("data", {})
                        
                        if signal_type == "plan_approval":
                            plan_id = signal_data.get("plan_id")
                            approved = signal_data.get("approved")
                            
                            if plan_id == self._current_plan_id:
                                logger.info(f"Received approval signal via Redis: {approved}")
                                await pubsub.close()
                                await redis_client.close()
                                return approved
                                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    # logger.error(f"Error processing Redis signal: {e}") # Reduce noise
                    pass
            
            await pubsub.close()
            await redis_client.close()
            
        except Exception as e:
            logger.error(f"Error in approval wait loop: {e}")
            return False
                
        logger.warning("Plan approval timed out")
        await self._broadcast_status("timeout", "Plan approval timed out. Please try again.")
        return False
    
    async def _generate_walkthrough(self, user_message: str, final_response: str) -> Optional[str]:
        """Generate a walkthrough summarizing what was accomplished.
        
        Args:
            user_message: Original user request
            final_response: The agent's final response
            
        Returns:
            Walkthrough markdown content, or None if generation failed
        """
        try:
            logger.info("Generating walkthrough")
            
            # Build context from conversation history
            context_parts = []
            for msg in self.messages[-10:]:  # Last 10 messages for context
                if hasattr(msg, 'content'):
                    if isinstance(msg.content, str):
                        context_parts.append(msg.content[:500])  # Limit each
            
            context = "\n---\n".join(context_parts)
            
            walkthrough_request = f"""User requested: {user_message}

## Conversation Context (last messages):
{context}

## Final Response:
{final_response}

Generate a brief walkthrough of what was accomplished."""

            # Use a single LLM call for efficiency
            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=1.0,
            )
            
            messages = [
                SystemMessage(content=WALKTHROUGH_SYSTEM_PROMPT),
                HumanMessage(content=walkthrough_request),
            ]
            
            response = await llm.ainvoke(messages)
            walkthrough_content = response.content if isinstance(response.content, str) else str(response.content)
            
            # Broadcast walkthrough to frontend
            if self._current_plan_id:
                await self.connection_manager.broadcast_to_project(
                    self.context.project_id,
                    {
                        "type": "walkthrough_ready",
                        "plan_id": self._current_plan_id,
                        "walkthrough_content": walkthrough_content,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            
            logger.info("Walkthrough generated successfully")
            return walkthrough_content
            
        except Exception as e:
            logger.error(f"Failed to generate walkthrough: {e}")
            return None
    
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
        
        # Load relevant memories if session_id is present
        memory_context = ""
        if self.context.session_id:
            memory_context = await self._load_memories(user_message)
            if memory_context:
                system_prompt = f"{system_prompt}\n\n{memory_context}"
        
        # Initialize conversation with system prompt and user message
        self.messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        
        # Only broadcast started status if skipping planning (otherwise planning phase handles it)
        if self.skip_planning:
            await self._broadcast_status("started", "Processing your request...")
        
        # =====================================================================
        # PLANNING PHASE: Create implementation plan and wait for approval
        # =====================================================================
        if not self.skip_planning:
            plan_content = await self._run_planning_phase(user_message)
            
            if plan_content:
                # Save plan to .codi folder
                plan_file_path = await self._save_plan_to_file(plan_content, user_message)
                
                # Create plan in database
                plan_id = await self._create_plan_in_db(plan_content, user_message, plan_file_path)
                self._current_plan_id = plan_id
                
                if plan_id:
                    # Broadcast plan_created message to frontend
                    await self.connection_manager.broadcast_to_project(
                        self.context.project_id,
                        {
                            "type": "plan_created",
                            "plan_id": plan_id,
                            "plan_markdown": plan_content,
                            "plan_file_path": plan_file_path,
                            "user_request": user_message,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    
                    await self._broadcast_status("awaiting_approval", "Plan created. Waiting for your approval...")
                    
                    # Wait for user approval
                    approved = await self._wait_for_approval()
                    
                    if not approved:
                        # User rejected or timeout
                        rejection_response = "I understand. Please let me know how you'd like me to modify the plan, or describe a different approach."
                        await self.connection_manager.broadcast_to_project(
                            self.context.project_id,
                            {
                                "type": "agent_response",
                                "message": rejection_response,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )

                        return rejection_response
                    
                    # User approved - continue to execution
                    approved_message = await self._generate_status_message("approved")
                    await self._broadcast_status("executing", approved_message)
                else:
                    logger.warning("Failed to create plan in database, proceeding with execution")
            else:
                logger.warning("Planning phase produced no content, proceeding with execution")
        
        # =====================================================================
        # EXECUTION PHASE: Execute the plan using tools
        # =====================================================================
        
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
        
        # Generate walkthrough if a plan was approved and executed
        if self._current_plan_id and self._plan_approved:
            await self._generate_walkthrough(user_message, final_response)
        
        # Send final response via WebSocket FIRST
        await self.connection_manager.broadcast_to_project(
            self.context.project_id,
            {
                "type": "agent_response",
                "message": final_response,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Save successful interaction to memory
        if self.context.session_id and not "reached the maximum number of iterations" in final_response:
            # Extract key accomplishment or summary for memory
            await self._save_memory(
                content=f"User asked: {user_message}\nAccomplished: {final_response[:200]}...",
                memory_type="task"
            )

        
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
    skip_planning: bool = False,
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
        skip_planning: If True, skip planning phase and execute directly
        
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
    
    agent = CodingAgent(context=context, tech_stack=tech_stack, skip_planning=skip_planning)
    return await agent.run(user_message)


# Global registry for active agents (needed for approval handling)
_active_agents: Dict[int, CodingAgent] = {}


def register_active_agent(project_id: int, agent: CodingAgent) -> None:
    """Register an active agent for a project."""
    _active_agents[project_id] = agent


def unregister_active_agent(project_id: int) -> None:
    """Unregister an active agent for a project."""
    _active_agents.pop(project_id, None)


def get_active_agent(project_id: int) -> Optional[CodingAgent]:
    """Get the active agent for a project."""
    return _active_agents.get(project_id)
