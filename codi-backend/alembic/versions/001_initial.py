"""Initial database migration.

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_id', sa.Integer(), nullable=False),
        sa.Column('github_username', sa.String(255), nullable=False),
        sa.Column('github_access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('github_avatar_url', sa.String(500), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('github_id', name=op.f('uq_users_github_id')),
        sa.UniqueConstraint('github_username', name=op.f('uq_users_github_username')),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_github_username'), 'users', ['github_username'], unique=True)

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('github_repo_name', sa.String(255), nullable=True),
        sa.Column('github_repo_full_name', sa.String(500), nullable=True),
        sa.Column('github_repo_url', sa.String(500), nullable=True),
        sa.Column('github_clone_url', sa.String(500), nullable=True),
        sa.Column('github_default_branch', sa.String(100), nullable=True, default='main'),
        sa.Column('github_current_branch', sa.String(100), nullable=True, default='main'),
        sa.Column('is_private', sa.Boolean(), nullable=False, default=False),
        sa.Column('status', sa.Enum('active', 'building', 'deploying', 'archived', 'error', name='projectstatus'), nullable=False, default='active'),
        sa.Column('framework_version', sa.String(50), nullable=True),
        sa.Column('dart_version', sa.String(50), nullable=True),
        sa.Column('deployment_url', sa.String(500), nullable=True),
        sa.Column('deployment_provider', sa.String(50), nullable=True),
        sa.Column('last_build_status', sa.String(50), nullable=True),
        sa.Column('last_build_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_deployment_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_projects_owner_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_projects')),
    )
    op.create_index(op.f('ix_projects_github_repo_full_name'), 'projects', ['github_repo_full_name'], unique=False)
    op.create_index(op.f('ix_projects_owner_id'), 'projects', ['owner_id'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)

    # Create operation_logs table
    op.create_table(
        'operation_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.Enum(
            'file_created', 'file_updated', 'file_deleted',
            'branch_created', 'commit_created', 'push_completed', 'pr_created', 'pr_merged',
            'build_started', 'build_progress', 'build_completed', 'build_failed',
            'deployment_started', 'deployment_completed', 'deployment_failed',
            'code_review_started', 'code_review_completed', 'code_review_issue',
            'agent_task_started', 'agent_task_completed', 'agent_task_failed',
            name='operationtype'
        ), nullable=False),
        sa.Column('agent_type', sa.Enum(
            'planner', 'flutter_engineer', 'code_reviewer',
            'git_operator', 'build_deploy', 'memory', 'system',
            name='agenttype'
        ), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='completed'),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('commit_sha', sa.String(40), nullable=True),
        sa.Column('branch_name', sa.String(255), nullable=True),
        sa.Column('lines_added', sa.Integer(), nullable=True),
        sa.Column('lines_removed', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_operation_logs_project_id_projects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_operation_logs_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_operation_logs')),
    )
    op.create_index(op.f('ix_operation_logs_agent_type'), 'operation_logs', ['agent_type'], unique=False)
    op.create_index(op.f('ix_operation_logs_created_at'), 'operation_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_operation_logs_operation_type'), 'operation_logs', ['operation_type'], unique=False)
    op.create_index(op.f('ix_operation_logs_project_id'), 'operation_logs', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_operation_logs_project_id'), table_name='operation_logs')
    op.drop_index(op.f('ix_operation_logs_operation_type'), table_name='operation_logs')
    op.drop_index(op.f('ix_operation_logs_created_at'), table_name='operation_logs')
    op.drop_index(op.f('ix_operation_logs_agent_type'), table_name='operation_logs')
    op.drop_table('operation_logs')

    op.drop_index(op.f('ix_projects_status'), table_name='projects')
    op.drop_index(op.f('ix_projects_owner_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_github_repo_full_name'), table_name='projects')
    op.drop_table('projects')

    op.drop_index(op.f('ix_users_github_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS projectstatus')
    op.execute('DROP TYPE IF EXISTS operationtype')
    op.execute('DROP TYPE IF EXISTS agenttype')
