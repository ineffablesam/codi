"""React Engineer agent for React/TypeScript code generation."""
import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.agents.prompts.react_engineer_prompts import SYSTEM_PROMPT
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ReactEngineerAgent(BaseAgent):
    """Agent responsible for writing React/TypeScript code.

    The React Engineer creates and modifies React components,
    writes production-quality TypeScript code, and validates all code
    before committing to prevent syntax errors.
    """

    name = "react_engineer"
    description = "React and TypeScript code generation"
    system_prompt = SYSTEM_PROMPT

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the React engineer."""

        @tool
        def read_file(file_path: str) -> str:
            """Read a file from the repository.

            Args:
                file_path: Path to the file to read

            Returns:
                File content
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                content = self.github_service.get_file_content(
                    repo_full_name=self.context.repo_full_name,
                    file_path=file_path,
                    ref=self.context.current_branch,
                )
                return content
            except Exception as e:
                return f"Error: {e}"

        @tool
        def write_file(file_path: str, content: str, commit_message: str) -> str:
            """Write content to a file in the repository.

            Args:
                file_path: Path to the file to write
                content: File content to write
                commit_message: Commit message for this change

            Returns:
                Result of the operation
            """
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
        def list_directory(path: str = "src") -> str:
            """List files in a directory.

            Args:
                path: Directory path to list

            Returns:
                JSON list of files
            """
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
        """Execute a code generation task.

        Args:
            input_data: Dictionary with task details from the planner

        Returns:
            Dictionary with results of the code generation
        """
        step = input_data.get("step", {})
        description = step.get("description", "")
        file_path = step.get("file_path", "")
        action = step.get("action", "create")

        await self.emit_status(
            status="started",
            message="Starting React code generation",
        )

        try:
            # Get existing content for updates
            existing_content = None
            if action in ["update", "analyze"] and file_path:
                await self.emit_tool_execution(
                    tool_name="read_file",
                    message=f"Reading existing file: {file_path}",
                    file_path=file_path,
                )
                try:
                    existing_content = await self.execute_tool(
                        "read_file",
                        {"file_path": file_path},
                    )
                except Exception:
                    existing_content = None

            # Build the code generation prompt
            code_prompt = self._build_code_prompt(
                description=description,
                file_path=file_path,
                action=action,
                existing_content=existing_content,
            )

            await self.emit_status(
                status="in_progress",
                message=f"Generating code for {file_path or 'new file'}",
            )

            response = await self.invoke([HumanMessage(content=code_prompt)])

            # Extract the generated code
            response_content = self._extract_response_content(response)
            generated_code = self._extract_code(response_content)

            if not generated_code:
                logger.error(f"Failed to extract code from LLM response.")
                raise ValueError("Failed to extract code from LLM response.")

            # Write the file if we have a path
            if file_path:
                commit_message = f"{'Create' if action == 'create' else 'Update'} {file_path.split('/')[-1]}"

                await self.emit_tool_execution(
                    tool_name="write_file",
                    message=f"Writing file: {file_path}",
                    file_path=file_path,
                )

                await self.execute_tool(
                    "write_file",
                    {
                        "file_path": file_path,
                        "content": generated_code,
                        "commit_message": commit_message,
                    },
                )

                await self.emit_file_operation(
                    operation=action,
                    file_path=file_path,
                    message=f"{'Created' if action == 'create' else 'Updated'} {file_path.split('/')[-1]}",
                )

            await self.emit_status(
                status="completed",
                message="Code generation complete",
                details={
                    "file_path": file_path,
                    "action": action,
                    "lines_generated": len(generated_code.split("\n")) if generated_code else 0,
                },
            )

            return {
                "file_path": file_path,
                "code": generated_code,
                "action": action,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            await self.emit_error(
                error=str(e),
                message="Code generation failed",
            )
            raise

    def _build_code_prompt(
        self,
        description: str,
        file_path: str,
        action: str,
        existing_content: Optional[str] = None,
    ) -> str:
        """Build a prompt for code generation."""
        prompt_parts = [
            f"Task: {description}",
            f"File: {file_path}",
            f"Action: {action}",
        ]

        if existing_content:
            prompt_parts.append(f"\nExisting content:\n```tsx\n{existing_content}\n```")
            prompt_parts.append("\nModify the existing content to implement the task.")
        else:
            prompt_parts.append("\nGenerate a complete, production-ready React/TypeScript file.")

        prompt_parts.append("""
Requirements:
- Use functional components with hooks
- Use TypeScript with proper type annotations
- Handle loading and error states
- Include all necessary imports
- Follow React best practices

Return ONLY the code, no explanations. Wrap in ```tsx code blocks.""")

        return "\n".join(prompt_parts)

    def _extract_response_content(self, response) -> str:
        """Extract text content from LLM response."""
        if hasattr(response, 'text') and response.text:
            return response.text
        elif isinstance(response.content, list):
            text_parts = []
            for part in response.content:
                if isinstance(part, dict) and 'text' in part:
                    text_parts.append(part['text'])
                elif isinstance(part, str):
                    text_parts.append(part)
            return "\n".join(text_parts)
        else:
            return str(response.content) if response.content else ""

    def _extract_code(self, text: str) -> Optional[str]:
        """Extract TypeScript/React code from text."""
        # Try JSON format first
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                if "changes" in data and isinstance(data["changes"], list):
                    for change in data["changes"]:
                        if change.get("content"):
                            return change["content"]
                if "code" in data and data["code"]:
                    return data["code"]
                if "content" in data and data["content"]:
                    return data["content"]
        except (json.JSONDecodeError, ValueError):
            pass

        # Look for tsx/typescript code blocks
        patterns = [
            r"```tsx\s*(.*?)\s*```",
            r"```typescript\s*(.*?)\s*```",
            r"```ts\s*(.*?)\s*```",
            r"```jsx\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                code = matches[0].strip()
                if code:
                    return code

        # Check if entire text looks like React code
        if "import " in text or "export " in text or "function " in text:
            return text.strip()

        return None
