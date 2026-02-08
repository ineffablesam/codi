"""Pydantic schemas for chat sessions and messages."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# Chat Session Schemas
# ==============================================================================


class ChatSessionCreate(BaseModel):
    """Schema for creating a new chat session."""
    
    title: str = Field(default="New Chat", max_length=255)
    metadata: Optional[Dict[str, Any]] = None


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""
    
    title: Optional[str] = Field(default=None, max_length=255)
    metadata: Optional[Dict[str, Any]] = None


class ChatSessionResponse(BaseModel):
    """Schema for chat session response."""
    
    id: str
    project_id: int
    user_id: int
    title: str
    message_count: int
    last_message_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default={}, validation_alias="meta_data")
    
    class Config:
        from_attributes = True


class ChatSessionListResponse(BaseModel):
    """Schema for listing chat sessions."""
    
    sessions: List[ChatSessionResponse]
    total: int
    has_archived: bool = False


# ==============================================================================
# Chat Message Schemas
# ==============================================================================


class ChatMessageCreate(BaseModel):
    """Schema for creating a new message."""
    
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    tool_calls: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    
    id: str
    session_id: str
    role: str
    content: str
    tool_calls: Optional[Dict[str, Any]] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default={}, validation_alias="meta_data")
    
    class Config:
        from_attributes = True


class ChatMessagesListResponse(BaseModel):
    """Schema for listing messages with pagination."""
    
    messages: List[ChatMessageResponse]
    total: int
    has_more: bool = False
    next_cursor: Optional[str] = None


# ==============================================================================
# Agent Memory Schemas
# ==============================================================================


class AgentMemoryResponse(BaseModel):
    """Schema for agent memory response."""
    
    id: str
    session_id: Optional[str] = None
    project_id: int
    memory_type: str
    content: str
    mem0_memory_id: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default={}, validation_alias="meta_data")
    
    class Config:
        from_attributes = True


class AgentMemoriesListResponse(BaseModel):
    """Schema for listing memories."""
    
    memories: List[AgentMemoryResponse]
    total: int
