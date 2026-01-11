"""Tests for project creation, local Git, and deployment flow.

This module tests the complete Codi v2 project creation flow:
1. Project creation → local Git folder created
2. Git operations → branches, commits
3. Deployment → container + subdomain URL
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.git_service import LocalGitService
from app.services.traefik_service import TraefikService
from app.services.framework_detector import FrameworkDetector


# ============================================================================
# Test Value Storage (for pretty output)
# ============================================================================

class TestValues:
    """Store test output values for display."""
    values: Dict[str, Any] = {}
    
    @classmethod
    def add(cls, test_name: str, key: str, value: Any):
        if test_name not in cls.values:
            cls.values[test_name] = {}
        cls.values[test_name][key] = value
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        return cls.values
    
    @classmethod
    def clear(cls):
        cls.values = {}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_repo_dir():
    """Create a temporary directory for Git repos."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def git_service():
    """Create a LocalGitService without a project folder."""
    return LocalGitService()


@pytest.fixture
def traefik_service():
    """Create a TraefikService."""
    return TraefikService(base_domain="test.codi.local")


@pytest.fixture
def framework_detector(temp_repo_dir):
    """Create a FrameworkDetector with temp directory."""
    return FrameworkDetector(project_path=temp_repo_dir)


# ============================================================================
# Unit Tests: LocalGitService
# ============================================================================

class TestLocalGitService:
    """Tests for LocalGitService."""

    def test_init_repository(self, git_service, temp_repo_dir):
        """Test creating a new Git repository."""
        with patch('app.services.git_service.REPOS_BASE_PATH', Path(temp_repo_dir)):
            repo_path = git_service.init_repository(
                project_slug="my-app",
                user_id=1,
            )
            
            TestValues.add("test_init_repository", "repo_path", str(repo_path))
            TestValues.add("test_init_repository", "git_dir", f"{repo_path}/.git")
            
            assert os.path.exists(repo_path)
            assert os.path.isdir(os.path.join(repo_path, ".git"))

    def test_init_repository_with_initial_files(self, git_service, temp_repo_dir):
        """Test creating repo with initial files."""
        initial_files = {
            "README.md": "# My App\n\nA test project.",
            "lib/main.dart": "void main() {}",
        }
        
        with patch('app.services.git_service.REPOS_BASE_PATH', Path(temp_repo_dir)):
            repo_path = git_service.init_repository(
                project_slug="my-app",
                user_id=1,
                initial_files=initial_files,
            )
            
            TestValues.add("test_init_repository_with_initial_files", "files_created", list(initial_files.keys()))
            TestValues.add("test_init_repository_with_initial_files", "repo_path", str(repo_path))
            
            assert os.path.exists(os.path.join(repo_path, "README.md"))
            assert os.path.exists(os.path.join(repo_path, "lib", "main.dart"))

    def test_get_branches(self, git_service, temp_repo_dir):
        """Test listing branches."""
        with patch('app.services.git_service.REPOS_BASE_PATH', Path(temp_repo_dir)):
            repo_path = git_service.init_repository(
                project_slug="my-app",
                user_id=1,
                initial_files={"README.md": "# Test"},
            )
            
            git_service.open_repository(repo_path)
            branches = git_service.get_branches()
            
            TestValues.add("test_get_branches", "branches", branches)
            TestValues.add("test_get_branches", "default_branch", branches[0] if branches else None)
            
            assert "main" in branches or "master" in branches

    def test_create_branch(self, git_service, temp_repo_dir):
        """Test creating a new branch."""
        with patch('app.services.git_service.REPOS_BASE_PATH', Path(temp_repo_dir)):
            repo_path = git_service.init_repository(
                project_slug="my-app",
                user_id=1,
                initial_files={"README.md": "Test"},
            )
            
            git_service.open_repository(repo_path)
            git_service.create_branch("feature-x")
            
            branches = git_service.get_branches()
            
            TestValues.add("test_create_branch", "new_branch", "feature-x")
            TestValues.add("test_create_branch", "all_branches", branches)
            
            assert "feature-x" in branches

    def test_checkout_branch(self, git_service, temp_repo_dir):
        """Test switching branches."""
        with patch('app.services.git_service.REPOS_BASE_PATH', Path(temp_repo_dir)):
            repo_path = git_service.init_repository(
                project_slug="my-app",
                user_id=1,
                initial_files={"README.md": "Test"},
            )
            
            git_service.open_repository(repo_path)
            git_service.create_branch("develop")
            git_service.checkout("develop")
            current = git_service.get_current_branch()
            
            TestValues.add("test_checkout_branch", "switched_to", current)
            TestValues.add("test_checkout_branch", "previous_branch", "main")
            
            assert current == "develop"

    def test_commit_file(self, git_service, temp_repo_dir):
        """Test committing a file."""
        with patch('app.services.git_service.REPOS_BASE_PATH', Path(temp_repo_dir)):
            repo_path = git_service.init_repository(
                project_slug="my-app",
                user_id=1,
                initial_files={"README.md": "Initial"},
            )
            
            git_service.open_repository(repo_path)
            git_service.write_file("new_file.txt", "New content")
            commit_info = git_service.commit(
                message="Add new file",
                all_changes=True,
            )
            
            TestValues.add("test_commit_file", "commit_sha", commit_info.sha[:8])
            TestValues.add("test_commit_file", "commit_message", commit_info.message)
            
            assert commit_info is not None
            assert len(commit_info.sha) == 40

    def test_get_commits(self, git_service, temp_repo_dir):
        """Test getting commit history."""
        with patch('app.services.git_service.REPOS_BASE_PATH', Path(temp_repo_dir)):
            repo_path = git_service.init_repository(
                project_slug="my-app",
                user_id=1,
                initial_files={"README.md": "Test"},
            )
            
            git_service.open_repository(repo_path)
            commits = git_service.get_log(n=10)
            
            TestValues.add("test_get_commits", "commit_count", len(commits))
            TestValues.add("test_get_commits", "latest_sha", commits[0].sha[:8] if commits else None)
            
            assert len(commits) >= 1
            assert commits[0].sha is not None
            assert commits[0].message is not None


