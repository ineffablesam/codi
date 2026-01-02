"""Deployment service for multi-platform app deployments.

Supports:
- Vercel (React, Next.js)
- Netlify (React, Next.js)
- GitHub Pages (Flutter Web, React, Next.js static)
"""
import json
import httpx
from typing import Any, Dict, Optional

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DeploymentService:
    """Service for deploying applications to various platforms."""

    def __init__(
        self,
        vercel_token: Optional[str] = None,
        netlify_token: Optional[str] = None,
    ):
        """Initialize deployment service.
        
        Args:
            vercel_token: Vercel API token for deployments
            netlify_token: Netlify API token for deployments
        """
        self.vercel_token = vercel_token
        self.netlify_token = netlify_token

    async def deploy_to_vercel(
        self,
        project_name: str,
        source_url: str,
        framework: str = "nextjs",
        environment: str = "production",
    ) -> Dict[str, Any]:
        """Deploy a project to Vercel.
        
        Args:
            project_name: Name of the project
            source_url: URL to the source code (GitHub repo)
            framework: Framework type (nextjs, react, static)
            environment: Deployment environment (production, preview)
            
        Returns:
            Deployment result with URL and status
        """
        if not self.vercel_token:
            raise ValueError("Vercel token not configured")

        headers = {
            "Authorization": f"Bearer {self.vercel_token}",
            "Content-Type": "application/json",
        }

        # Create project if it doesn't exist
        async with httpx.AsyncClient() as client:
            # Check if project exists
            resp = await client.get(
                f"https://api.vercel.com/v9/projects/{project_name}",
                headers=headers,
            )

            if resp.status_code == 404:
                # Create new project
                create_resp = await client.post(
                    "https://api.vercel.com/v9/projects",
                    headers=headers,
                    json={
                        "name": project_name,
                        "framework": framework,
                        "gitRepository": {
                            "type": "github",
                            "repo": source_url.replace("https://github.com/", ""),
                        },
                    },
                )

                if create_resp.status_code not in [200, 201]:
                    logger.error(f"Failed to create Vercel project: {create_resp.text}")
                    return {
                        "success": False,
                        "error": create_resp.text,
                    }

            # Trigger deployment
            deploy_resp = await client.post(
                "https://api.vercel.com/v13/deployments",
                headers=headers,
                json={
                    "name": project_name,
                    "target": environment,
                    "gitSource": {
                        "type": "github",
                        "ref": "main",
                        "repoId": source_url.replace("https://github.com/", ""),
                    },
                },
            )

            if deploy_resp.status_code in [200, 201]:
                data = deploy_resp.json()
                return {
                    "success": True,
                    "deployment_id": data.get("id"),
                    "url": f"https://{data.get('url', project_name + '.vercel.app')}",
                    "status": "deploying",
                    "provider": "vercel",
                }
            else:
                return {
                    "success": False,
                    "error": deploy_resp.text,
                    "provider": "vercel",
                }

    async def deploy_to_netlify(
        self,
        project_name: str,
        source_url: str,
        build_command: str = "npm run build",
        publish_dir: str = "dist",
    ) -> Dict[str, Any]:
        """Deploy a project to Netlify.
        
        Args:
            project_name: Name of the site
            source_url: URL to the source code (GitHub repo)
            build_command: Command to build the project
            publish_dir: Directory containing build output
            
        Returns:
            Deployment result with URL and status
        """
        if not self.netlify_token:
            raise ValueError("Netlify token not configured")

        headers = {
            "Authorization": f"Bearer {self.netlify_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            # Create new site with GitHub integration
            resp = await client.post(
                "https://api.netlify.com/api/v1/sites",
                headers=headers,
                json={
                    "name": project_name,
                    "repo": {
                        "provider": "github",
                        "repo_path": source_url.replace("https://github.com/", ""),
                        "cmd": build_command,
                        "dir": publish_dir,
                        "branch": "main",
                    },
                },
            )

            if resp.status_code in [200, 201]:
                data = resp.json()
                return {
                    "success": True,
                    "site_id": data.get("id"),
                    "url": data.get("ssl_url") or data.get("url"),
                    "status": "building",
                    "provider": "netlify",
                }
            else:
                return {
                    "success": False,
                    "error": resp.text,
                    "provider": "netlify",
                }

    def get_github_pages_url(self, repo_full_name: str) -> str:
        """Get the GitHub Pages URL for a repository.
        
        Args:
            repo_full_name: Full repository name (owner/repo)
            
        Returns:
            GitHub Pages URL
        """
        parts = repo_full_name.split("/")
        if len(parts) == 2:
            owner, repo = parts
            return f"https://{owner}.github.io/{repo}/"
        return ""

    def get_deployment_config(
        self,
        framework: str,
        platform: str,
    ) -> Dict[str, Any]:
        """Get deployment configuration for a framework and platform.
        
        Args:
            framework: Project framework (flutter, react, nextjs, react_native)
            platform: Deployment platform (vercel, netlify, github_pages)
            
        Returns:
            Deployment configuration
        """
        configs = {
            ("nextjs", "vercel"): {
                "framework": "nextjs",
                "build_command": "npm run build",
                "output_directory": ".next",
                "install_command": "npm install",
            },
            ("nextjs", "netlify"): {
                "build_command": "npm run build",
                "publish_dir": "out",
                "plugin": "@netlify/plugin-nextjs",
            },
            ("react", "vercel"): {
                "framework": "vite",
                "build_command": "npm run build",
                "output_directory": "dist",
            },
            ("react", "netlify"): {
                "build_command": "npm run build",
                "publish_dir": "dist",
            },
            ("react", "github_pages"): {
                "build_command": "npm run build",
                "publish_dir": "dist",
                "base_url": "/${{ github.event.repository.name }}/",
            },
            ("flutter", "github_pages"): {
                "build_command": "flutter build web --release --base-href /${{ github.event.repository.name }}/",
                "publish_dir": "build/web",
            },
            ("flutter", "vercel"): {
                "framework": "other",
                "build_command": "flutter build web --release",
                "output_directory": "build/web",
            },
        }

        return configs.get((framework, platform), {})


# Singleton instance
deployment_service = DeploymentService()
