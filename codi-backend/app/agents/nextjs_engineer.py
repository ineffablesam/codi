"""Next.js Engineer agent for Next.js App Router development."""
import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.agents.prompts.nextjs_engineer_prompts import SYSTEM_PROMPT
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NextjsEngineerAgent(BaseAgent):
    """Agent responsible for writing Next.js code with App Router patterns.

    The Next.js Engineer creates pages, API routes, Server Components,
    Client Components, and middleware using Next.js 14+ patterns.
    """

    name = "nextjs_engineer"
    description = "Next.js App Router development"
    system_prompt = SYSTEM_PROMPT

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the Next.js engineer."""

        @tool
        def read_file(file_path: str) -> str:
            """Read a file from the repository."""
            if not self.context.repo_full_name:
                return "Error: No repository configured"
            try:
                return self.github_service.get_file_content(
                    repo_full_name=self.context.repo_full_name,
                    file_path=file_path,
                    ref=self.context.current_branch,
                )
            except Exception as e:
                return f"Error: {e}"

        @tool
        def write_file(file_path: str, content: str, commit_message: str) -> str:
            """Write content to a file in the repository."""
            if not self.context.repo_full_name:
                return "Error: No repository configured"
            try:
                result = self.github_service.create_or_update_file(
                    repo_full_name=self.context.repo_full_name,
                    file_path=file_path,
                    content=content,
                    commit_message=commit_message,
                    branch=self.context.current_branch,
                )
                return json.dumps(result)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def list_directory(path: str = "app") -> str:
            """List files in a directory (defaults to app/ for App Router)."""
            if not self.context.repo_full_name:
                return "Error: No repository configured"
            try:
                files = self.github_service.list_files(
                    repo_full_name=self.context.repo_full_name,
                    path=path,
                    ref=self.context.current_branch,
                )
                return json.dumps(files, indent=2)
            except Exception as e:
                return f"Error: {e}"

        return [read_file, write_file, list_directory]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Next.js code generation task."""
        step = input_data.get("step", {})
        description = step.get("description", "")
        file_path = step.get("file_path", "")
        action = step.get("action", "create")

        await self.emit_status(status="started", message="Starting Next.js code generation")

        try:
            existing_content = None
            if action in ["update", "analyze"] and file_path:
                try:
                    existing_content = await self.execute_tool("read_file", {"file_path": file_path})
                except Exception:
                    pass

            prompt = self._build_prompt(description, file_path, action, existing_content)
            await self.emit_status(status="in_progress", message=f"Generating {file_path or 'code'}")

            response = await self.invoke([HumanMessage(content=prompt)])
            code = self._extract_code(self._get_content(response))

            if not code:
                raise ValueError("Failed to extract code from LLM response")

            if file_path:
                msg = f"{'Create' if action == 'create' else 'Update'} {file_path.split('/')[-1]}"
                await self.execute_tool("write_file", {"file_path": file_path, "content": code, "commit_message": msg})
                await self.emit_file_operation(operation=action, file_path=file_path, message=msg)

            await self.emit_status(status="completed", message="Code generation complete")
            return {"file_path": file_path, "code": code, "action": action, "success": True}

        except Exception as e:
            logger.error(f"Next.js code generation failed: {e}")
            await self.emit_error(error=str(e), message="Code generation failed")
            raise

    def _build_prompt(self, description: str, file_path: str, action: str, existing: Optional[str]) -> str:
        parts = [f"Task: {description}", f"File: {file_path}", f"Action: {action}"]
        if existing:
            parts.append(f"\nExisting content:\n```tsx\n{existing}\n```")
        parts.append("""
Requirements:
- Use Next.js 14+ App Router patterns
- Use Server Components by default, Client Components only when needed
- Include proper TypeScript types
- Add metadata for SEO on pages
- Handle loading and error states

Return ONLY the code in ```tsx blocks.""")
        return "\n".join(parts)

    def _get_content(self, response) -> str:
        if hasattr(response, 'text') and response.text:
            return response.text
        if isinstance(response.content, list):
            return "\n".join(p.get('text', str(p)) if isinstance(p, dict) else str(p) for p in response.content)
        return str(response.content) if response.content else ""

    def _extract_code(self, text: str) -> Optional[str]:
        for pattern in [r"```tsx\s*(.*?)\s*```", r"```typescript\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches and matches[0].strip():
                return matches[0].strip()
        if "import " in text or "export " in text:
            return text.strip()
        return None