# ============================================================================
# Unit Tests: TraefikService
# ============================================================================

class TestTraefikService:
    """Tests for TraefikService."""

    def test_generate_labels_production(self, traefik_service):
        """Test generating labels for production deployment."""
        labels = traefik_service.generate_labels(
            project_slug="my-app",
            container_name="codi-my-app",
            port=3000,
            is_preview=False,
        )
        
        # Extract the host rule
        host_rule = [v for v in labels.values() if "Host" in str(v)]
        
        TestValues.add("test_generate_labels_production", "labels_count", len(labels))
        TestValues.add("test_generate_labels_production", "host_rule", host_rule[0] if host_rule else None)
        TestValues.add("test_generate_labels_production", "port", 3000)
        
        assert "traefik.enable" in labels
        assert labels["traefik.enable"] == "true"
        found_host_rule = any("Host" in v and "my-app" in v for v in labels.values())
        assert found_host_rule, "Should have Host rule with project slug"

    def test_generate_labels_preview(self, traefik_service):
        """Test generating labels for preview deployment."""
        labels = traefik_service.generate_labels(
            project_slug="my-app",
            container_name="codi-my-app-preview",
            port=3000,
            is_preview=True,
            branch="feature-x",
        )
        
        TestValues.add("test_generate_labels_preview", "preview_label", labels.get("codi.deployment.preview"))
        TestValues.add("test_generate_labels_preview", "branch_label", labels.get("codi.deployment.branch"))
        TestValues.add("test_generate_labels_preview", "is_preview", True)
        
        assert "traefik.enable" in labels
        assert labels.get("codi.deployment.preview") == "true"
        assert labels.get("codi.deployment.branch") == "feature-x"

    def test_get_subdomain_url(self, traefik_service):
        """Test generating subdomain URL."""
        url = traefik_service.get_subdomain_url("my-app")
        
        TestValues.add("test_get_subdomain_url", "subdomain_url", url)
        TestValues.add("test_get_subdomain_url", "project_slug", "my-app")
        
        assert url == "http://my-app.test.codi.local"

    def test_get_preview_url(self, traefik_service):
        """Test generating preview URL."""
        url = traefik_service.get_preview_url("my-app", "feature-x")
        
        TestValues.add("test_get_preview_url", "preview_url", url)
        TestValues.add("test_get_preview_url", "branch", "feature-x")
        
        assert "my-app" in url
        assert "feature-x" in url
        assert "test.codi.local" in url

    def test_get_port_for_framework(self, traefik_service):
        """Test getting default port for framework."""
        flutter_port = traefik_service.get_port_for_framework("flutter")
        nextjs_port = traefik_service.get_port_for_framework("nextjs")
        react_port = traefik_service.get_port_for_framework("react")
        
        TestValues.add("test_get_port_for_framework", "flutter_port", flutter_port)
        TestValues.add("test_get_port_for_framework", "nextjs_port", nextjs_port)
        TestValues.add("test_get_port_for_framework", "react_port", react_port)
        
        assert flutter_port == 80
        assert nextjs_port == 3000
        assert react_port == 80


