"""Update enum types with missing values.

Revision ID: 20251230_192600
Revises: 20251230_004419_add_agent_tasks_table
Create Date: 2024-12-30 19:26:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251230_192600_update_enums'
down_revision: Union[str, None] = 'b2f4ae3e874d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing values to operationtype enum
    # These were defined in the Python Enum but not in the initial migration
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'plan_created'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'plan_step_started'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'plan_step_completed'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'project_created'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'project_updated'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'project_archived'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'user_message'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'agent_response'")
    op.execute("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'file_read'")

    # Add missing values to agenttype enum
    op.execute("ALTER TYPE agenttype ADD VALUE IF NOT EXISTS 'backend_engineer'")
    op.execute("ALTER TYPE agenttype ADD VALUE IF NOT EXISTS 'user'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values easily
    # To downgrade, you would need to:
    # 1. Create a new enum type without the values
    # 2. Update the column to use the new type
    # 3. Drop the old type
    # This is left as a no-op for simplicity
    pass
