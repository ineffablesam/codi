"""E2E tests for project creation with automatic app generation from idea."""
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.agent_task import AgentTask
from app.models.user import User
from app.main import app

@pytest.mark.asyncio
async def test_create_project_with_app_idea_triggers_agent(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_user_data: dict,
):
    """Test that creating a project with an app_idea triggers the agent workflow."""
    
    # 1. Create a user
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Mock authentication
    # Mock authentication using dependency overrides
    from app.api.v1.deps import get_current_user
    async def override_get_current_user():
        return user
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        # Mock Git and Template services
        with patch("app.api.v1.routes.projects.get_git_service") as mock_get_git, \
             patch("app.api.v1.routes.projects.StarterTemplateService") as mock_template_service, \
             patch("app.tasks.celery_app.run_agent_workflow_task.delay") as mock_run_task:
            
            # Setup mock git service
            mock_git = MagicMock()
            mock_git.init_repository.return_value = "/tmp/test-project"
            mock_git.get_current_commit.return_value = "fake-sha"
            mock_get_git.return_value = mock_git
            
            # Setup mock template service
            mock_template = MagicMock()
            mock_template.push_template_to_repo = AsyncMock()
            mock_template_service.return_value = mock_template
            
            app_idea = "A church app with events and sermon list"
            project_data = {
                "name": "My Church App",
                "description": "Test app",
                "app_idea": app_idea,
                "framework": "flutter",
                "platform_type": "mobile"
            }
            
            # 3. Request project creation
            response = await client.post(
                "/api/v1/projects",
                json=project_data,
                headers={"Authorization": "Bearer fake-token"}
            )
            
            # 4. Assertions
            if response.status_code != 201:
                print(f"DEBUG: Response status {response.status_code}, Body: {response.json()}")
            assert response.status_code == 201
            data = response.json()
            project_id = data["id"]
            assert data["name"] == "My Church App"
            
            # Verify project exists in DB
            result = await db_session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            assert project is not None
            
            # Verify AgentTask was created
            result = await db_session.execute(select(AgentTask).where(AgentTask.project_id == project_id))
            tasks = result.scalars().all()
            assert len(tasks) == 1
            assert app_idea in tasks[0].message
            assert tasks[0].status == "queued"
            
            # Verify Celery task was called with correct arguments
            mock_run_task.assert_called_once()
            args, kwargs = mock_run_task.call_args
            assert kwargs["project_id"] == project_id
            assert kwargs["user_id"] == user.id
            assert app_idea in kwargs["user_message"]
            assert "project_folder" in kwargs
    finally:
        del app.dependency_overrides[get_current_user]

@pytest.mark.asyncio
async def test_create_project_without_app_idea_does_not_trigger_agent(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_user_data: dict,
):
    """Test that creating a project without app_idea does NOT trigger agent workflow."""
    
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    from app.api.v1.deps import get_current_user
    async def override_get_current_user():
        return user
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        # Mock Git and Template services
        with patch("app.api.v1.routes.projects.get_git_service") as mock_get_git, \
             patch("app.api.v1.routes.projects.StarterTemplateService") as mock_template_service, \
             patch("app.tasks.celery_app.run_agent_workflow_task.delay") as mock_run_task:
            
            # Setup mock git service
            mock_git = MagicMock()
            mock_git.init_repository.return_value = "/tmp/test-project"
            mock_git.get_current_commit.return_value = "fake-sha"
            mock_get_git.return_value = mock_git
            
            # Setup mock template service
            mock_template = MagicMock()
            mock_template.push_template_to_repo = AsyncMock()
            mock_template_service.return_value = mock_template
            
            project_data = {
                "name": "Simple App",
                "framework": "flutter"
            }
            
            response = await client.post(
                "/api/v1/projects",
                json=project_data,
                headers={"Authorization": "Bearer fake-token"}
            )
            
            assert response.status_code == 201
            mock_run_task.assert_not_called()
            
            # Verify NO AgentTask was created
            data = response.json()
            project_id = data["id"]
            result = await db_session.execute(select(AgentTask).where(AgentTask.project_id == project_id))
            tasks = result.scalars().all()
            assert len(tasks) == 0
    finally:
        del app.dependency_overrides[get_current_user]
