"""Signal Engine - Event-driven agent coordination.

The SignalEngine is the heart of the Antigravity architecture.
It replaces explicit task delegation with signal-based activation.

Key behaviors:
1. Agents emit signals instead of delegating tasks
2. Agents subscribe to signals they can handle
3. When a signal is emitted, all subscribers are notified
4. Signals are derived from artifact state
"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Any
import uuid

from app.core.signals.types import Signal, SignalEvent, SignalPriority
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Type for signal handlers
SignalHandler = Callable[[SignalEvent], Any]


@dataclass
class SignalSubscription:
    """A subscription to a signal."""
    
    agent: str
    signal: Signal
    handler: Optional[SignalHandler] = None
    priority: int = 0  # Higher = called first
    
    def __hash__(self):
        return hash((self.agent, self.signal))


class SignalEngine:
    """
    Central signal routing engine.
    
    The engine manages:
    - Signal subscriptions (which agents handle which signals)
    - Signal emission (when signals fire)
    - Signal history (for debugging)
    - Signal derivation (from artifact state)
    """
    
    _instance: Optional["SignalEngine"] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Subscriptions: signal -> list of subscriptions
        self._subscriptions: Dict[Signal, List[SignalSubscription]] = defaultdict(list)
        
        # Active signals per project
        self._active_signals: Dict[int, Set[Signal]] = defaultdict(set)
        
        # Signal history for debugging
        self._history: List[SignalEvent] = []
        self._max_history = 1000
        
        # Event handlers for async notification
        self._event_handlers: List[SignalHandler] = []
        
        self._initialized = True
        logger.info("SignalEngine initialized")
    
    def subscribe(
        self,
        agent: str,
        signal: Signal,
        handler: Optional[SignalHandler] = None,
        priority: int = 0,
    ) -> None:
        """
        Subscribe an agent to a signal.
        
        Args:
            agent: Agent name
            signal: Signal to subscribe to
            handler: Optional callback for when signal fires
            priority: Higher priority handlers are called first
        """
        subscription = SignalSubscription(
            agent=agent,
            signal=signal,
            handler=handler,
            priority=priority,
        )
        
        # Avoid duplicates
        existing = [s for s in self._subscriptions[signal] if s.agent == agent]
        if not existing:
            self._subscriptions[signal].append(subscription)
            # Sort by priority (higher first)
            self._subscriptions[signal].sort(key=lambda s: -s.priority)
            
            logger.debug(f"Agent '{agent}' subscribed to signal {signal.value}")
    
    def unsubscribe(self, agent: str, signal: Signal) -> None:
        """Unsubscribe an agent from a signal."""
        self._subscriptions[signal] = [
            s for s in self._subscriptions[signal]
            if s.agent != agent
        ]
    
    def unsubscribe_all(self, agent: str) -> None:
        """Unsubscribe an agent from all signals."""
        for signal in Signal:
            self.unsubscribe(agent, signal)
    
    def get_subscribers(self, signal: Signal) -> List[str]:
        """Get list of agents subscribed to a signal."""
        return [s.agent for s in self._subscriptions[signal]]
    
    def get_subscriptions(self, agent: str) -> List[Signal]:
        """Get signals an agent is subscribed to."""
        return [
            signal for signal, subs in self._subscriptions.items()
            if any(s.agent == agent for s in subs)
        ]
    
    async def emit(
        self,
        signal: Signal,
        project_id: int,
        context: Dict[str, Any] = None,
        source: str = "system",
        priority: SignalPriority = SignalPriority.NORMAL,
        artifact_ids: List[str] = None,
    ) -> SignalEvent:
        """
        Emit a signal.
        
        This is the core method that replaces explicit delegation.
        When a signal is emitted, all subscribed agents are notified.
        
        Args:
            signal: Signal to emit
            project_id: Project context
            context: Additional context for handlers
            source: Agent or system that emitted the signal
            priority: Signal priority
            artifact_ids: Related artifact IDs
            
        Returns:
            The emitted SignalEvent
        """
        event = SignalEvent(
            signal=signal,
            project_id=project_id,
            context=context or {},
            source=source,
            priority=priority,
            artifact_ids=artifact_ids or [],
            correlation_id=str(uuid.uuid4())[:8],
        )
        
        # Track active signal
        self._active_signals[project_id].add(signal)
        
        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        logger.info(
            f"Signal emitted: {signal.value} for project {project_id} "
            f"(source: {source}, subscribers: {len(self._subscriptions[signal])})"
        )
        
        # Notify handlers
        subscriptions = self._subscriptions[signal]
        for subscription in subscriptions:
            if subscription.handler:
                try:
                    result = subscription.handler(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Handler error for {subscription.agent}: {e}")
        
        # Notify global event handlers
        for handler in self._event_handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Global handler error: {e}")
        
        return event
    
    async def emit_batch(
        self,
        signals: List[Signal],
        project_id: int,
        context: Dict[str, Any] = None,
        source: str = "system",
    ) -> List[SignalEvent]:
        """Emit multiple signals."""
        events = []
        for signal in signals:
            event = await self.emit(signal, project_id, context, source)
            events.append(event)
        return events
    
    def resolve(self, signal: Signal, project_id: int) -> None:
        """Mark a signal as resolved for a project."""
        self._active_signals[project_id].discard(signal)
        logger.debug(f"Signal resolved: {signal.value} for project {project_id}")
    
    def get_active_signals(self, project_id: int) -> Set[Signal]:
        """Get all active signals for a project."""
        return self._active_signals[project_id].copy()
    
    def is_active(self, signal: Signal, project_id: int) -> bool:
        """Check if a signal is currently active for a project."""
        return signal in self._active_signals[project_id]
    
    def add_event_handler(self, handler: SignalHandler) -> None:
        """Add a global event handler for all signals."""
        self._event_handlers.append(handler)
    
    def get_history(
        self,
        project_id: Optional[int] = None,
        signal: Optional[Signal] = None,
        limit: int = 100,
    ) -> List[SignalEvent]:
        """Get signal history, optionally filtered."""
        history = self._history
        
        if project_id is not None:
            history = [e for e in history if e.project_id == project_id]
        
        if signal is not None:
            history = [e for e in history if e.signal == signal]
        
        return history[-limit:]
    
    def clear_project(self, project_id: int) -> None:
        """Clear all active signals for a project."""
        self._active_signals[project_id].clear()


# Singleton instance
signal_engine = SignalEngine()


def get_signal_engine() -> SignalEngine:
    """Get the signal engine singleton."""
    return signal_engine
