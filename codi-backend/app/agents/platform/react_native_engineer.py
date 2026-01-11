"""React Native Engineer agent for mobile app development."""
import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import BaseAgent
from app.agents.prompts.react_native_prompts import SYSTEM_PROMPT
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ReactNativeEngineerAgent(BaseAgent):
    """Agent responsible for writing React Native code.

    The React Native Engineer creates cross-platform mobile components
    using React Native primitives (View, Text, etc.) - never HTML elements.
    """

    name = "react_native_engineer"
    description = "React Native mobile development"
    system_prompt = SYSTEM_PROMPT

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the React Native engineer."""

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
        def list_directory(path: str = "src") -> str:
            """List files in a directory."""
            try:
                files = self.git_service.list_files(
                    path=path,
                    ref=self.context.current_branch,
                )
                return json.dumps([f.__dict__ for f in files], indent=2)
            except Exception as e:
                return f"Error: {e}"

        return [read_file, write_file, list_directory]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a React Native code generation task."""
        step = input_data.get("step", {})
        description = step.get("description", "")
        file_path = step.get("file_path", "")
        action = step.get("action", "create")

        await self.emit_status(status="started", message="Starting React Native code generation")

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

            # Validate no HTML elements
            html_elements = self._check_html_elements(code)
            if html_elements:
                logger.warning(f"HTML elements found in React Native code: {html_elements}")
                # Try to regenerate
                code = await self._regenerate_without_html(description, file_path, code, html_elements)

            if file_path:
                msg = f"{'Create' if action == 'create' else 'Update'} {file_path.split('/')[-1]}"
                await self.execute_tool("write_file", {"file_path": file_path, "content": code, "commit_message": msg})
                await self.emit_file_operation(operation=action, file_path=file_path, message=msg)

            await self.emit_status(status="completed", message="Code generation complete")
            return {"file_path": file_path, "code": code, "action": action, "success": True}

        except Exception as e:
            logger.error(f"React Native code generation failed: {e}")
            await self.emit_error(error=str(e), message="Code generation failed")
            raise

    def _build_prompt(self, description: str, file_path: str, action: str, existing: Optional[str]) -> str:
        parts = [f"Task: {description}", f"File: {file_path}", f"Action: {action}"]
        if existing:
            parts.append(f"\nExisting content:\n```tsx\n{existing}\n```")
        parts.append("""
Requirements:
- Use ONLY React Native components (View, Text, Image, etc.)
- NEVER use HTML elements (div, span, p, img, input, button)
- Use StyleSheet.create for all styles
- Include proper TypeScript types
- Handle SafeAreaView for edge devices

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

    def _check_html_elements(self, code: str) -> List[str]:
        """Check for HTML elements that shouldn't be in React Native."""
        html_patterns = [
            r'<div\b', r'<span\b', r'<p\b', r'<img\b', r'<input\b',
            r'<button\b', r'<a\b', r'<ul\b', r'<li\b', r'<form\b',
        ]
        found = []
        for pattern in html_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                found.append(pattern.replace(r'<', '').replace(r'\b', ''))
        return found

    async def _regenerate_without_html(self, description: str, file_path: str, code: str, html_elements: List[str]) -> str:
        """Regenerate code without HTML elements."""
        prompt = f"""CRITICAL ERROR: Your previous code contained HTML elements which are NOT valid in React Native.

INVALID ELEMENTS FOUND: {', '.join(html_elements)}

REMEMBER:
- <div> → <View>
- <span>/<p> → <Text>
- <img> → <Image>
- <input> → <TextInput>
- <button> → <TouchableOpacity> or <Pressable>

Original task: {description}
File: {file_path}

Fix the code and return ONLY React Native components in ```tsx blocks."""

        response = await self.invoke([HumanMessage(content=prompt)])
        new_code = self._extract_code(self._get_content(response))
        return new_code if new_code else code
