"""Mem0.ai integration service for agent memory management.

Provides persistent memory capabilities for the coding agent, enabling
context-aware conversations that span multiple sessions.
"""
import os
from typing import Any, Dict, List, Optional

from mem0 import Memory

from app.utils.logging import get_logger

logger = get_logger(__name__)


class Mem0Service:
    """Service for managing agent memory with Mem0.ai.
    
    Mem0 provides intelligent memory management with:
    - Automatic extraction of important information from conversations
    - Semantic search for relevant context retrieval
    - Memory consolidation and deduplication
    
    Configuration uses ChromaDB by default (already in requirements).
    Can be switched to Qdrant for production deployments.
    """
    
    _instance: Optional["Mem0Service"] = None
    _memory: Optional[Memory] = None
    
    def __new__(cls) -> "Mem0Service":
        """Singleton pattern for memory service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize Mem0 with configured backend."""
        if self._memory is not None:
            return  # Already initialized
            
        try:
            # Use environment variables for configuration
            vector_store = os.getenv("MEM0_VECTOR_STORE", "chroma")
            
            if vector_store == "qdrant":
                config = {
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "host": os.getenv("QDRANT_HOST", "localhost"),
                            "port": int(os.getenv("QDRANT_PORT", 6333)),
                            "collection_name": "codi_agent_memory",
                        }
                    },
                    "llm": {
                        "provider": "google",
                        "config": {
                            "model": "gemini-2.0-flash",
                            "temperature": 0.1,
                            "api_key": os.getenv("GEMINI_API_KEY"),
                        }
                    },
                    "embedder": {
                        "provider": "google",
                        "config": {
                            "model": "models/text-embedding-004",
                            "api_key": os.getenv("GEMINI_API_KEY"),
                        }
                    }
                }
            else:
                # Default to ChromaDB (simpler, no extra service needed)
                config = {
                    "vector_store": {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "codi_agent_memory",
                            "path": os.getenv("CHROMA_PATH", "/var/codi/chromadb"),
                        }
                    },
                    "llm": {
                        "provider": "google",
                        "config": {
                            "model": "gemini-2.0-flash",
                            "temperature": 0.1,
                            "api_key": os.getenv("GEMINI_API_KEY"),
                        }
                    },
                    "embedder": {
                        "provider": "google",
                        "config": {
                            "model": "models/text-embedding-004",
                            "api_key": os.getenv("GEMINI_API_KEY"),
                        }
                    }
                }
            
            self._memory = Memory.from_config(config)
            logger.info(f"Mem0 initialized with {vector_store} backend")
            
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            # Don't raise - service should work without memory (graceful degradation)
            self._memory = None
    
    @property
    def is_available(self) -> bool:
        """Check if memory service is available."""
        return self._memory is not None
    
    async def add_memory(
        self,
        content: str,
        user_id: str,
        session_id: Optional[str] = None,
        project_id: Optional[int] = None,
        memory_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Add a memory to Mem0.
        
        Args:
            content: The memory content to store
            user_id: Unique user identifier (format: "user_{id}")
            session_id: Optional session ID for session-scoped memories
            project_id: Optional project ID for project-scoped memories
            memory_type: Type classification (task, decision, learning, deployment, etc.)
            metadata: Additional metadata to store
            
        Returns:
            Memory ID from Mem0, or None if failed
        """
        if not self.is_available:
            logger.warning("Memory service not available, skipping add_memory")
            return None
            
        try:
            # Build metadata
            mem_metadata = metadata or {}
            mem_metadata.update({
                "type": memory_type,
                "session_id": session_id,
                "project_id": project_id,
            })
            
            # Add memory to Mem0
            result = self._memory.add(
                content,
                user_id=user_id,
                metadata=mem_metadata,
            )
            
            # Extract memory ID from result
            if result and isinstance(result, dict):
                memory_id = result.get("id") or result.get("memory_id")
                logger.info(f"Added memory: {memory_id} for user {user_id}")
                return memory_id
            elif result and isinstance(result, list) and len(result) > 0:
                memory_id = result[0].get("id") or result[0].get("memory_id")
                logger.info(f"Added memory: {memory_id} for user {user_id}")
                return memory_id
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return None
    
    async def search_memories(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None,
        project_id: Optional[int] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for relevant memories.
        
        Args:
            query: Search query for semantic matching
            user_id: User identifier to scope search
            session_id: Optional session ID to filter by
            project_id: Optional project ID to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of memory dictionaries with content and metadata
        """
        if not self.is_available:
            logger.warning("Memory service not available, returning empty memories")
            return []
            
        try:
            # Search with Mem0
            results = self._memory.search(
                query=query,
                user_id=user_id,
                limit=limit,
            )
            
            # Filter by session/project if specified
            memories = []
            for mem in (results or []):
                mem_metadata = mem.get("metadata", {})
                
                # Apply session filter
                if session_id and mem_metadata.get("session_id") != session_id:
                    continue
                    
                # Apply project filter
                if project_id and mem_metadata.get("project_id") != project_id:
                    continue
                
                memories.append({
                    "id": mem.get("id"),
                    "content": mem.get("memory") or mem.get("content", ""),
                    "type": mem_metadata.get("type", "general"),
                    "session_id": mem_metadata.get("session_id"),
                    "project_id": mem_metadata.get("project_id"),
                    "score": mem.get("score", 0),
                })
            
            logger.debug(f"Found {len(memories)} relevant memories for query")
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_session_context(
        self,
        session_id: str,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """Get formatted context for a session.
        
        Retrieves relevant memories and formats them for inclusion
        in the agent's system prompt.
        
        Args:
            session_id: Chat session ID
            user_id: User identifier
            query: Optional query to find relevant context (uses session history if not provided)
            limit: Maximum memories to include
            
        Returns:
            Formatted context string for agent prompt
        """
        if not query:
            query = "What has been discussed and accomplished in this project?"
            
        memories = await self.search_memories(
            query=query,
            user_id=user_id,
            session_id=None,  # Search all sessions for broader context
            limit=limit,
        )
        
        if not memories:
            return ""
            
        context_parts = [
            "## Relevant Context from Previous Interactions\n",
            "The following information may be relevant to the current task:\n",
        ]
        
        for mem in memories:
            mem_type = mem.get("type", "note")
            content = mem.get("content", "")
            context_parts.append(f"- [{mem_type}] {content}")
        
        return "\n".join(context_parts)
    
    async def delete_session_memories(
        self,
        session_id: str,
        user_id: str,
    ) -> bool:
        """Delete all memories for a session.
        
        Called when a session is deleted to clean up associated memories.
        
        Args:
            session_id: Session to delete memories for
            user_id: User identifier
            
        Returns:
            True if deletion succeeded
        """
        if not self.is_available:
            return True  # Nothing to delete
            
        try:
            # Get all memories for this session
            memories = await self.search_memories(
                query="*",  # Match all
                user_id=user_id,
                session_id=session_id,
                limit=1000,
            )
            
            # Delete each memory
            for mem in memories:
                mem_id = mem.get("id")
                if mem_id:
                    self._memory.delete(mem_id)
            
            logger.info(f"Deleted {len(memories)} memories for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session memories: {e}")
            return False
    
    async def get_all_user_memories(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all memories for a user.
        
        Useful for debugging or memory management UI.
        
        Args:
            user_id: User identifier
            limit: Maximum memories to return
            
        Returns:
            List of all user memories
        """
        if not self.is_available:
            return []
            
        try:
            result = self._memory.get_all(user_id=user_id)
            
            memories = []
            for mem in (result or []):
                memories.append({
                    "id": mem.get("id"),
                    "content": mem.get("memory") or mem.get("content", ""),
                    "metadata": mem.get("metadata", {}),
                    "created_at": mem.get("created_at"),
                })
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get user memories: {e}")
            return []


# Singleton instance for easy access
_mem0_service: Optional[Mem0Service] = None


def get_mem0_service() -> Mem0Service:
    """Get the Mem0 service singleton."""
    global _mem0_service
    if _mem0_service is None:
        _mem0_service = Mem0Service()
    return _mem0_service
