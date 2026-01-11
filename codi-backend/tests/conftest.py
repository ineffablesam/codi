"""Pytest configuration and fixtures with colorful output."""
import asyncio
from collections import defaultdict
from typing import AsyncGenerator, Generator, Dict, List, Any

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


# =============================================================================
# Test Result Collector for Pretty Summary
# =============================================================================

class TestResultCollector:
    """Collects test results for pretty summary."""
    
    def __init__(self):
        self.results: Dict[str, List[Dict]] = defaultdict(list)
        self.passed = 0
        self.failed = 0
        self.skipped = 0
    
    def add_result(self, category: str, name: str, status: str, duration: float = 0):
        self.results[category].append({
            "name": name,
            "status": status,
            "duration": duration,
        })
        if status == "passed":
            self.passed += 1
        elif status == "failed":
            self.failed += 1
        else:
            self.skipped += 1


# Global collector
_collector = TestResultCollector()


def get_test_category(nodeid: str) -> str:
    """Extract test category from node ID."""
    if "LocalGitService" in nodeid:
        return "🔀 Git Operations"
    elif "TraefikService" in nodeid:
        return "🌐 Traefik Routing"
    elif "FrameworkDetector" in nodeid:
        return "🔍 Framework Detection"
    elif "ProjectCreationFlow" in nodeid:
        return "🚀 Deployment Flow"
    return "📋 Other Tests"


def get_test_name(nodeid: str) -> str:
    """Extract clean test name from node ID."""
    if "::" in nodeid:
        name = nodeid.split("::")[-1]
        name = name.replace("test_", "").replace("_", " ").title()
        return name
    return nodeid


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to collect test results."""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call":
        category = get_test_category(item.nodeid)
        name = get_test_name(item.nodeid)
        status = report.outcome
        duration = report.duration
        _collector.add_result(category, name, status, duration)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print beautiful test summary using rich."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich import box
        
        # Import TestValues from test file
        try:
            from tests.test_project_flow import TestValues
            test_values = TestValues.get_all()
        except ImportError:
            test_values = {}
        
        console = Console()
        
        # Header
        console.print()
        console.print(Panel.fit(
            "[bold cyan]🧪 Codi v2 Test Summary[/bold cyan]",
            border_style="cyan",
        ))
        console.print()
        
        # Category icons and colors
        category_styles = {
            "🔀 Git Operations": "green",
            "🌐 Traefik Routing": "blue",
            "🔍 Framework Detection": "yellow",
            "🚀 Deployment Flow": "magenta",
            "📋 Other Tests": "white",
        }
        
        # Print each category
        for category, tests in _collector.results.items():
            style = category_styles.get(category, "white")
            
            table = Table(
                title=f"[bold {style}]{category}[/bold {style}]",
                box=box.ROUNDED,
                show_header=True,
                header_style=f"bold {style}",
                expand=True,
            )
            table.add_column("Test", style="white", no_wrap=True)
            table.add_column("Status", justify="center", width=8)
            table.add_column("Output Values", style="dim cyan", ratio=2)
            
            for test in tests:
                # Status with emoji
                if test["status"] == "passed":
                    status = "[green]✓ PASS[/green]"
                elif test["status"] == "failed":
                    status = "[red]✗ FAIL[/red]"
                else:
                    status = "[yellow]○ SKIP[/yellow]"
                
                # Get test values
                test_key = "test_" + test["name"].lower().replace(" ", "_")
                values = test_values.get(test_key, {})
                
                # Format values nicely
                if values:
                    value_strs = []
                    for k, v in values.items():
                        if isinstance(v, list):
                            v = ", ".join(str(x) for x in v)
                        value_strs.append(f"[cyan]{k}[/cyan]=[white]{v}[/white]")
                    value_display = " | ".join(value_strs[:3])  # Show max 3
                else:
                    value_display = "[dim]—[/dim]"
                
                table.add_row(test["name"], status, value_display)
            
            console.print(table)
            console.print()
        
        # Highlight key URLs section
        if test_values:
            console.print(Panel.fit(
                "[bold white]🔗 Generated URLs & Values[/bold white]",
                border_style="blue",
            ))
            
            url_table = Table(box=box.SIMPLE, show_header=False)
            url_table.add_column("Key", style="cyan", width=25)
            url_table.add_column("Value", style="green")
            
            # Extract important values
            important_keys = [
                ("Production URL", "test_get_subdomain_url", "subdomain_url"),
                ("Preview URL", "test_get_preview_url", "preview_url"),
                ("Deploy URL", "test_deployment_creates_container_and_url", "production_url"),
                ("Deploy Preview", "test_deployment_creates_container_and_url", "preview_url"),
                ("Container ID", "test_deployment_creates_container_and_url", "container_id"),
                ("Flutter Port", "test_get_port_for_framework", "flutter_port"),
                ("Next.js Port", "test_get_port_for_framework", "nextjs_port"),
            ]
            
            for label, test_name, key in important_keys:
                if test_name in test_values and key in test_values[test_name]:
                    url_table.add_row(label, str(test_values[test_name][key]))
            
            console.print(url_table)
            console.print()
        
        # Summary stats
        total = _collector.passed + _collector.failed + _collector.skipped
        
        if _collector.failed == 0:
            summary_style = "bold green"
            summary_text = f"✅ All {_collector.passed} tests passed!"
        else:
            summary_style = "bold red"
            summary_text = f"❌ {_collector.failed} failed, {_collector.passed} passed"
        
        stats_table = Table(box=box.SIMPLE, show_header=False)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", justify="right")
        stats_table.add_row("Total Tests", str(total))
        stats_table.add_row("Passed", f"[green]{_collector.passed}[/green]")
        stats_table.add_row("Failed", f"[red]{_collector.failed}[/red]")
        stats_table.add_row("Skipped", f"[yellow]{_collector.skipped}[/yellow]")
        
        console.print(Panel(
            stats_table,
            title=f"[{summary_style}]{summary_text}[/{summary_style}]",
            border_style="cyan",
        ))
        console.print()
        
    except ImportError:
        pass


# =============================================================================
# Original Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for tests."""
    return {
        "github_id": 12345,
        "github_username": "testuser",
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def sample_project_data() -> dict:
    """Sample project data for tests."""
    return {
        "name": "Test Project",
        "description": "A test Flutter project",
        "is_private": False,
    }


@pytest.fixture
def auth_headers() -> dict:
    """Generate fake auth headers for testing."""
    return {"Authorization": "Bearer fake-token-for-testing"}
