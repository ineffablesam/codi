"""Signal Subscriber Mixin for agents.

This mixin enables agents to subscribe to and handle signals.
Agents that include this mixin are activated when subscribed signals fire.
"""
from typing import Any, Callable, Dict, List, Optional

from app.core.signals import (
    Signal,
    SignalEvent,
    get_signal_engine,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SignalSubscriberMixin:
    """
    Mixin for agents that subscribe to signals.
    
    This mixin provides signal handling capabilities. Agents declare
    which signals they handle, and are activated when those signals fire.
    
    Usage:
        class MyAgent(BaseAgent, SignalSubscriberMixin):
            subscribes_to = [Signal.NEEDS_BUILD, Signal.BUILD_FAILED]
            
            async def handle_signal(self, event: SignalEvent):
                if event.signal == Signal.NEEDS_BUILD:
                    await self.build_project()
    """
    
    # Override in subclass to declare subscriptions
    subscribes_to: List[Signal] = []
    
    # Signal handling priority (higher = called first)
    signal_priority: int = 0
    
    _subscribed: bool = False
    
    def register_signal_handlers(self) -> None:
        """Register this agent's signal handlers with the engine."""
        if self._subscribed:
            return
        
        engine = get_signal_engine()
        
        for signal in self.subscribes_to:
            engine.subscribe(
                agent=self.name,
                signal=signal,
                handler=self._dispatch_signal,
                priority=self.signal_priority,
            )
        
        self._subscribed = True
        
        if self.subscribes_to:
            logger.info(
                f"Agent '{self.name}' subscribed to signals: "
                f"{[s.value for s in self.subscribes_to]}"
            )
    
    def unregister_signal_handlers(self) -> None:
        """Unregister this agent's signal handlers."""
        engine = get_signal_engine()
        engine.unsubscribe_all(self.name)
        self._subscribed = False
    
    async def _dispatch_signal(self, event: SignalEvent) -> None:
        """Internal dispatcher for signal events."""
        try:
            await self.handle_signal(event)
        except Exception as e:
            logger.error(
                f"Agent '{self.name}' failed to handle signal "
                f"{event.signal.value}: {e}"
            )
            raise
    
    async def handle_signal(self, event: SignalEvent) -> None:
        """
        Handle a signal event.
        
        Override this method in subclasses to implement signal handling.
        
        Args:
            event: The signal event with context
        """
        # Default implementation - subclasses should override
        logger.debug(
            f"Agent '{self.name}' received signal {event.signal.value} "
            f"(no handler implemented)"
        )
    
    async def emit_signal(
        self,
        signal: Signal,
        context: Dict[str, Any] = None,
        artifact_ids: List[str] = None,
    ) -> SignalEvent:
        """
        Emit a signal from this agent.
        
        Args:
            signal: Signal to emit
            context: Optional context
            artifact_ids: Related artifact IDs
            
        Returns:
            The emitted signal event
        """
        engine = get_signal_engine()
        
        # Get project_id from context
        project_id = getattr(self.context, 'project_id', 0)
        
        return await engine.emit(
            signal=signal,
            project_id=project_id,
            context=context or {},
            source=self.name,
            artifact_ids=artifact_ids or [],
        )
    
    def can_handle(self, signal: Signal) -> bool:
        """Check if this agent can handle a signal."""
        return signal in self.subscribes_to


class SignalHandlerRegistry:
    """
    Registry for signal handler methods.
    
    This allows decorating methods as signal handlers.
    
    Usage:
        class MyAgent(BaseAgent, SignalSubscriberMixin):
            @signal_handler(Signal.NEEDS_BUILD)
            async def handle_needs_build(self, event):
                ...
    """
    
    _handlers: Dict[str, Dict[Signal, Callable]] = {}
    
    @classmethod
    def register(cls, agent_class: str, signal: Signal, method: Callable) -> None:
        """Register a handler method for a signal."""
        if agent_class not in cls._handlers:
            cls._handlers[agent_class] = {}
        cls._handlers[agent_class][signal] = method
    
    @classmethod
    def get_handler(cls, agent_class: str, signal: Signal) -> Optional[Callable]:
        """Get the handler method for a signal."""
        return cls._handlers.get(agent_class, {}).get(signal)


def signal_handler(signal: Signal):
    """
    Decorator to mark a method as a signal handler.
    
    Usage:
        @signal_handler(Signal.NEEDS_BUILD)
        async def handle_needs_build(self, event):
            ...
    """
    def decorator(method: Callable) -> Callable:
        # Store signal on method for discovery
        method._handles_signal = signal
        return method
    return decorator
