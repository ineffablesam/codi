"""Add local git columns to projects.

Revision ID: b1f02e37a810
Revises: a2306eab695e
Create Date: 2026-01-10 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f02e37a810'
down_revision: Union[str, None] = 'a2306eab695e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add local git columns to projects table."""
    # Add new local git columns
    op.add_column('projects', sa.Column('local_path', sa.String(500), nullable=True))
    op.add_column('projects', sa.Column('git_commit_sha', sa.String(40), nullable=True))
    op.add_column('projects', sa.Column('git_branch', sa.String(100), nullable=False, server_default='main'))


def downgrade() -> None:
    """Remove local git columns from projects table."""
    op.drop_column('projects', 'git_branch')
    op.drop_column('projects', 'git_commit_sha')
    op.drop_column('projects', 'local_path')
