"""Pytest configuration and fixtures."""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, get_db_session
from app.main import app

# Test database URL
TEST_DATABASE_URL = settings.database_url.replace(
    "codi_db", "codi_test_db"
) if "codi_db" in settings.database_url else "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# Test session factory
TestAsyncSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test.

    Yields:
        AsyncSession for database operations
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestAsyncSessionLocal() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override.

    Args:
        db_session: Test database session

    Yields:
        AsyncClient for making test requests
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for tests.

    Returns:
        Dictionary with user fields
    """
    return {
        "github_id": 12345,
        "github_username": "testuser",
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def sample_project_data() -> dict:
    """Sample project data for tests.

    Returns:
        Dictionary with project fields
    """
    return {
        "name": "Test Project",
        "description": "A test Flutter project",
        "is_private": False,
    }


@pytest.fixture
def auth_headers() -> dict:
    """Generate fake auth headers for testing.

    Returns:
        Dictionary with Authorization header
    """
    # In real tests, you'd generate a proper JWT
    return {"Authorization": "Bearer fake-token-for-testing"}
