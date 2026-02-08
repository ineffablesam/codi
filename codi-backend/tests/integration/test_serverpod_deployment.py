"""Integration test for Flutter-Serverpod project creation and deployment."""
import pytest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models.project import Project, ProjectStatus
from app.models.environment_variable import EnvironmentVariable
from app.models.agent_task import AgentTask
from app.models.operation_log import OperationLog
from app.models.user import User
from app.core.config import settings
from app.workflows.executor import run_workflow
import asyncio
import time


@pytest.fixture
async def db_session():
    """Create a database session for testing."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_serverpod_project_creation():
    """Test creating a Flutter-Serverpod project with environment management."""
    from app.api.v1.routes.projects import create_project
    from app.schemas.project import ProjectCreate
    
    # Create database session
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get the first user from database (assuming single user exists)
        result = await session.execute(select(User).limit(1))
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            pytest.skip("No user found in database. Create a user first.")
        
        print(f"Using user: {test_user.email}")
        
        # Create project (without app_idea to avoid background task)
        project_data = ProjectCreate(
            name="test-serverpod-app",
            description="A serverpod app for testing",
            framework="flutter",
            backend_type="serverpod",
            platform_type="web",
            is_private=True,
        )
        
        # Call the create_project endpoint
        project_response = await create_project(
            project_data=project_data,
            session=session,
            current_user=test_user,
        )
        
        print(f"Created project: {project_response.name} (ID: {project_response.id})")
        
        assert project_response.id is not None
        assert project_response.name == "test-serverpod-app"
        assert project_response.backend_type == "serverpod"
        
        # Run agent task IN-PROCESS for monitoring
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        app_idea = "A simple todo list app with task creation, completion, and deletion"
        
        print("\n--- Starting In-Process Agent Workflow ---")
        start_time = time.time()
        
        # We need to manually add the task to DB since we're bypassing the API for the task submission
        agent_task = AgentTask(
            id=task_id,
            project_id=project_response.id,
            user_id=test_user.id,
            status="queued",
            message=app_idea,
        )
        session.add(agent_task)
        await session.commit()
        
        try:
            result = await run_workflow(
                project_id=project_response.id,
                user_id=test_user.id,
                task_id=task_id,
                user_message=app_idea,
                project_folder=project_response.local_path,
            )
            
            duration = time.time() - start_time
            print(f"\n--- Agent Workflow Completed in {duration:.2f}s ---")
            
            if result.get('has_error'):
                print(f"Agent Error: {result.get('error')}")
                assert False, f"Agent workflow failed: {result.get('error')}"
            
            print("Agent Workflow Succeeded!")
            
        except Exception as e:
            print(f"Exception during agent workflow: {e}")
            raise
        
        # Verify environment variables were created
        result = await session.execute(
            select(EnvironmentVariable).where(
                EnvironmentVariable.project_id == project_response.id
            )
        )
        env_vars = list(result.scalars().all())
        
        print(f"Found {len(env_vars)} environment variables")
        assert len(env_vars) > 0, "No environment variables were created"
        
        # Verify PROJECT_NAME has correct value
        project_name_var = next(v for v in env_vars if v.key == "PROJECT_NAME")
        project_name_value = project_name_var.get_value()
        print(f"PROJECT_NAME value: {project_name_value}")
        assert "test-serverpod-app" in project_name_value
        
        # Verify .env file was created
        project_path = Path(project_response.local_path)
        env_file = project_path / ".env"
        assert env_file.exists(), f".env file not found at {env_file}"
        
        print("✓ All assertions passed!")
        
    await engine.dispose()


@pytest.mark.asyncio
async def test_environment_api_basic():
    """Test basic environment variable API operations."""
    from app.services.domain.environment import EnvironmentService
    
    # Create database session
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get the first user
        result = await session.execute(select(User).limit(1))
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            pytest.skip("No user found in database")
        
        # Get the first project
        result = await session.execute(
            select(Project).where(Project.owner_id == test_user.id).limit(1)
        )
        test_project = result.scalar_one_or_none()
        
        if not test_project:
            pytest.skip("No project found. Run test_serverpod_project_creation first.")
        
        print(f"Testing with project: {test_project.name} (ID: {test_project.id})")
        
        # Test environment service
        result = await session.execute(
            select(EnvironmentVariable).where(
                EnvironmentVariable.project_id == test_project.id
            )
        )
        env_vars = list(result.scalars().all())
        
        assert len(env_vars) > 0
        
        # Test .env file generation
        env_content = EnvironmentService.generate_env_file_content(env_vars)
        assert len(env_content) > 0
        assert "PROJECT_NAME=" in env_content
        
        print("✓ Environment API test passed!")
        
    await engine.dispose()


if __name__ == "__main__":
    import asyncio
    print("Running Serverpod integration tests...")
    asyncio.run(test_serverpod_project_creation())
    asyncio.run(test_environment_api_basic())
