"""Add chat sessions and multi-chat support.

Revision ID: 20260126_000000
Revises: 20260118_083413
Create Date: 2026-01-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260126_000000'
down_revision: Union[str, None] = '9ee71cd1de62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False, server_default='New Chat'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mem0_user_id', sa.String(255), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_chat_sessions_project_id_projects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_chat_sessions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chat_sessions')),
    )
    op.create_index(op.f('ix_chat_sessions_project_id'), 'chat_sessions', ['project_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_user_id'), 'chat_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_archived_at'), 'chat_sessions', ['archived_at'], unique=False)
    op.create_index(op.f('ix_chat_sessions_deleted_at'), 'chat_sessions', ['deleted_at'], unique=False)

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], name=op.f('fk_chat_messages_session_id_chat_sessions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chat_messages')),
    )
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)
    # Composite index for efficient session message queries
    op.create_index('ix_chat_messages_session_created', 'chat_messages', ['session_id', 'created_at'], unique=False)

    # Create agent_memories table
    op.create_table(
        'agent_memories',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('memory_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('mem0_memory_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], name=op.f('fk_agent_memories_session_id_chat_sessions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_agent_memories_project_id_projects'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_memories')),
    )
    op.create_index(op.f('ix_agent_memories_session_id'), 'agent_memories', ['session_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_project_id'), 'agent_memories', ['project_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_memory_type'), 'agent_memories', ['memory_type'], unique=False)

    # Add setup_stage column to projects for initial project setup flow
    op.add_column('projects', sa.Column('setup_stage', sa.String(50), nullable=False, server_default='completed'))


def downgrade() -> None:
    # Remove setup_stage from projects
    op.drop_column('projects', 'setup_stage')

    # Drop agent_memories
    op.drop_index(op.f('ix_agent_memories_memory_type'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_project_id'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_session_id'), table_name='agent_memories')
    op.drop_table('agent_memories')

    # Drop chat_messages
    op.drop_index('ix_chat_messages_session_created', table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_created_at'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_session_id'), table_name='chat_messages')
    op.drop_table('chat_messages')

    # Drop chat_sessions
    op.drop_index(op.f('ix_chat_sessions_deleted_at'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_archived_at'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_user_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_project_id'), table_name='chat_sessions')
    op.drop_table('chat_sessions')
