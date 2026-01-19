"""Simplified Workflow Executor.

Replaces the complex LangGraph-based executor with a simple agent invocation.
Uses the new baby-code style CodingAgent for all tasks.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.agent import CodingAgent
from app.agent.tools import AgentContext
from app.core.config import settings
from app.core.database import get_db_context
from app.models.project import Project
from app.models.agent_task import AgentTask
from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager
from app.utils.serialization import sanitize_for_json

logger = get_logger(__name__)


async def classify_message_intent(message: str) -> str:
    """Classify user message intent using LLM.
    
    Uses Gemini Flash to classify messages into:
    - 'conversational': Greetings, questions about capabilities, casual chat
    - 'task': Implementation requests, code modifications, feature additions
    - 'clarification': Ambiguous requests that need more information
    
    Args:
        message: User's message to classify
        
    Returns:
        One of: 'conversational', 'task', 'clarification'
    """
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,
        convert_system_message_to_human=False,
    )
    
    classifier_prompt = """You are an intent classifier for a development assistant chatbot.

Classify user messages into ONE of these categories:

1. **conversational** - Greetings, questions about capabilities, general questions, chitchat
2. **task** - Implementation requests, code modifications, file operations, builds
3. **clarification** - Vague or ambiguous requests that need more detail

Rules:
- If unsure between conversational and task, choose task (safer default)
- Short messages like "Hi" are always conversational
- Any mention of specific files, code, or features = task

Respond with ONLY ONE WORD: conversational, task, or clarification"""
    
    messages = [
        SystemMessage(content=classifier_prompt),
        HumanMessage(content=f"Classify this message:\n\n{message}"),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        
        if isinstance(response.content, list):
            content_str = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in response.content
            )
        else:
            content_str = str(response.content)
        
        intent = content_str.strip().lower()
        
        if intent not in ['conversational', 'task', 'clarification']:
            logger.warning(f"Invalid intent '{intent}', defaulting to 'task'")
            return 'task'
        
        logger.info(f"Classified message as: {intent}")
        return intent
        
    except Exception as e:
        logger.error(f"Intent classification failed: {e}, defaulting to 'task'")
        return 'task'


class WorkflowExecutor:
    """Simplified executor using the baby-code style agent."""

    def __init__(
        self,
        project_id: int,
        user_id: int,
        task_id: str,
        project_folder: Optional[str] = None,
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
        self._project_slug: Optional[str] = None
        self._current_branch: str = "main"
        self._framework: Optional[str] = None

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
                
                # Build tech stack for knowledge packs
                self._tech_stack = {}
                if project.framework:
                    self._tech_stack["frontend"] = project.framework
                if project.backend_type:
                    self._tech_stack["backend"] = project.backend_type
                if project.deployment_platform:
                    self._tech_stack["deployment"] = project.deployment_platform
                
                import os
                if self.project_folder:
                    self._project_slug = os.path.basename(self.project_folder)
                else:
                    self._project_slug = None

    async def _handle_conversational(self, message: str) -> Dict[str, Any]:
        """Handle conversational messages with simple LLM response."""
        logger.info(f"Handling conversational message: {message[:50]}...")
        
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=1.0,
            convert_system_message_to_human=False,
        )
        
        system_prompt = """You are Codi, a friendly AI development assistant.

You help developers build applications by:
- Generating code for Flutter, Next.js, React, React Native
- Modifying existing code files
- Running tests and builds
- Deploying Docker previews

