"""Base agent class for all LangGraph agents."""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel

from app.core.config import settings
from app.services.infrastructure.git import LocalGitService, get_git_service
from app.services.infrastructure.docker import DockerService, get_docker_service
from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


class AgentContext(BaseModel):
    """Context passed to agents during execution."""

    project_id: int
    user_id: int
    project_folder: Optional[str] = None  # Local path: /var/codi/repos/user_id/project_slug
    current_branch: str = "main"
    task_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """Base class for all agents in the system.

    Each agent has:
    - A unique name and system prompt
    - Access to its designated LLM (multi-model support)
    - Tools specific to its role
    - WebSocket broadcasting capabilities
    - Memory logging integration
    """

    # Agent identity
    name: str = "base_agent"
    description: str = "Base agent"

    # Default system prompt (override in subclasses)
    system_prompt: str = "You are a helpful AI assistant."
    
    # Model configuration (override in subclasses for multi-model)
    model_provider: str = "gemini"  # "openai", "anthropic", "gemini"
    model_name: str = ""  # Leave empty to use default from config
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0

    def __init__(self, context: AgentContext) -> None:
        """Initialize the agent.

        Args:
            context: Agent context with project info and credentials
        """
        self.context = context
        self._llm: Optional[BaseChatModel] = None
        self._git_service: Optional[LocalGitService] = None
        self._docker_service: Optional[DockerService] = None
        self._tools: Optional[List[BaseTool]] = None
        self._start_time: Optional[datetime] = None

    @property
    def llm(self) -> BaseChatModel:
        """Get the LLM instance (lazy initialization with multi-model support)."""
        if self._llm is None:
            from app.agents.llm_providers import get_llm_for_agent, get_llm
            
            # Use agent-specific configuration if force_gemini is off
            if settings.force_gemini_overall:
                # Force Gemini for all agents
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                api_key = settings.gemini_api_key
                if not api_key:
                    logger.error("GEMINI_API_KEY is not set")
                    raise ValueError(
                        "GEMINI_API_KEY is missing. Please add it to your .env file."
                    )
                
                self._llm = ChatGoogleGenerativeAI(
                    model=settings.gemini_model,
                    google_api_key=api_key,
                    temperature=1.0,
                    max_output_tokens=8192,
                    streaming=False,
                    # Critical for Gemini 3 function calling with thought signatures
                    convert_system_message_to_human=False,
                )
            else:
                # Use multi-model configuration
                if self.model_provider and self.model_name:
                    self._llm = get_llm(
                        provider=self.model_provider,
                        model_name=self.model_name,
                        temperature=1.0,
                    )
                else:
                    self._llm = get_llm_for_agent(self.name)
                    
            logger.info(f"Initialized LLM for {self.name}: {self._llm.__class__.__name__}")
        
        return self._llm

    @property
    def git_service(self) -> LocalGitService:
        """Get the local Git service instance (lazy initialization)."""
        if self._git_service is None:
            if self.context.project_folder:
                self._git_service = get_git_service(self.context.project_folder)
            else:
                self._git_service = get_git_service()
        return self._git_service

    @property
    def docker_service(self) -> DockerService:
        """Get the Docker service instance (lazy initialization)."""
        if self._docker_service is None:
            self._docker_service = get_docker_service()
        return self._docker_service

    @property
    def tools(self) -> List[BaseTool]:
        """Get the agent's tools (lazy initialization)."""
        if self._tools is None:
            self._tools = self.get_tools()
        return self._tools

    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """Get the tools available to this agent.

        Returns:
            List of LangChain tools
        """
        pass

    def get_system_message(self) -> SystemMessage:
        """Get the system message for this agent.

        Returns:
            SystemMessage with the agent's system prompt
        """
        return SystemMessage(content=self.system_prompt)

    async def emit_status(
        self,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a status update via WebSocket.

        Args:
            status: Status (started, in_progress, completed, failed)
            message: Human-readable message
            details: Optional additional details
        """
        await connection_manager.send_agent_status(
            project_id=self.context.project_id,
            agent=self.name,
            status=status,
            message=message,
            details=details,
        )

    async def emit_tool_execution(
        self,
        tool_name: str,
        message: str,
        file_path: Optional[str] = None,
    ) -> None:
        """Emit a tool execution update via WebSocket.

        Args:
            tool_name: Name of the tool being executed
            message: Human-readable message
            file_path: Optional file path involved
        """
        await connection_manager.send_tool_execution(
            project_id=self.context.project_id,
            agent=self.name,
            tool=tool_name,
            message=message,
            file_path=file_path,
        )

    async def emit_file_operation(
        self,
        operation: str,
        file_path: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a file operation update via WebSocket.

        Args:
            operation: Operation type (create, update, delete)
            file_path: Path to the file
            message: Human-readable message
            details: Optional additional details
        """
        await connection_manager.send_file_operation(
            project_id=self.context.project_id,
            agent=self.name,
            operation=operation,
            file_path=file_path,
            message=message,
            details=details,
        )

    async def emit_error(
        self,
        error: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an error via WebSocket.

        Args:
            error: Error description
            message: Human-readable message
            details: Optional additional details
        """
        await connection_manager.send_error(
            project_id=self.context.project_id,
            agent=self.name,
            error=error,
            message=message,
            details=details,
        )

    async def invoke(
        self,
        messages: List[BaseMessage],
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke the LLM with messages and tools.

        Args:
            messages: List of messages to send
            **kwargs: Additional arguments to pass to the LLM

        Returns:
            AI response message
        """
        # Bind tools to LLM if available
        if self.tools:
            llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            llm_with_tools = self.llm

        # Add system message at the start
        full_messages = [self.get_system_message()] + messages

        try:
            response = await llm_with_tools.ainvoke(full_messages, **kwargs)
            
            # Debug: Check for thoughtSignature
            if hasattr(response, "additional_kwargs"):
                sig = response.additional_kwargs.get("thoughtSignature")
                if sig:
                    logger.debug(f"Gemini Thought Signature captured: {sig[:50]}...")
                elif response.tool_calls:
                    logger.debug("Gemini ToolCall generated but NO thoughtSignature found in additional_kwargs.")

            return response

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            await self.emit_error(
                error=str(e),
                message=f"LLM invocation failed: {e}",
            )
            raise

    async def invoke_with_retry(
        self,
        messages: List[BaseMessage],
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke the LLM with retry logic.

        Args:
            messages: List of messages to send
            **kwargs: Additional arguments to pass to the LLM

        Returns:
            AI response message
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await self.invoke(messages, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM invocation attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        raise last_error

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Any:
        """Execute a tool by name with arguments.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Tool execution result
        """
        # Find the tool
        target_tool = None
        for t in self.tools:
            if t.name == tool_name:
                target_tool = t
                break

        if target_tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        # Emit tool execution start
        await self.emit_tool_execution(
            tool_name=tool_name,
            message=f"Executing {tool_name}",
            file_path=tool_args.get("file_path") or tool_args.get("path"),
        )

        try:
            # Execute the tool
            if asyncio.iscoroutinefunction(target_tool.func):
                result = await target_tool.ainvoke(tool_args)
            else:
                result = target_tool.invoke(tool_args)

            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            await self.emit_error(
                error=str(e),
                message=f"Tool {tool_name} failed: {e}",
            )
            raise

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent with input data.

        Args:
            input_data: Input data for the agent

        Returns:
            Output data from the agent
        """
        pass

    async def log_operation(
        self,
        operation_type: str,
        message: str,
        status: str = "completed",
        details: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Log an operation to the memory system.

        Args:
            operation_type: Type of operation
            message: Human-readable message
            status: Operation status
            details: Additional details
            file_path: File path if applicable
            duration_ms: Duration in milliseconds
            error_message: Error message if failed
        """
        try:
            from app.agents.operations.memory import MemoryAgent
            from app.models.operation_log import AgentType, OperationType
            
            memory = MemoryAgent(self.context)
            
            # Map string to enum if needed
            try:
                op_type = OperationType(operation_type)
            except ValueError:
                op_type = OperationType.AGENT_TASK_COMPLETED
            
            try:
                agent_type = AgentType(self.name)
            except ValueError:
                agent_type = AgentType.SYSTEM
            
            await memory.log_operation(
                operation_type=op_type,
                agent_type=agent_type,
                message=message,
                status=status,
                details=details,
                file_path=file_path,
                duration_ms=duration_ms,
                error_message=error_message,
            )
        except Exception as e:
            # Don't let logging failures break the agent
            logger.warning(f"Failed to log operation: {e}")

    def start_timer(self) -> None:
        """Start the operation timer."""
        self._start_time = datetime.utcnow()

    def get_duration_ms(self) -> Optional[int]:
        """Get duration since timer start in milliseconds."""
        if self._start_time is None:
            return None
        delta = datetime.utcnow() - self._start_time
        return int(delta.total_seconds() * 1000)


def create_tool(
    name: str,
    description: str,
    func: Callable,
    args_schema: Optional[Type[BaseModel]] = None,
) -> BaseTool:
    """Create a LangChain tool from a function.

    Args:
        name: Tool name
        description: Tool description
        func: Function to wrap
        args_schema: Optional Pydantic model for arguments

    Returns:
        LangChain tool
    """
    @tool(name, description=description)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    if args_schema:
        wrapper.args_schema = args_schema

    return wrapper
