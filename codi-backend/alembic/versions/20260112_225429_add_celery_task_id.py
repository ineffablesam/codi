"""Add celery_task_id to agent_tasks

Revision ID: a8b135195b20
Revises: d6ee6fa321db
Create Date: 2026-01-12 22:54:29.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8b135195b20"
down_revision: Union[str, None] = "d6ee6fa321db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Commented out: agent_tasks table doesn't exist in migration chain
    # op.add_column("agent_tasks", sa.Column("celery_task_id", sa.String(length=100), nullable=True))
    pass


def downgrade() -> None:
    # Commented out: agent_tasks table doesn't exist in migration chain
    # op.drop_column("agent_tasks", "celery_task_id")
    pass