For casual conversation:
- Be friendly, helpful, and concise
- Answer questions about your capabilities
- Keep responses brief (2-3 sentences)"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message),
        ]
        
        try:
            response = await llm.ainvoke(messages)
            
            if isinstance(response.content, list):
                response_text = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in response.content
                )
            else:
                response_text = str(response.content)
            
            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "conversational_response",
                    "message": response_text,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            
            return {
                "type": "conversational",
                "response": response_text,
                "is_complete": True,
                "has_error": False,
            }
        except Exception as e:
            logger.error(f"Conversational handler failed: {e}")
            fallback_response = "Hi! I'm Codi, your AI development assistant. I can help you build apps. What would you like to create?"
            
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
        """Handle ambiguous messages that need clarification."""
        logger.info(f"Requesting clarification for: {message[:50]}...")
        
        clarification_message = f"""I'd be happy to help! Could you provide more detail?

Your request: "{message}"

Please specify:
- What specific feature or component should I work on?
- Which file(s) should I modify?
- Any specific requirements?"""
        
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

    async def _is_initial_project_setup(self, user_message: str) -> bool:
        """Check if this is an initial project setup that should skip planning.
        
        Initial project setup includes:
        - First message after project creation (starter template deployment)
        - Messages that are clearly about initial setup/building from template
        
        Args:
            user_message: The user's request message
            
        Returns:
            True if planning should be skipped, False otherwise
        """
        import os
        
        # Check if project folder has minimal files (just created from template)
        if self.project_folder and os.path.exists(self.project_folder):
            # Count non-hidden files/folders in root
            try:
                root_items = [f for f in os.listdir(self.project_folder) if not f.startswith('.')]
                
                # Check for "fresh project" indicators:
                # - Only has template files like package.json, next.config, etc.
                # - No src modifications yet (very few total files)
                
                # Count total files in src/app if it exists
                src_path = os.path.join(self.project_folder, "src", "app")
                if os.path.exists(src_path):
                    src_files = os.listdir(src_path)
                    # Fresh Next.js has ~3-5 files in src/app
                    if len(src_files) <= 6:
                        logger.info(f"Detected fresh project (src/app has {len(src_files)} files)")
                        return True
                
                # Alternative: Check for no agent task history yet
                async with get_db_context() as session:
                    from sqlalchemy import select, func
                    result = await session.execute(
                        select(func.count(AgentTask.id))
                        .where(AgentTask.project_id == self.project_id)
                        .where(AgentTask.status == "completed")
                    )
                    completed_tasks = result.scalar() or 0
                    
                    if completed_tasks == 0:
                        logger.info(f"First task for project {self.project_id}, skipping planning")
                        return True
                        
            except Exception as e:
                logger.warning(f"Error checking project setup state: {e}")
        
        return False

    async def execute(self, user_message: str) -> Dict[str, Any]:
        """Execute the workflow for a user message.

        Args:
            user_message: The user's request message

        Returns:
            Result dictionary
        """
        start_time = datetime.utcnow()

        # Load project info
        await self._load_project_info()

        # Classify message intent
        intent = await classify_message_intent(user_message)
        
        if intent == 'conversational':
            logger.info("Detected conversational message, bypassing agent")
            return await self._handle_conversational(user_message)
        
        elif intent == 'clarification':
            logger.info("Message needs clarification")
            return await self._handle_clarification_needed(user_message)

        # intent == 'task' → Run the coding agent
        logger.info("Detected task message, running coding agent")

        # Notify start
        await connection_manager.broadcast_to_project(
            self.project_id,
            {
                "type": "agent_status",
                "agent": "codi",
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
            # Create agent context
            context = AgentContext(
                project_id=self.project_id,
                user_id=self.user_id,
                project_folder=self.project_folder,
                project_slug=self._project_slug,
                current_branch=self._current_branch,
                framework=self._framework,
                task_id=self.task_id,
            )
            
            # Check if this is initial project setup (skip planning for starter templates)
            skip_planning = await self._is_initial_project_setup(user_message)
            if skip_planning:
                logger.info(f"Skipping planning phase for initial project setup", task_id=self.task_id)
            
            # Run the simple coding agent with tech stack for knowledge packs
            tech_stack = getattr(self, "_tech_stack", {})
            agent = CodingAgent(context=context, tech_stack=tech_stack, skip_planning=skip_planning)
            
            # Register agent for approval signal handling
            from app.agent.agent import register_active_agent, unregister_active_agent
            register_active_agent(self.project_id, agent)
            
            if tech_stack:
                logger.info(
                    f"Loaded knowledge packs for tech stack",
                    tech_stack=tech_stack,
                    task_id=self.task_id,
                )
            
            try:
                response = await agent.run(user_message)
            finally:
                # Always unregister the agent when done
                unregister_active_agent(self.project_id)

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Agent completed",
                task_id=self.task_id,
                duration_seconds=duration,
            )

            # Update task status in DB
            async with get_db_context() as session:
                from sqlalchemy import update
                await session.execute(
                    update(AgentTask)
                    .where(AgentTask.id == self.task_id)
                    .values(
                        status="completed",
                        completed_at=datetime.utcnow(),
                        result=sanitize_for_json({"response": response})
                    )
                )
                await session.commit()

            return {
                "type": "task",
                "response": response,
                "is_complete": True,
                "has_error": False,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")

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

            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "agent_status",
                    "agent": "codi",
                    "status": "failed",
                    "message": f"Error: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            return {
                "type": "task",
                "response": f"An error occurred: {e}",
                "is_complete": True,
                "has_error": True,
                "error": str(e),
            }


async def run_workflow(
    project_id: int,
    user_id: int,
    task_id: str,
    user_message: str,
    project_folder: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function to run a workflow.

    Args:
        project_id: Project ID
        user_id: User ID
        task_id: Unique task identifier
        user_message: The user's request message
        project_folder: Local path to project repository

    Returns:
        Result dictionary
    """
    executor = WorkflowExecutor(
        project_id=project_id,
        user_id=user_id,
        task_id=task_id,
        project_folder=project_folder,
    )

    return await executor.execute(user_message)
