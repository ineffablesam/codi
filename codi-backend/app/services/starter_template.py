"""Starter template service for initializing new Flutter projects."""
import base64
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.github import GitHubService
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Directory patterns to exclude when reading the template
EXCLUDE_DIRS = {
    ".dart_tool",
    ".idea",
    "build",
    ".git",
    "android",
    "ios",
    ".pub-cache",
    ".pub",
}

# File patterns to exclude
EXCLUDE_FILES = {
    ".metadata",
    "pubspec.lock",
    ".iml",
}

# The deployment workflow to add to new projects
DEPLOY_WORKFLOW = '''name: Deploy Flutter Web

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      deploy_target:
        description: 'Deployment target'
        required: true
        default: 'github_pages'
        type: choice
        options:
          - github_pages
          - vercel
      environment:
        description: 'Deployment environment'
        required: true
        default: 'production'
        type: choice
        options:
          - production
          - staging

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false


jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      build_success: ${{ steps.build.outcome == 'success' }}
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          channel: 'stable'
          cache: true
          cache-key: 'flutter-:os:-:channel:-:version:-:arch:-:hash:'
          cache-path: '${{ runner.tool_cache }}/flutter/:channel:-:version:-:arch:'

      - name: Verify Flutter installation
        run: |
          flutter --version
          flutter doctor -v

      - name: Get dependencies
        run: flutter pub get

      - name: Analyze code
        run: flutter analyze --no-fatal-infos
        continue-on-error: true

      - name: Build Flutter web
        id: build
        run: |
          flutter build web --release --base-href "/${{ github.event.repository.name }}/"
          echo "Build completed successfully"

      - name: Verify build output
        run: |
          ls -la build/web/
          test -f build/web/index.html

      - name: Setup Pages
        if: github.event_name != 'pull_request'
        uses: actions/configure-pages@v4

      - name: Upload artifact for Pages
        if: github.event_name != 'pull_request'
        uses: actions/upload-pages-artifact@v3
        with:
          path: 'build/web'

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: flutter-web-build
          path: build/web
          retention-days: 7

  deploy-pages:
    if: github.event_name != 'pull_request' && (github.event.inputs.deploy_target == 'github_pages' || github.event.inputs.deploy_target == '')
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4

      - name: Output deployment URL
        run: |
          echo "::notice::Deployed to ${{ steps.deployment.outputs.page_url }}"

  deploy-vercel:
    if: github.event.inputs.deploy_target == 'vercel'
    runs-on: ubuntu-latest
    needs: build
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download build artifact
        uses: actions/download-artifact@v4
        with:
          name: flutter-web-build
          path: build/web

      - name: Install Vercel CLI
        run: npm install --global vercel@latest

      - name: Deploy to Vercel
        id: vercel-deploy
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: |
          cd build/web
          if [ "${{ github.event.inputs.environment }}" == "production" ]; then
            vercel deploy --prod --token=$VERCEL_TOKEN --yes
          else
            vercel deploy --token=$VERCEL_TOKEN --yes
          fi

  notify:
    if: always()
    runs-on: ubuntu-latest
    needs: [build, deploy-pages]
    
    steps:
      - name: Check deployment status
        run: |
          if [ "${{ needs.build.result }}" == "success" ]; then
            echo "::notice::Build completed successfully"
          else
            echo "::error::Build failed"
          fi
          
          if [ "${{ needs.deploy-pages.result }}" == "success" ]; then
            echo "::notice::Deployment to GitHub Pages completed"
          elif [ "${{ needs.deploy-pages.result }}" == "failure" ]; then
            echo "::error::Deployment to GitHub Pages failed"
          fi
'''


