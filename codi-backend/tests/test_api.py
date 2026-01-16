"""Basic API tests for Codi backend."""
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test health endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_redirect():
    """Test root redirects to docs."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/", follow_redirects=False)
        # Should redirect to /docs
        assert response.status_code in [301, 302, 307, 308]
