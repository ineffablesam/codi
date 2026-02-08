"""Add Opik tracing tables for AI operation tracking.

Revision ID: 20260206_000000
Revises: 20260126_000000
Create Date: 2026-02-06 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260206_000000'
down_revision: Union[str, None] = 'adafc1b64587'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create traces table
    op.create_table(
        'traces',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('trace_type', sa.String(50), nullable=False),
        sa.Column('parent_trace_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_traces_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_traces_project_id_projects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_trace_id'], ['traces.id'], name=op.f('fk_traces_parent_trace_id_traces'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_traces')),
    )
    op.create_index(op.f('ix_traces_user_id'), 'traces', ['user_id'], unique=False)
    op.create_index(op.f('ix_traces_project_id'), 'traces', ['project_id'], unique=False)
    op.create_index(op.f('ix_traces_start_time'), 'traces', ['start_time'], unique=False)
    op.create_index(op.f('ix_traces_trace_type'), 'traces', ['trace_type'], unique=False)
    # Composite index for efficient user/project trace queries
    op.create_index('ix_traces_user_project_start', 'traces', ['user_id', 'project_id', 'start_time'], unique=False)

    # Create evaluations table
    op.create_table(
        'evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('trace_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trace_id'], ['traces.id'], name=op.f('fk_evaluations_trace_id_traces'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluations')),
    )
    op.create_index(op.f('ix_evaluations_trace_id'), 'evaluations', ['trace_id'], unique=False)
    op.create_index(op.f('ix_evaluations_metric_name'), 'evaluations', ['metric_name'], unique=False)

    # Create experiments table (for A/B testing prompts)
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('prompt_versions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_experiments_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_experiments')),
    )
    op.create_index(op.f('ix_experiments_user_id'), 'experiments', ['user_id'], unique=False)

    # Create prompts table (versioned prompt management)
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_prompts')),
        sa.UniqueConstraint('name', 'version', name=op.f('uq_prompts_name_version')),
    )
    op.create_index(op.f('ix_prompts_name'), 'prompts', ['name'], unique=False)


def downgrade() -> None:
    # Drop prompts table
    op.drop_index(op.f('ix_prompts_name'), table_name='prompts')
    op.drop_table('prompts')

    # Drop experiments table
    op.drop_index(op.f('ix_experiments_user_id'), table_name='experiments')
    op.drop_table('experiments')

    # Drop evaluations table
    op.drop_index(op.f('ix_evaluations_metric_name'), table_name='evaluations')
    op.drop_index(op.f('ix_evaluations_trace_id'), table_name='evaluations')
    op.drop_table('evaluations')

    # Drop traces table
    op.drop_index('ix_traces_user_project_start', table_name='traces')
    op.drop_index(op.f('ix_traces_trace_type'), table_name='traces')
    op.drop_index(op.f('ix_traces_start_time'), table_name='traces')
    op.drop_index(op.f('ix_traces_project_id'), table_name='traces')
    op.drop_index(op.f('ix_traces_user_id'), table_name='traces')
    op.drop_table('traces')
