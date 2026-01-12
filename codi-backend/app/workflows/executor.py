"""Workflow executor for running the agent graph."""
import re
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.base import AgentContext
from app.core.config import settings
from app.core.database import get_db_context
from app.models.project import Project
from app.models.agent_task import AgentTask
from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager
from app.workflows.graph import create_workflow_graph
from app.workflows.state import WorkflowState, create_initial_state

logger = get_logger(__name__)


async def classify_message_intent(message: str) -> str:
    """Production-grade LLM-based intent classifier.
    
    Uses Gemini Flash to accurately classify user messages into:
    - 'conversational': Greetings, questions about capabilities, casual chat
    - 'task': Implementation requests, code modifications, feature additions
    - 'clarification': Ambiguous requests that need more information
    
    This is robust, context-aware, and handles edge cases better than regex.
    
    Args:
        message: User's message to classify
        
    Returns:
        One of: 'conversational', 'task', 'clarification'
    """
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,  # Fast classification
        google_api_key=settings.gemini_api_key,
        temperature=0.1,  # Low temperature for consistent classification
        convert_system_message_to_human=False,
    )
    
    classifier_prompt = """You are an intent classifier for a development assistant chatbot.

Your job is to classify user messages into ONE of these categories:

1. **conversational** - Use for:
   - Greetings: "Hi", "Hello", "Hey there"
   - Questions about capabilities: "What can you do?", "How do you work?"
   - General questions: "What's Next.js?", "How do React hooks work?"
   - Chitchat: "Thanks", "Goodbye", "You're awesome"
   - Help requests: "Help me understand X", "Can you explain Y?"

2. **task** - Use for:
   - Implementation: "Add a login page", "Create a button", "Build a feature"
   - Modifications: "Change the title to X", "Update the color", "Fix the bug"
   - Code requests: "Generate a function", "Write code for X"
   - File operations: "Create file X", "Edit file Y"
   - Any request that requires modifying code or files

3. **clarification** - Use for:
   - Vague requests: "Make it better", "Fix it", "Change stuff"
   - Ambiguous: "Do something with the homepage"
   - Missing context: "Add that feature we discussed"

**Rules:**
- If unsure between conversational and task, choose task (safer default)
- Short messages like "Hi" are always conversational
- Any mention of specific files, code, or features = task
- Questions about "how to code X" without asking for implementation = conversational

Respond with ONLY ONE WORD: conversational, task, or clarification"""
    
    messages = [
        SystemMessage(content=classifier_prompt),
        HumanMessage(content=f"Classify this message:\n\n{message}"),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        
        # Extract content - handle both string and list responses
        if isinstance(response.content, list):
            # If content is a list, join all text parts
            content_str = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in response.content
            )
        else:
            content_str = str(response.content)
        
        intent = content_str.strip().lower()
        
        # Validate response
        if intent not in ['conversational', 'task', 'clarification']:
            logger.warning(f"Invalid intent '{intent}', defaulting to 'task'")
            return 'task'
        
        logger.info(f"Classified message as: {intent}")
        return intent
        
    except Exception as e:
        logger.error(f"Intent classification failed: {e}, defaulting to 'task'")
        # Safe default: treat as task to avoid missing actual work requests
        return 'task'


