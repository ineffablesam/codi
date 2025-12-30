"""Base agent class for all LangGraph agents."""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.config import settings
from app.services.github import GitHubService
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


class AgentContext(BaseModel):
    """Context passed to agents during execution."""

    project_id: int
    user_id: int
    github_token: str
    repo_full_name: Optional[str] = None
    current_branch: str = "main"
    task_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """Base class for all agents in the system.

    Each agent has:
    - A unique name and system prompt
    - Access to the LLM (Gemini)
    - Tools specific to its role
    - WebSocket broadcasting capabilities
    """

    # Agent identity
    name: str = "base_agent"
    description: str = "Base agent"

    # Default system prompt (override in subclasses)
    system_prompt: str = "You are a helpful AI assistant."

    def __init__(self, context: AgentContext) -> None:
        """Initialize the agent.

        Args:
            context: Agent context with project info and credentials
        """
        self.context = context
        self._llm: Optional[ChatGoogleGenerativeAI] = None
        self._github_service: Optional[GitHubService] = None
        self._tools: Optional[List[BaseTool]] = None

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Get the LLM instance (lazy initialization)."""
        if self._llm is None:
            api_key = settings.gemini_api_key
            if not api_key:
                logger.error("GEMINI_API_KEY is not set in environment or .env file")
                raise ValueError(
                    "GEMINI_API_KEY is missing. Please add it to your .env file. "
                    "You can get one from https://aistudio.google.com/app/apikey"
                )

            self._llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=api_key,
                temperature=1.0,
                max_output_tokens=8192,
                convert_system_message_to_human=True,
                streaming=False,
            )
        return self._llm

    @property
    def github_service(self) -> GitHubService:
        """Get the GitHub service instance (lazy initialization)."""
        if self._github_service is None:
            self._github_service = GitHubService(access_token=self.context.github_token)
        return self._github_service

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
            return response

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            await self.emit_error(
                error=str(e),
                message=f"LLM invocation failed: {e}",
            )
            raise

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
