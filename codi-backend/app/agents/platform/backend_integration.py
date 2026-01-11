"""Backend Integration agent for Supabase, Firebase, and Serverpod setup."""
import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import BaseAgent
from app.agents.prompts.backend_integration_prompts import (
    SYSTEM_PROMPT,
    SUPABASE_FLUTTER_SETUP,
    SUPABASE_REACT_SETUP,
    SUPABASE_NEXTJS_SETUP,
    FIREBASE_FLUTTER_SETUP,
    FIREBASE_REACT_SETUP,
    SERVERPOD_FLUTTER_SETUP,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BackendIntegrationAgent(BaseAgent):
    """Agent responsible for setting up backend integrations.

    Handles Supabase, Firebase, and Serverpod configuration
    for Flutter, React, React Native, and Next.js projects.
    """

    name = "backend_integration"
    description = "Backend service configuration and integration"
    system_prompt = SYSTEM_PROMPT

    # Map of backend + framework to setup prompts
    SETUP_PROMPTS = {
        ("supabase", "flutter"): SUPABASE_FLUTTER_SETUP,
        ("supabase", "react"): SUPABASE_REACT_SETUP,
        ("supabase", "nextjs"): SUPABASE_NEXTJS_SETUP,
        ("supabase", "react_native"): SUPABASE_REACT_SETUP,  # Similar to React
        ("firebase", "flutter"): FIREBASE_FLUTTER_SETUP,
        ("firebase", "react"): FIREBASE_REACT_SETUP,
        ("firebase", "nextjs"): FIREBASE_REACT_SETUP,  # Similar to React
        ("firebase", "react_native"): FIREBASE_REACT_SETUP,  # Similar to React
        ("serverpod", "flutter"): SERVERPOD_FLUTTER_SETUP,
    }

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the backend integration agent."""

        @tool
        def read_file(file_path: str) -> str:
            """Read a file from the repository."""
            try:
                return self.git_service.get_file_content(
                    file_path=file_path,
                    ref=self.context.current_branch,
                )
            except Exception as e:
                return f"Error: {e}"

        @tool
        def write_file(file_path: str, content: str, commit_message: str) -> str:
            """Write content to a file in the repository."""
            try:
                self.git_service.write_file(file_path=file_path, content=content)
                result = self.git_service.commit(message=commit_message, files=[file_path])
                return json.dumps(result.__dict__, default=str)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def create_env_file(env_vars: str) -> str:
            """Create a .env.example file with placeholder values.

            Args:
                env_vars: JSON object of environment variable names

            Returns:
                Result of the operation
            """
            try:
                vars_dict = json.loads(env_vars)
                content = "# Environment Variables\n# Copy this file to .env and fill in your values\n\n"
                for key, description in vars_dict.items():
                    content += f"# {description}\n{key}=\n\n"

                self.git_service.write_file(file_path=".env.example", content=content)
                result = self.git_service.commit(
                    message="Add environment variables template",
                    files=[".env.example"],
                )
                return json.dumps(result.__dict__, default=str)
            except Exception as e:
                return f"Error: {e}"

        return [read_file, write_file, create_env_file]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute backend integration setup."""
        backend_type = input_data.get("backend_type", "supabase")  # supabase, firebase, serverpod
        framework = input_data.get("framework", "flutter")  # flutter, react, nextjs, react_native
        step = input_data.get("step", {})
        description = step.get("description", f"Setup {backend_type} for {framework}")

        await self.emit_status(
            status="started",
            message=f"Configuring {backend_type} for {framework}",
        )

        try:
            # Get the appropriate setup prompt
            setup_prompt = self.SETUP_PROMPTS.get((backend_type, framework), "")

            # Build the integration prompt
            prompt = f"""Task: {description}

Backend: {backend_type}
Framework: {framework}

Reference implementation:
{setup_prompt}

Generate the necessary files to integrate {backend_type} with {framework}.
Follow the patterns exactly as shown in the reference.

Return JSON:
{{
  "files": [
    {{"path": "path/to/file.ts", "content": "file content", "description": "what this file does"}}
  ],
  "env_vars": {{
    "VAR_NAME": "Description of the variable"
  }}
}}
"""

            await self.emit_status(
                status="in_progress",
                message=f"Generating {backend_type} integration files",
            )

            response = await self.invoke([HumanMessage(content=prompt)])
            content = self._get_content(response)

            # Extract JSON from response
            result = self._extract_json(content)

            files_created = []

            # Write each file
            for file_info in result.get("files", []):
                file_path = file_info.get("path", "")
                file_content = file_info.get("content", "")

                if file_path and file_content:
                    await self.emit_tool_execution(
                        tool_name="write_file",
                        message=f"Creating {file_path}",
                        file_path=file_path,
                    )

                    await self.execute_tool(
                        "write_file",
                        {
                            "file_path": file_path,
                            "content": file_content,
                            "commit_message": f"Add {backend_type} integration: {file_path.split('/')[-1]}",
                        },
                    )

                    files_created.append(file_path)

                    await self.emit_file_operation(
                        operation="create",
                        file_path=file_path,
                        message=file_info.get("description", f"Created {file_path}"),
                    )

            # Create .env.example if env_vars provided
            env_vars = result.get("env_vars", {})
            if env_vars:
                await self.execute_tool(
                    "create_env_file",
                    {"env_vars": json.dumps(env_vars)},
                )
                files_created.append(".env.example")

            await self.emit_status(
                status="completed",
                message=f"Created {len(files_created)} integration files",
                details={
                    "backend": backend_type,
                    "framework": framework,
                    "files_created": files_created,
                },
            )

            return {
                "backend_type": backend_type,
                "framework": framework,
                "files_created": files_created,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Backend integration failed: {e}")
            await self.emit_error(error=str(e), message="Backend integration failed")
            raise

    def _get_content(self, response) -> str:
        if hasattr(response, 'text') and response.text:
            return response.text
        if isinstance(response.content, list):
            return "\n".join(
                p.get('text', str(p)) if isinstance(p, dict) else str(p)
                for p in response.content
            )
        return str(response.content) if response.content else ""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from response text."""
        import re

        # Try to find JSON in code blocks
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # Try direct JSON extraction
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        return {"files": [], "env_vars": {}}
