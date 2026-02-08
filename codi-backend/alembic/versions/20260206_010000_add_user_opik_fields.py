"""Add Opik preferences to users table.

Revision ID: 20260206_010000
Revises: 20260206_000000
Create Date: 2026-02-06 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260206_010000'
down_revision: Union[str, None] = '20260206_000000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Opik configuration columns to users table
    op.add_column('users', sa.Column('opik_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('opik_api_key', sa.Text(), nullable=True))  # Encrypted
    op.add_column('users', sa.Column('opik_workspace', sa.String(255), nullable=True))
    
    # Create index for quick lookups of users with tracing enabled
    op.create_index(op.f('ix_users_opik_enabled'), 'users', ['opik_enabled'], unique=False)


def downgrade() -> None:
    # Drop index and columns
    op.drop_index(op.f('ix_users_opik_enabled'), table_name='users')
    op.drop_column('users', 'opik_workspace')
    op.drop_column('users', 'opik_api_key')
    op.drop_column('users', 'opik_enabled')