class StarterTemplateService:
    """Service for managing Flutter starter templates from the codiexample directory."""

    # Path to the codiexample template directory
    TEMPLATE_DIR = Path(__file__).parent.parent.parent / "codiexample"

    def __init__(self, github_service: Optional[GitHubService] = None) -> None:
        """Initialize starter template service.

        Args:
            github_service: Optional GitHubService instance for pushing to GitHub
        """
        self.github_service = github_service

    def _should_include_path(self, path: Path) -> bool:
        """Check if a file path should be included in the template.

        Args:
            path: Path to check

        Returns:
            True if the path should be included
        """
        # Check if any parent directory is in exclude list
        for part in path.parts:
            if part in EXCLUDE_DIRS:
                return False

        # Check file extensions and names
        if path.name in EXCLUDE_FILES:
            return False
        if path.suffix == ".iml":
            return False

        return True

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is binary
        """
        binary_extensions = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".ttf", ".otf", ".woff", ".woff2"}
        return file_path.suffix.lower() in binary_extensions

    def get_template_files(
        self,
        project_name: str,
        project_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get starter template files from the codiexample directory.

        Args:
            project_name: Name of the project (snake_case or kebab-case)
            project_title: Human-readable project title

        Returns:
            Dictionary mapping file paths to file contents (str for text, bytes for binary)
        """
        if project_title is None:
            project_title = project_name.replace("_", " ").replace("-", " ").title()

        repo_name = GitHubService.slugify(project_name)
        
        # Ensure name is a valid Dart identifier (only lowercase, digits, and underscores)
        import re
        dart_package_name = re.sub(r'[^a-z0-9_]', '_', project_name.lower())
        if dart_package_name and (not dart_package_name[0].isalpha() and dart_package_name[0] != '_'):
            dart_package_name = "app_" + dart_package_name

        if not self.TEMPLATE_DIR.exists():
            logger.error(f"Template directory not found: {self.TEMPLATE_DIR}")
            raise ValueError(f"Template directory not found: {self.TEMPLATE_DIR}")

        files: Dict[str, Any] = {}

        # Walk through the template directory
        for file_path in self.TEMPLATE_DIR.rglob("*"):
            if file_path.is_dir():
                continue

            # Get relative path from template directory
            rel_path = file_path.relative_to(self.TEMPLATE_DIR)

            if not self._should_include_path(rel_path):
                continue

            try:
                if self._is_binary_file(file_path):
                    # Read binary files
                    content = file_path.read_bytes()
                    files[str(rel_path)] = {"content": content, "is_binary": True}
                else:
                    # Read text files and perform replacements
                    content = file_path.read_text(encoding="utf-8")

                    # Replace placeholders in text files
                    if file_path.suffix == ".dart":
                        # Update internal package imports
                        content = content.replace("package:codiexample/", f"package:{dart_package_name}/")
                    
                    if file_path.name == "pubspec.yaml":
                        # Update the package name
                        content = content.replace("name: codiexample", f"name: {dart_package_name}")
                        # Ensure SDK version is compatible with modern lints (3.5.0+)
                        # But avoid hardcoding too strictly to allow range matching
                        for old_sdk in ['sdk: ">=3.0.0 <4.0.0"', "sdk: '>=3.0.0 <4.0.0'", 
                                       'sdk: ">=3.8.0 <4.0.0"', "sdk: '>=3.8.0 <4.0.0'"]:
                            content = content.replace(old_sdk, 'sdk: ">=3.5.0 <4.0.0"')
                    elif file_path.name == "index.html":
                        # Update the title in web/index.html
                        content = content.replace("codiexample", project_title)
                    elif file_path.name == "manifest.json":
                        # Update the manifest
                        content = content.replace("codiexample", project_title)

                    files[str(rel_path)] = {"content": content, "is_binary": False}

            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {e}")
                continue

        # Add the GitHub Actions workflow
        files[".github/workflows/flutter_web_deploy.yml"] = {
            "content": DEPLOY_WORKFLOW,
            "is_binary": False,
        }

        logger.info(f"Loaded {len(files)} template files from {self.TEMPLATE_DIR}")
        return files

    async def push_template_to_repo(
        self,
        repo_full_name: str,
        project_name: str,
        project_title: Optional[str] = None,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Push starter template to a GitHub repository.

        Args:
            repo_full_name: Full repository name (owner/repo)
            project_name: Name of the project
            project_title: Human-readable project title
            branch: Branch to push to

        Returns:
            Dictionary with commit information
        """
        if not self.github_service:
            raise ValueError("GitHub service not configured")

        template_files = self.get_template_files(project_name, project_title)

        # Convert to list of dicts for GitHub API
        files_list = []
        for path, file_info in template_files.items():
            if file_info["is_binary"]:
                # Encode binary content as base64 for the API
                content = base64.b64encode(file_info["content"]).decode("utf-8")
                files_list.append({"path": path, "content": content, "encoding": "base64"})
            else:
                files_list.append({"path": path, "content": file_info["content"]})

        # Commit all files at once
        result = self.github_service.commit_multiple_files(
            repo_full_name=repo_full_name,
            files=files_list,
            commit_message="Initial commit: Flutter starter template from Codi",
            branch=branch,
        )

        logger.info(
            f"Pushed starter template to {repo_full_name}",
            files_count=len(files_list),
            commit_sha=result.get("commit_sha"),
        )

        return result

    def create_local_template(
        self,
        output_dir: str,
        project_name: str,
        project_title: Optional[str] = None,
    ) -> Path:
        """Create starter template files locally.

        Args:
            output_dir: Directory to create template in
            project_name: Name of the project
            project_title: Human-readable project title

        Returns:
            Path to the created template directory
        """
        import shutil

        template_files = self.get_template_files(project_name, project_title)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for file_path, file_info in template_files.items():
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if file_info["is_binary"]:
                full_path.write_bytes(file_info["content"])
            else:
                full_path.write_text(file_info["content"])

        logger.info(f"Created local template at {output_path}")
        return output_path

    @classmethod
    def get_file_count(cls) -> int:
        """Get the number of files in the starter template.

        Returns:
            Number of template files
        """
        if not cls.TEMPLATE_DIR.exists():
            return 0

        count = 0
        for file_path in cls.TEMPLATE_DIR.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(cls.TEMPLATE_DIR)
                # Check exclusions
                should_include = True
                for part in rel_path.parts:
                    if part in EXCLUDE_DIRS:
                        should_include = False
                        break
                if rel_path.name in EXCLUDE_FILES or rel_path.suffix == ".iml":
                    should_include = False
                if should_include:
                    count += 1

        return count + 1  # +1 for the workflow file

    @classmethod
    def get_template_info(cls) -> Dict[str, Any]:
        """Get information about the starter template.

        Returns:
            Dictionary with template metadata
        """
        return {
            "file_count": cls.get_file_count(),
            "template_dir": str(cls.TEMPLATE_DIR),
            "features": [
                "Flutter web support",
                "Material 3 theming",
                "GitHub Actions CI/CD",
                "GitHub Pages deployment",
                "Vercel deployment option",
            ],
        }
