"""Chat session and message CRUD API endpoints."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.database import get_db_session as get_db
from app.models.chat_session import AgentMemory, ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import (
    AgentMemoriesListResponse,
    AgentMemoryResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessagesListResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.memory.mem0_service import get_mem0_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])


# ==============================================================================
# Chat Session Endpoints
# ==============================================================================


@router.post(
    "/projects/{project_id}/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_session(
    project_id: int,
    data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new chat session for a project."""
    try:
        user_id = user.id
        # Generate mem0 user ID
        mem0_user_id = f"user_{user_id}_project_{project_id}"
        
        session = ChatSession(
            id=str(uuid4()),
            project_id=project_id,
            user_id=user_id,
            title=data.title,
            mem0_user_id=mem0_user_id,
            meta_data=data.metadata or {},
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Created chat session {session.id} for project {project_id}")
        return ChatSessionResponse.model_validate(session)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session",
        )


@router.get(
    "/projects/{project_id}/sessions",
    response_model=ChatSessionListResponse,
)
async def list_chat_sessions(
    project_id: int,
    include_archived: bool = Query(False, description="Include archived sessions"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all chat sessions for a project."""
    try:
        user_id = user.id
        # Base query - exclude soft-deleted
        query = select(ChatSession).where(
            ChatSession.project_id == project_id,
            ChatSession.user_id == user_id,
            ChatSession.deleted_at.is_(None),
        )
        
        # Filter archived unless requested
        if not include_archived:
            query = query.where(ChatSession.archived_at.is_(None))
        
        # Order by last message (most recent first), then created_at
        query = query.order_by(
            ChatSession.last_message_at.desc().nullsfirst(),
            ChatSession.created_at.desc(),
        )
        
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        # Check if there are any archived sessions
        archived_count_query = select(func.count(ChatSession.id)).where(
            ChatSession.project_id == project_id,
            ChatSession.user_id == user_id,
            ChatSession.deleted_at.is_(None),
            ChatSession.archived_at.isnot(None),
        )
        archived_result = await db.execute(archived_count_query)
        has_archived = archived_result.scalar() > 0
        
        return ChatSessionListResponse(
            sessions=[ChatSessionResponse.model_validate(s) for s in sessions],
            total=len(sessions),
            has_archived=has_archived,
        )
        
    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list chat sessions",
        )


@router.get(
    "/{session_id}",
    response_model=ChatSessionResponse,
)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a chat session by ID."""
    session = await _get_session_or_404(db, session_id, user.id)
    return ChatSessionResponse.model_validate(session)


@router.patch(
    "/{session_id}/title",
    response_model=ChatSessionResponse,
)
async def update_chat_title(
    session_id: str,
    data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update chat session title."""
    session = await _get_session_or_404(db, session_id, user.id)
    
    if data.title:
        session.title = data.title
    if data.metadata:
        session.meta_data = {**(session.meta_data or {}), **data.metadata}
    
    session.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(session)
    
    return ChatSessionResponse.model_validate(session)


@router.patch(
    "/{session_id}/archive",
    response_model=ChatSessionResponse,
)
async def archive_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Archive a chat session."""
    session = await _get_session_or_404(db, session_id, user.id)
    
    if session.archived_at:
        # Unarchive if already archived
        session.archived_at = None
    else:
        session.archived_at = datetime.utcnow()
    
    session.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(session)
    
    logger.info(f"Toggled archive status for session {session_id}")
    return ChatSessionResponse.model_validate(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft delete a chat session."""
    session = await _get_session_or_404(db, session_id, user.id)
    
    session.deleted_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Clean up Mem0 memories in background
    try:
        mem0_service = get_mem0_service()
        await mem0_service.delete_session_memories(
            session_id=session_id,
            user_id=session.mem0_user_id,
        )
    except Exception as e:
        logger.warning(f"Failed to clean up Mem0 memories: {e}")
    
    logger.info(f"Soft deleted session {session_id}")


# ==============================================================================
# Chat Message Endpoints
# ==============================================================================


@router.get(
    "/{session_id}/messages",
    response_model=ChatMessagesListResponse,
)
async def list_chat_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    before: Optional[str] = Query(None, description="Cursor for pagination (message ID)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List messages for a chat session with cursor pagination."""
    # Verify session access
    await _get_session_or_404(db, session_id, user.id)
    
    try:
        query = select(ChatMessage).where(
            ChatMessage.session_id == session_id,
        )
        
        # Apply cursor pagination
        if before:
            # Get the timestamp of the cursor message
            cursor_query = select(ChatMessage.created_at).where(
                ChatMessage.id == before
            )
            cursor_result = await db.execute(cursor_query)
            cursor_time = cursor_result.scalar()
            
            if cursor_time:
                query = query.where(ChatMessage.created_at < cursor_time)
        
        # Order by oldest first for chat display
        query = query.order_by(ChatMessage.created_at.desc()).limit(limit + 1)
        
        result = await db.execute(query)
        messages = list(result.scalars().all())
        
        # Check if there are more messages
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        # Reverse to get chronological order
        messages.reverse()
        
        # Get next cursor
        next_cursor = messages[0].id if messages and has_more else None
        
        # Get total count
        count_query = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return ChatMessagesListResponse(
            messages=[ChatMessageResponse.model_validate(m) for m in messages],
            total=total,
            has_more=has_more,
            next_cursor=next_cursor,
        )
        
    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list messages",
        )


@router.post(
    "/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_message(
    session_id: str,
    data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new message in a chat session."""
    session = await _get_session_or_404(db, session_id, user.id)
    
    try:
        message = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            role=data.role,
            content=data.content,
            tool_calls=data.tool_calls,
            meta_data=data.metadata or {},
        )
        
        db.add(message)
        
        # Update session stats
        session.message_count += 1
        session.last_message_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(message)
        
        return ChatMessageResponse.model_validate(message)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create message",
        )


# ==============================================================================
# Agent Memory Endpoints
# ==============================================================================


@router.get(
    "/{session_id}/memories",
    response_model=AgentMemoriesListResponse,
)
async def list_session_memories(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all memories for a chat session."""
    # Verify session access
    await _get_session_or_404(db, session_id, user.id)
    
    try:
        query = select(AgentMemory).where(
            AgentMemory.session_id == session_id,
        ).order_by(AgentMemory.created_at.desc())
        
        result = await db.execute(query)
        memories = result.scalars().all()
        
        return AgentMemoriesListResponse(
            memories=[AgentMemoryResponse.model_validate(m) for m in memories],
            total=len(memories),
        )
        
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list memories",
        )


# ==============================================================================
# Helper Functions
# ==============================================================================


async def _get_session_or_404(
    db: AsyncSession,
    session_id: str,
    user_id: int,
) -> ChatSession:
    """Get a session or raise 404."""
    query = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
        ChatSession.deleted_at.is_(None),
    )
    
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    
    return session
