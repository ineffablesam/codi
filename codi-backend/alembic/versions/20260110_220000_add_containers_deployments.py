"""Add containers and deployments tables.

Revision ID: c2d03f48b921
Revises: b1f02e37a810
Create Date: 2026-01-10 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d03f48b921'
down_revision: Union[str, None] = 'b1f02e37a810'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create containers and deployments tables."""
    
    # Create container_status enum (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE containerstatus AS ENUM ('pending', 'building', 'created', 'running', 'stopped', 'error', 'destroyed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create deployment_status enum  
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE deploymentstatus AS ENUM ('pending', 'building', 'deploying', 'active', 'inactive', 'failed', 'destroyed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create containers table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS containers (
            id VARCHAR(64) PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL UNIQUE,
            image VARCHAR(500) NOT NULL,
            image_tag VARCHAR(255) NOT NULL DEFAULT 'latest',
            status containerstatus NOT NULL DEFAULT 'pending',
            status_message TEXT,
            git_commit_sha VARCHAR(40),
            git_branch VARCHAR(100) NOT NULL DEFAULT 'main',
            port INTEGER NOT NULL DEFAULT 80,
            host_port INTEGER,
            cpu_limit FLOAT NOT NULL DEFAULT 0.5,
            memory_limit_mb INTEGER NOT NULL DEFAULT 512,
            is_preview BOOLEAN NOT NULL DEFAULT FALSE,
            auto_restart BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            started_at TIMESTAMP,
            stopped_at TIMESTAMP,
            build_duration_seconds INTEGER,
            build_logs TEXT
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_containers_project_id ON containers(project_id);")
    
    # Create deployments table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS deployments (
            id VARCHAR(36) PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            container_id VARCHAR(64) REFERENCES containers(id) ON DELETE SET NULL,
            subdomain VARCHAR(100) NOT NULL UNIQUE,
            url VARCHAR(500) NOT NULL,
            status deploymentstatus NOT NULL DEFAULT 'pending',
            status_message TEXT,
            framework VARCHAR(50) NOT NULL DEFAULT 'unknown',
            git_commit_sha VARCHAR(40),
            git_branch VARCHAR(100) NOT NULL DEFAULT 'main',
            is_preview BOOLEAN NOT NULL DEFAULT FALSE,
            is_production BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            deployed_at TIMESTAMP
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_deployments_project_id ON deployments(project_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_deployments_container_id ON deployments(container_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_deployments_subdomain ON deployments(subdomain);")


def downgrade() -> None:
    """Drop containers and deployments tables."""
    op.drop_table('deployments')
    op.drop_table('containers')
    op.execute("DROP TYPE IF EXISTS deploymentstatus")
    op.execute("DROP TYPE IF EXISTS containerstatus")