class WorkflowExecutor:
    """Executor for running the agent workflow graph."""

    def __init__(
        self,
        project_id: int,
        user_id: int,
        task_id: str,
        project_folder: str | None = None,
    ) -> None:
        """Initialize the workflow executor.

        Args:
            project_id: Project ID
            user_id: User ID
            task_id: Unique task identifier
            project_folder: Local path to project repository
        """
        self.project_id = project_id
        self.user_id = user_id
        self.task_id = task_id
        self.project_folder = project_folder
        self._graph = None
        self._current_branch: str = "main"
        self._framework: str | None = None

    async def _load_project_info(self) -> None:
        """Load project information from database."""
        async with get_db_context() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Project).where(Project.id == self.project_id)
            )
            project = result.scalar_one_or_none()

            if project:
                self.project_folder = project.local_path
                self._current_branch = project.git_branch or "main"
                self._framework = project.framework

    def _patch_agent_context(self, state: WorkflowState) -> None:
        """Patch agent context with project folder.

        Args:
            state: Current workflow state
        """
        # Agents access project folder through context
        pass

    async def _handle_conversational(self, message: str) -> Dict[str, Any]:
        """Handle conversational messages with simple LLM response.
        
        Args:
            message: User's conversational message
            
        Returns:
            Dict with conversational response
        """
        logger.info(f"Handling conversational message: {message[:50]}...")
        
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=1.0,
            convert_system_message_to_human=False,
        )
        
        system_prompt = """You are Codi, a friendly AI development assistant for the Codi platform.

You help developers build applications by:
- Generating code for Flutter, Next.js, React, React Native
- Modifying existing code files in local project repositories  
- Reviewing code quality
- Committing changes to local Git automatically

Capabilities:
- Multi-framework support (Flutter, Next.js, React, React Native)
- Local Git integration for seamless code management
- Intelligent code generation using specialized AI agents
- Real-time collaboration and updates
- Docker-based deployment and preview

For casual conversation:
- Be friendly, helpful, and concise
- Answer questions about your capabilities
- Offer to help with coding tasks when appropriate
- Keep responses brief (2-3 sentences)

When users want to build something, acknowledge and let them know you're ready to help!"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message),
        ]
        
        try:
            response = await llm.ainvoke(messages)
            
            # Extract text content - handle both string and list responses
            if isinstance(response.content, list):
                # If content is a list, join all text parts
                response_text = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in response.content
                )
            else:
                response_text = str(response.content)
            
            # Send response via WebSocket
            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "conversational_response",
                    "message": response_text,  # Now guaranteed to be a string
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            
            logger.info(f"Sent conversational response: {response_text[:50]}...")
            
            return {
                "type": "conversational",
                "response": response_text,
                "is_complete": True,
                "has_error": False,
            }
        except Exception as e:
            logger.error(f"Conversational handler failed: {e}")
            fallback_response = "Hi! I'm Codi, your AI development assistant. I can help you build apps with Flutter, Next.js, React, and React Native. What would you like to create?"
            
            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "conversational_response",
                    "message": fallback_response,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            
            return {
                "type": "conversational",
                "response": fallback_response,
                "is_complete": True,
                "has_error": False,
            }

    async def _handle_clarification_needed(self, message: str) -> Dict[str, Any]:
        """Handle ambiguous messages that need clarification.
        
        Args:
            message: User's ambiguous message
            
        Returns:
            Dict with clarification request
        """
        logger.info(f"Requesting clarification for: {message[:50]}...")
        
        clarification_message = f"""I'd be happy to help with that! To give you the best solution, could you provide a bit more detail?

Your request: "{message}"

Please specify:
- What specific feature or component should I work on?
- Which file(s) should I modify? (if you know)
- Any specific requirements or constraints?

