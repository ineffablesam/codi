"""Session Manager for agent context continuity.

Tracks agent sessions for multi-turn interactions and context preservation.
Enables session resumption and parent-child task relationships.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Session TTL - sessions older than this are pruned
SESSION_TTL = timedelta(hours=2)


@dataclass
class SessionMessage:
    """A message in a session history."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent: Optional[str] = None
    tool_calls: List[str] = field(default_factory=list)


@dataclass
class AgentSession:
    """An agent session with context and history."""
    id: str
    parent_id: Optional[str] = None
    agent: str = "conductor"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Session context
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    task_id: Optional[str] = None
    
    # Message history (limited for memory efficiency)
    messages: List[SessionMessage] = field(default_factory=list)
    max_messages: int = 50
    
    # Metadata
    title: Optional[str] = None
    status: str = "active"  # active, idle, completed
    
    # Skills and context injected
    active_skills: List[str] = field(default_factory=list)
    category: Optional[str] = None
    
    def add_message(self, role: str, content: str, agent: Optional[str] = None, 
                    tool_calls: Optional[List[str]] = None) -> None:
        """Add a message to session history."""
        msg = SessionMessage(
            role=role,
            content=content,
            agent=agent,
            tool_calls=tool_calls or []
        )
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        
        # Trim old messages if exceeding limit
        if len(self.messages) > self.max_messages:
            # Keep system messages and recent messages
            system_msgs = [m for m in self.messages if m.role == "system"]
            other_msgs = [m for m in self.messages if m.role != "system"]
            keep_count = self.max_messages - len(system_msgs)
            self.messages = system_msgs + other_msgs[-keep_count:]
    
    def get_context_messages(self) -> List[Dict[str, Any]]:
        """Get messages formatted for LLM context."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "agent": msg.agent,
            }
            for msg in self.messages
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "agent": self.agent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "project_id": self.project_id,
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status,
            "message_count": len(self.messages),
            "active_skills": self.active_skills,
            "category": self.category,
        }


class SessionManager:
    """Manager for agent sessions.
    
    Features:
    - Create and track sessions
    - Session resumption with full context
    - Parent-child session relationships (for background tasks)
    - Session pruning based on TTL
    """
    
    _instance: Optional["SessionManager"] = None
    
    def __new__(cls) -> "SessionManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._sessions: Dict[str, AgentSession] = {}
        self._subagent_sessions: Set[str] = set()  # Sessions created as subagents
        self._lock = asyncio.Lock()
        self._initialized = True
        
        logger.info("SessionManager initialized")
    
    async def create(
        self,
        session_id: str,
        parent_id: Optional[str] = None,
        agent: str = "conductor",
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        category: Optional[str] = None,
        skills: Optional[List[str]] = None,
    ) -> AgentSession:
        """Create a new session.
        
        Args:
            session_id: Unique session identifier
            parent_id: Parent session ID (for subagent sessions)
            agent: Agent name for this session
            project_id: Associated project ID
            user_id: Associated user ID
            task_id: Associated task ID
            title: Human-readable session title
            category: Agent category (visual, logic, etc.)
            skills: Active skills for this session
            
        Returns:
            Created AgentSession
        """
        async with self._lock:
            session = AgentSession(
                id=session_id,
                parent_id=parent_id,
                agent=agent,
                project_id=project_id,
                user_id=user_id,
                task_id=task_id,
                title=title,
                category=category,
                active_skills=skills or [],
            )
            self._sessions[session_id] = session
            
            if parent_id:
                self._subagent_sessions.add(session_id)
            
            logger.debug(f"Created session {session_id} for agent {agent}")
            return session
    
    def get(self, session_id: str) -> Optional[AgentSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_or_create(
        self,
        session_id: str,
        **kwargs
    ) -> AgentSession:
        """Get existing session or create new one."""
        if session_id in self._sessions:
            return self._sessions[session_id]
        
        # Create synchronously (can't await in this method)
        session = AgentSession(id=session_id, **kwargs)
        self._sessions[session_id] = session
        return session
    
    def get_children(self, parent_id: str) -> List[AgentSession]:
        """Get all child sessions of a parent."""
        return [
            session for session in self._sessions.values()
            if session.parent_id == parent_id
        ]
    
    def get_active_sessions(self) -> List[AgentSession]:
        """Get all active sessions."""
        return [
            session for session in self._sessions.values()
            if session.status == "active"
        ]
    
    def is_subagent_session(self, session_id: str) -> bool:
        """Check if a session is a subagent session."""
        return session_id in self._subagent_sessions
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: Optional[str] = None,
        tool_calls: Optional[List[str]] = None,
    ) -> bool:
        """Add a message to a session.
        
        Returns:
            True if message was added, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.add_message(role, content, agent, tool_calls)
        return True
    
    def update_status(self, session_id: str, status: str) -> bool:
        """Update session status.
        
        Args:
            session_id: Session ID
            status: New status (active, idle, completed)
            
        Returns:
            True if updated, False if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.status = status
        session.updated_at = datetime.utcnow()
        return True
    
    async def delete(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._subagent_sessions.discard(session_id)
                logger.debug(f"Deleted session {session_id}")
                return True
            return False
    
    def prune_stale_sessions(self) -> int:
        """Remove sessions older than TTL.
        
        Returns:
            Number of sessions pruned
        """
        now = datetime.utcnow()
        stale_ids = []
        
        for session_id, session in self._sessions.items():
            age = now - session.updated_at
            if age > SESSION_TTL and session.status != "active":
                stale_ids.append(session_id)
        
        for session_id in stale_ids:
            del self._sessions[session_id]
            self._subagent_sessions.discard(session_id)
        
        if stale_ids:
            logger.info(f"Pruned {len(stale_ids)} stale sessions")
        
        return len(stale_ids)
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get full session context for resumption.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session context dict or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session": session.to_dict(),
            "messages": session.get_context_messages(),
            "parent_context": (
                self.get_session_context(session.parent_id)
                if session.parent_id else None
            ),
        }
    
    def list_sessions(
        self,
        project_id: Optional[int] = None,
        agent: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[AgentSession]:
        """List sessions with optional filters.
        
        Args:
            project_id: Filter by project
            agent: Filter by agent name
            status: Filter by status
            limit: Max results
            
        Returns:
            List of matching sessions
        """
        results = []
        for session in self._sessions.values():
            if project_id and session.project_id != project_id:
                continue
            if agent and session.agent != agent:
                continue
            if status and session.status != status:
                continue
            results.append(session)
            if len(results) >= limit:
                break
        
        return sorted(results, key=lambda s: s.updated_at, reverse=True)
    
    def cleanup(self) -> None:
        """Cleanup all sessions."""
        self._sessions.clear()
        self._subagent_sessions.clear()
        logger.info("SessionManager cleaned up")


# Global singleton instance
session_manager = SessionManager()
