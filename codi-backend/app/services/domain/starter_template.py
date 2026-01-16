"""Starter template service for initializing new Flutter, React, and Next.js projects.

All templates are now created locally. No GitHub API dependency.
"""
import base64
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.infrastructure.git import get_git_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


def slugify(name: str) -> str:
    """Create a URL-safe slug from a project name.
    
    Args:
        name: Project name to slugify
        
    Returns:
        URL-safe slug
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9-]', '-', slug)
    slug = re.sub(r'-+', '-', slug)  # Remove consecutive hyphens
    slug = slug.strip('-')  # Remove leading/trailing hyphens
    return slug or "project"



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

      - name: Setup Vercel Project
        env:
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: |
          mkdir -p .vercel
          echo '{"projectId":"'$VERCEL_PROJECT_ID'","orgId":"'$VERCEL_ORG_ID'"}' > .vercel/project.json

      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
        run: |
          cd build/web
          if [ "${{ github.event.inputs.environment || 'production' }}" == "production" ]; then
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

# React/Vite deploy workflow for GitHub Pages and Vercel
REACT_DEPLOY_WORKFLOW = '''name: Deploy React App

on:
  push:
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

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          # cache: 'npm' # Disabled until package-lock.json is generated
      - run: npm install # Use install instead of ci for initial setup
      - run: npm run build
        env:
          BASE_URL: /${{ github.event.repository.name }}/
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist

  deploy-pages:
    if: __PAGES_DEFAULT__ || (github.event_name == 'workflow_dispatch' && github.event.inputs.deploy_target == 'github_pages')
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: 'dist'
      - uses: actions/deploy-pages@v4
        id: deployment

  deploy-vercel:
    if: __VERCEL_DEFAULT__ || (github.event_name == 'workflow_dispatch' && github.event.inputs.deploy_target == 'vercel')
    runs-on: ubuntu-latest
    # Remote build doesn't need local build artifact
    steps:
      - uses: actions/checkout@v4
      - name: Install Vercel CLI
        run: npm install --global vercel@latest
      - name: Setup Vercel Project
        env:
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: |
          mkdir -p .vercel
          echo '{"projectId":"'$VERCEL_PROJECT_ID'","orgId":"'$VERCEL_ORG_ID'"}' > .vercel/project.json
      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
        run: |
          if [ "${{ github.event.inputs.environment || 'production' }}" == "production" ]; then
            vercel deploy --prod --token=$VERCEL_TOKEN --yes
          else
            vercel deploy --token=$VERCEL_TOKEN --yes
          fi
'''

# Next.js deploy workflow for Vercel and GitHub Pages
NEXTJS_DEPLOY_WORKFLOW = '''name: Deploy Next.js App

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      deploy_target:
        description: 'Deployment target'
        required: true
        default: 'vercel'
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

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          # cache: 'npm' # Disabled until package-lock.json is generated
      - run: npm install # Use install instead of ci for initial setup
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: out
          path: out

  deploy-pages:
    # Default to pages if not specified or explicitly selected
    if: __PAGES_DEFAULT__ || (github.event_name == 'workflow_dispatch' && github.event.inputs.deploy_target == 'github_pages')
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: out
          path: out
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: 'out'
      - uses: actions/deploy-pages@v4
        id: deployment

  deploy-vercel:
    # Default to Vercel for Next.js on push, or if selected
    if: __VERCEL_DEFAULT__ || (github.event_name == 'workflow_dispatch' && github.event.inputs.deploy_target == 'vercel')
    runs-on: ubuntu-latest
    # Remote build doesn't need local build artifact, so we don't 'needs: build'
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Vercel CLI
        run: npm install --global vercel@latest
      - name: Setup Vercel Project
        env:
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: |
          mkdir -p .vercel
          echo '{"projectId":"'$VERCEL_PROJECT_ID'","orgId":"'$VERCEL_ORG_ID'"}' > .vercel/project.json
      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
        run: |
          if [ "${{ github.event.inputs.environment || 'production' }}" == "production" ]; then
            vercel deploy --prod --token=$VERCEL_TOKEN --yes
          else
            vercel deploy --token=$VERCEL_TOKEN --yes
          fi
'''


class StarterTemplateService:
    """Service for managing multi-framework starter templates.
    
    Supported frameworks:
    - flutter: Flutter web/mobile (Dart)
    - react: React + Vite + TypeScript
    - nextjs: Next.js 15 + App Router + TypeScript + Tailwind
    """

    # Base path to the templates directory
    # __file__ = /app/app/services/domain/starter_template.py
    # Going up 4 levels: domain -> services -> app -> app -> root
    # This resolves to /app/codi-starter-templates in Docker
    TEMPLATES_BASE = Path(__file__).parent.parent.parent.parent / "codi-starter-templates"
    
    # Framework to template directory mapping
    FRAMEWORK_DIRS = {
        "flutter": "flutter-starter",
        "react": "react-starter",
        "nextjs": "nextjs-starter",
    }
    
    # Framework-specific exclusion patterns
    FRAMEWORK_EXCLUDES = {
        "flutter": {
            "dirs": {".dart_tool", ".idea", "build", ".git", "android", "ios", ".pub-cache", ".pub"},
            "files": {".metadata", "pubspec.lock", ".iml"},
        },
        "react": {
            "dirs": {"node_modules", ".git", "dist", ".cache"},
            "files": {".DS_Store"},
        },
        "nextjs": {
            "dirs": {"node_modules", ".git", ".next", "out", ".cache"},
            "files": {".DS_Store"},
        },
    }

    def __init__(self, framework: str = "flutter", deployment_platform: str = "github_pages") -> None:
        """Initialize starter template service.

        Args:
            framework: Framework type (flutter, react, nextjs)
            deployment_platform: Target deployment platform (github_pages, vercel)
        """
        self.framework = framework
        self.deployment_platform = deployment_platform
        self._validate_framework()
    
    def _validate_framework(self) -> None:
        """Validate the framework is supported."""
        if self.framework not in self.FRAMEWORK_DIRS:
            raise ValueError(f"Unsupported framework: {self.framework}. Supported: {list(self.FRAMEWORK_DIRS.keys())}")
    
    @property
    def TEMPLATE_DIR(self) -> Path:
        """Get the template directory for the current framework."""
        return self.TEMPLATES_BASE / self.FRAMEWORK_DIRS[self.framework]

    def _should_include_path(self, path: Path) -> bool:
        """Check if a file path should be included in the template.

        Args:
            path: Path to check

        Returns:
            True if the path should be included
        """
        excludes = self.FRAMEWORK_EXCLUDES.get(self.framework, {"dirs": set(), "files": set()})
        exclude_dirs = excludes.get("dirs", set())
        exclude_files = excludes.get("files", set())
        
        # Check if any parent directory is in exclude list
        for part in path.parts:
            if part in exclude_dirs:
                return False

        # Check file names
        if path.name in exclude_files:
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
        """Get starter template files for the configured framework.

        Args:
            project_name: Name of the project (snake_case or kebab-case)
            project_title: Human-readable project title

        Returns:
            Dictionary mapping file paths to file contents (str for text, bytes for binary)
        """
        if project_title is None:
            project_title = project_name.replace("_", " ").replace("-", " ").title()

        repo_name = slugify(project_name)
        
        # Framework-specific name processing
        import re
        if self.framework == "flutter":
            # Dart package name: only lowercase, digits, and underscores
            package_name = re.sub(r'[^a-z0-9_]', '_', project_name.lower())
            if package_name and (not package_name[0].isalpha() and package_name[0] != '_'):
                package_name = "app_" + package_name
        else:
            # JavaScript/TypeScript: kebab-case
            package_name = re.sub(r'[^a-z0-9-]', '-', project_name.lower())

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
                    
                    # Apply framework-specific replacements
                    content = self._apply_replacements(content, file_path, project_name, project_title, package_name)

                    files[str(rel_path)] = {"content": content, "is_binary": False}

            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {e}")
                continue

        # Add framework-specific GitHub Actions workflow
        workflow = self._get_deploy_workflow()
        
        # Customize workflow default target based on configured deployment platform
        # We use placeholders in the workflow templates to toggle defaults
        pages_default = "github.event_name == 'push'" if self.deployment_platform == 'github_pages' else "false"
        vercel_default = "github.event_name == 'push'" if self.deployment_platform == 'vercel' else "false"
        
        workflow = workflow.replace("__PAGES_DEFAULT__", pages_default)
        workflow = workflow.replace("__VERCEL_DEFAULT__", vercel_default)
        
        workflow_name = self._get_workflow_filename()
        files[f".github/workflows/{workflow_name}"] = {
            "content": workflow,
            "is_binary": False,
        }

        logger.info(f"Loaded {len(files)} template files for {self.framework} from {self.TEMPLATE_DIR}")
        return files
    
    def _apply_replacements(self, content: str, file_path: Path, project_name: str, project_title: str, package_name: str) -> str:
        """Apply framework-specific placeholder replacements."""
        # Universal replacements
        content = content.replace("{{PROJECT_TITLE}}", project_title)
        content = content.replace("{{PROJECT_NAME}}", project_name)
        
        if self.framework == "flutter":
            if file_path.suffix == ".dart":
                content = content.replace("package:codiexample/", f"package:{package_name}/")
            
            if file_path.name == "pubspec.yaml":
                content = content.replace("name: codiexample", f"name: {package_name}")
                for old_sdk in ['sdk: ">=3.0.0 <4.0.0"', "sdk: '>=3.0.0 <4.0.0'", 
                               'sdk: ">=3.8.0 <4.0.0"', "sdk: '>=3.8.0 <4.0.0'"]:
                    content = content.replace(old_sdk, 'sdk: ">=3.5.0 <4.0.0"')
            elif file_path.name == "index.html":
                content = content.replace("codiexample", project_title)
            elif file_path.name == "manifest.json":
                content = content.replace("codiexample", project_title)
                
        elif self.framework in ("react", "nextjs"):
            if file_path.name == "package.json":
                content = content.replace('"react-starter"', f'"{package_name}"')
                content = content.replace('"nextjs-starter"', f'"{package_name}"')
            elif file_path.name == "index.html":
                content = content.replace("{{PROJECT_TITLE}}", project_title)
        
        # Next.js specific configuration for GitHub Pages (static export)
        # Note: For Docker/local deployment we keep "standalone" mode
        if self.framework == "nextjs" and self.deployment_platform == "github_pages" and file_path.name in ("next.config.js", "next.config.ts", "next.config.mjs"):
            # Replace standalone with export for static GitHub Pages deployment
            content = content.replace('output: "standalone"', "output: 'export'")

        return content
    
    def _get_workflow_filename(self) -> str:
        """Get the GitHub Actions workflow filename for the framework."""
        return {
            "flutter": "flutter_web_deploy.yml",
            "react": "react_deploy.yml",
            "nextjs": "nextjs_deploy.yml",
        }.get(self.framework, "deploy.yml")
    
    def _get_deploy_workflow(self) -> str:
        """Get the GitHub Actions deployment workflow for the framework."""
        if self.framework == "flutter":
            return DEPLOY_WORKFLOW
        elif self.framework == "react":
            return REACT_DEPLOY_WORKFLOW
        elif self.framework == "nextjs":
            return NEXTJS_DEPLOY_WORKFLOW
        return DEPLOY_WORKFLOW

    async def push_template_to_repo(
        self,
        project_path: str,
        project_name: str,
        project_title: Optional[str] = None,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Initialize local repository with starter template.

        Args:
            project_path: Path to local project repository
            project_name: Name of the project
            project_title: Human-readable project title
            branch: Branch to initialize

        Returns:
            Dictionary with commit information
        """
        template_files = self.get_template_files(project_name, project_title)
        
        # Format files for git_service
        files_dict = {}
        for path, file_info in template_files.items():
            files_dict[path] = file_info["content"]

        git_service = get_git_service(project_path)
        
        # Initialize and commit
        # If repo doesn't exist, this might need to call init_repository first
        # But usually we call this from projects.py which has the flow
        
        project_label = project_title or project_name
        commit_msg = f"Initial commit: {self.framework.capitalize()} starter template for {project_label} from Codi"
        
        # Assuming we use git_service.init_repository pattern
        # or we just write files and commit if already initialized
        for rel_path, content in files_dict.items():
            full_path = Path(project_path) / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                full_path.write_bytes(content)
            else:
                full_path.write_text(content)
        
        git_service.commit(commit_msg, all_changes=True)
        sha = git_service.get_current_commit()

        logger.info(
            f"Initialized local template at {project_path}",
            files_count=len(template_files),
            commit_sha=sha,
        )
        
        return {"commit_sha": sha, "branch": branch}

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