The more details you provide, the better I can help! 🎯"""
        
        await connection_manager.broadcast_to_project(
            self.project_id,
            {
                "type": "conversational_response",
                "message": clarification_message,
                "timestamp": datetime.utcnow().isoformat(),
                "needs_clarification": True,
            },
        )
        
        return {
            "type": "clarification",
            "response": clarification_message,
            "is_complete": True,
            "has_error": False,
        }

    @property
    def graph(self):
        """Get or create the workflow graph."""
        if self._graph is None:
            graph_builder = create_workflow_graph()
            self._graph = graph_builder.compile()
        return self._graph

    async def execute(self, user_message: str) -> Dict[str, Any]:
        """Execute the workflow for a user message.

        Args:
            user_message: The user's request message

        Returns:
            Final workflow state as dictionary
        """
        start_time = datetime.utcnow()

        # Load project info
        await self._load_project_info()

        # Classify message intent using LLM (production-grade)
        intent = await classify_message_intent(user_message)
        
        if intent == 'conversational':
            logger.info("Detected conversational message, bypassing workflow")
            return await self._handle_conversational(user_message)
        
        elif intent == 'clarification':
            logger.info("Message needs clarification, sending clarification request")
            return await self._handle_clarification_needed(user_message)

        # intent == 'task' → Continue with normal workflow
        logger.info("Detected task message, executing full workflow")

        # Create initial state
        initial_state = create_initial_state(
            project_id=self.project_id,
            user_id=self.user_id,
            task_id=self.task_id,
            user_message=user_message,
            project_folder=self.project_folder,
            current_branch=self._current_branch,
            detected_framework=self._framework,
        )

        logger.info(
            f"Starting workflow execution",
            task_id=self.task_id,
            project_id=self.project_id,
            framework=self._framework,
            user_message=user_message[:100],
        )

        # Notify start
        await connection_manager.broadcast_to_project(
            self.project_id,
            {
                "type": "agent_status",
                "agent": "system",
                "status": "started",
                "message": "Processing your request...",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Update task status in DB
        async with get_db_context() as session:
            from sqlalchemy import update
            await session.execute(
                update(AgentTask)
                .where(AgentTask.id == self.task_id)
                .values(status="processing", started_at=datetime.utcnow())
            )
            await session.commit()

        try:
            # Run the graph
            # Note: Agents access project_folder through AgentContext
            # into each agent. This is done through AgentContext in the node functions.
            final_state = await self.graph.ainvoke(
                initial_state,
                {"recursion_limit": 50},
            )

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Workflow completed",
                task_id=self.task_id,
                duration_seconds=duration,
                has_error=final_state.get("has_error", False),
            )

            # Update task status in DB
            async with get_db_context() as session:
                from sqlalchemy import update
                status = "completed" if not final_state.get("has_error") else "failed"
                error_msg = final_state.get("error_message") if final_state.get("has_error") else None
                
                await session.execute(
                    update(AgentTask)
                    .where(AgentTask.id == self.task_id)
                    .values(
                        status=status,
                        completed_at=datetime.utcnow(),
                        error=error_msg,
                        result=dict(final_state) if not final_state.get("has_error") else None
                    )
                )
                await session.commit()

            return dict(final_state)

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            # Update task status in DB on failure
            async with get_db_context() as session:
                from sqlalchemy import update
                await session.execute(
                    update(AgentTask)
                    .where(AgentTask.id == self.task_id)
                    .values(
                        status="failed",
                        completed_at=datetime.utcnow(),
                        error=str(e)
                    )
                )
                await session.commit()

            raise

    async def execute_step(
        self,
        state: WorkflowState,
        agent_name: str,
    ) -> WorkflowState:
        """Execute a single step in the workflow.

        This is useful for manual step-by-step execution.

        Args:
            state: Current workflow state
            agent_name: Name of the agent to run

        Returns:
            Updated workflow state
        """
        from app.workflows.graph import (
            planner_node,
            flutter_engineer_node,
            code_reviewer_node,
            git_operator_node,
            build_deploy_node,
            memory_node,
        )

        agents = {
            "planner": planner_node,
            "flutter_engineer": flutter_engineer_node,
            "code_reviewer": code_reviewer_node,
            "git_operator": git_operator_node,
            "build_deploy": build_deploy_node,
            "memory": memory_node,
        }

        if agent_name not in agents:
            raise ValueError(f"Unknown agent: {agent_name}")

        node_func = agents[agent_name]
        return await node_func(state)


async def run_workflow(
    project_id: int,
    user_id: int,
    task_id: str,
    user_message: str,
    project_folder: str | None = None,
) -> Dict[str, Any]:
    """Convenience function to run a workflow.

    Args:
        project_id: Project ID
        user_id: User ID
        task_id: Unique task identifier
        user_message: The user's request message
        project_folder: Local path to project repository

    Returns:
        Final workflow state
    """
    executor = WorkflowExecutor(
        project_id=project_id,
        user_id=user_id,
        task_id=task_id,
        project_folder=project_folder,
    )

    return await executor.execute(user_message)