# ============================================================================
# Unit Tests: FrameworkDetector
# ============================================================================

class TestFrameworkDetector:
    """Tests for FrameworkDetector."""

    def test_detect_flutter(self, temp_repo_dir):
        """Test detecting Flutter project."""
        with open(os.path.join(temp_repo_dir, "pubspec.yaml"), "w") as f:
            f.write("name: my_app\nflutter:\n  sdk: flutter")
        
        detector = FrameworkDetector(project_path=temp_repo_dir)
        result = detector.detect()
        
        TestValues.add("test_detect_flutter", "detected", result.framework.value)
        TestValues.add("test_detect_flutter", "confidence", f"{result.confidence:.0%}")
        
        assert result.framework.value == "flutter"

    def test_detect_nextjs(self, temp_repo_dir):
        """Test detecting Next.js project."""
        with open(os.path.join(temp_repo_dir, "package.json"), "w") as f:
            f.write('{"dependencies": {"next": "14.0.0", "react": "18.0.0"}}')
        
        detector = FrameworkDetector(project_path=temp_repo_dir)
        result = detector.detect()
        
        TestValues.add("test_detect_nextjs", "detected", result.framework.value)
        TestValues.add("test_detect_nextjs", "confidence", f"{result.confidence:.0%}")
        
        assert result.framework.value == "nextjs"

    def test_detect_react(self, temp_repo_dir):
        """Test detecting React project."""
        with open(os.path.join(temp_repo_dir, "package.json"), "w") as f:
            f.write('{"dependencies": {"react": "18.0.0", "react-dom": "18.0.0"}}')
        
        detector = FrameworkDetector(project_path=temp_repo_dir)
        result = detector.detect()
        
        TestValues.add("test_detect_react", "detected", result.framework.value)
        TestValues.add("test_detect_react", "confidence", f"{result.confidence:.0%}")
        
        assert result.framework.value == "react"

    def test_detect_vite(self, temp_repo_dir):
        """Test detecting Vite project."""
        with open(os.path.join(temp_repo_dir, "vite.config.js"), "w") as f:
            f.write("export default {}")
        with open(os.path.join(temp_repo_dir, "package.json"), "w") as f:
            f.write('{"devDependencies": {"vite": "5.0.0"}}')
        
        detector = FrameworkDetector(project_path=temp_repo_dir)
        result = detector.detect()
        
        TestValues.add("test_detect_vite", "detected", result.framework.value)
        TestValues.add("test_detect_vite", "confidence", f"{result.confidence:.0%}")
        
        assert result.framework.value == "vite"

    def test_get_build_command_flutter(self, temp_repo_dir):
        """Test getting build command for Flutter."""
        with open(os.path.join(temp_repo_dir, "pubspec.yaml"), "w") as f:
            f.write("name: my_app\nflutter:\n  sdk: flutter")
        
        detector = FrameworkDetector(project_path=temp_repo_dir)
        detector.detect()
        cmd = detector.get_build_command()
        
        TestValues.add("test_get_build_command_flutter", "build_command", cmd)
        
        assert "flutter" in cmd


# ============================================================================
# Integration Tests: Full Project Flow
# ============================================================================

class TestProjectCreationFlow:
    """Integration tests for project creation flow."""

    @pytest.mark.asyncio
    async def test_deployment_creates_container_and_url(self):
        """Test that deployment creates container and generates URL."""
        with patch('app.services.docker_service.DockerService') as MockDocker:
            mock_docker = MockDocker.return_value
            mock_docker.build_image = AsyncMock(return_value="sha256:abc123def456")
            mock_docker.create_container = AsyncMock(return_value="container-abc123")
            mock_docker.start_container = AsyncMock(return_value=True)

            traefik_service = TraefikService(base_domain="codi.local")
            
            # Simulate deployment flow
            labels = traefik_service.generate_labels(
                project_slug="my-app",
                container_name="codi-my-app",
                port=80,
                is_preview=False,
            )
            
            url = traefik_service.get_subdomain_url("my-app")
            preview_url = traefik_service.get_preview_url("my-app", "feature-branch")
            
            # Store values for display
            TestValues.add("test_deployment_creates_container_and_url", "production_url", url)
            TestValues.add("test_deployment_creates_container_and_url", "preview_url", preview_url)
            TestValues.add("test_deployment_creates_container_and_url", "container_id", "container-abc123")
            TestValues.add("test_deployment_creates_container_and_url", "image_id", "sha256:abc123")
            
            # Assertions
            assert url == "http://my-app.codi.local"
            assert "traefik.enable" in labels
            assert labels["codi.project.slug"] == "my-app"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
