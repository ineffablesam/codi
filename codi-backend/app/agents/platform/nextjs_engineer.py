"""Next.js Engineer agent for Next.js App Router development."""
import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, ToolMessage
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

            messages = [HumanMessage(content=prompt)]
            
            # ReAct loop: allow agent to use tools before generating final answer
            # Limit to 5 turns to prevent infinite loops
            final_response = None
            
            for i in range(5):
                response = await self.invoke(messages)
                
                # Check if the model wants to call tools
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(f"Agent requested {len(response.tool_calls)} tool calls in turn {i+1}")
                    logger.debug(f"Tool calls metadata: {response.tool_calls}")
                    if hasattr(response, 'additional_kwargs'):
                        logger.debug(f"Additional kwargs: {response.additional_kwargs}")
                    
                    messages.append(response)  # Add the AI's tool request to history
                    
                    # Execute all requested tools
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        tool_call_id = tool_call["id"]
                        
                        logger.info(f"Executing tool {tool_name} with args: {tool_args}")
                        
                        try:
                            # Execute the tool
                            result = await self.execute_tool(tool_name, tool_args)
                            
                            # Add the tool result to history
                            messages.append(ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call_id,
                                name=tool_name
                            ))
                        except Exception as e:
                            logger.error(f"Tool execution failed: {e}")
                            messages.append(ToolMessage(
                                content=f"Error executing tool: {e}",
                                tool_call_id=tool_call_id,
                                name=tool_name
                            ))
                    
                    # Continue to next iteration to give tool outputs back to LLM
                    continue
                
                # If no tool calls (or content is present alongside them), treat as final response
                # Ideally, if tool_calls matches, we loop. If text content, we stop.
                # However, some models return both. If we have tool calls, we prioritized them above.
                # So if we are here, we either have no tool calls, or we decided to stop.
                final_response = response
                break
            
            if not final_response:
                # If we exhausted loops without a final non-tool response, use the last text we got
                # OR just perform one last invoke to force an answer? 
                # For now, let's use the last response we have
                final_response = response

            raw_content = self._get_content(final_response)
            logger.debug(f"LLM response content (first 500 chars): {raw_content[:500] if raw_content else 'EMPTY'}")
            
            # Extract ALL files from the response
            files_to_write = self._extract_all_files(raw_content)
            
            if files_to_write:
                # Write all extracted files
                written_files = []
                for f in files_to_write:
                    try:
                        msg = f"feat: {f['path'].split('/')[-1]}"
                        await self.emit_status(status="in_progress", message=f"Writing {f['path']}...")
                        await self.execute_tool("write_file", {
                            "file_path": f["path"],
                            "content": f["code"],
                            "commit_message": msg
                        })
                        await self.emit_file_operation(operation=action, file_path=f["path"], message=msg)
                        written_files.append(f["path"])
                        logger.info(f"Successfully wrote file: {f['path']}")
                    except Exception as write_error:
                        logger.error(f"Failed to write file {f['path']}: {write_error}")
                
                await self.emit_status(status="completed", message=f"Created {len(written_files)} file(s)")
                return {
                    "files_written": written_files,
                    "file_count": len(written_files),
                    "action": action,
                    "success": len(written_files) > 0
                }
            
            # Fallback: Try legacy single-file extraction if multi-file didn't work
            code = self._extract_code(raw_content)
            if not code:
                logger.error(f"Failed to extract code. LLM returned: {raw_content[:1000] if raw_content else 'EMPTY RESPONSE'}")
                raise ValueError(f"Failed to extract code from LLM response. Response length: {len(raw_content) if raw_content else 0} chars")

            # Write single file if file_path was provided
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
        parts = [f"Task: {description}"]
        if file_path:
            parts.append(f"Primary File: {file_path}")
        parts.append(f"Action: {action}")
        if existing:
            parts.append(f"\nExisting content:\n```tsx\n{existing}\n```")
        parts.append("""
Requirements:
- Use Next.js 14+ App Router patterns
- Use Server Components by default, Client Components only when needed
- Include proper TypeScript types
- Add metadata for SEO on pages
- Handle loading and error states

CRITICAL OUTPUT FORMAT:
You MUST return code in this EXACT format for EACH file you create/modify:

```tsx
// filepath: components/example.tsx
'use client';

import React from 'react';
// ... rest of code
```

The "// filepath:" comment on the FIRST LINE inside each code block is REQUIRED.
This tells me which file to write the code to.

If you need to create MULTIPLE files, include MULTIPLE code blocks, each with its own filepath comment.
""")
        return "\n".join(parts)

    def _get_content(self, response) -> str:
        """Extract text content from LLM response."""
        # Debug logging to see what we're working with
        logger.debug(f"Response type: {type(response)}")
        logger.debug(f"Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        
        # Handle AIMessage.text property vs method
        if hasattr(response, 'text'):
            text = response.text
            logger.debug(f"response.text type: {type(text)}, value: {str(text)[:200] if text else 'None'}")
            # If it's a callable (method), call it
            if callable(text):
                text = text()
                logger.debug(f"After calling text(): {str(text)[:200] if text else 'None'}")
            if text and isinstance(text, str):
                return text
        
        # Handle content as list (e.g., multipart responses)
        if hasattr(response, 'content'):
            content = response.content
            logger.debug(f"response.content type: {type(content)}, value: {str(content)[:200] if content else 'None'}")
            if isinstance(content, list):
                return "\n".join(
                    p.get('text', str(p)) if isinstance(p, dict) else str(p) 
                    for p in content
                )
            if isinstance(content, str):
                return content
            if content:
                return str(content)
        
        logger.warning(f"Could not extract content from response: {str(response)[:500]}")
        return ""

    def _extract_code(self, text: str) -> Optional[str]:
        """Extract code from markdown code blocks (legacy single-file extraction)."""
        if not text or not isinstance(text, str):
            return None
            
        for pattern in [r"```tsx\s*(.*?)\s*```", r"```typescript\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches and matches[0].strip():
                return matches[0].strip()
        if "import " in text or "export " in text:
            return text.strip()
        return None

    def _extract_all_files(self, text: str) -> List[Dict[str, str]]:
        """Extract all files from markdown response with filepath comments.
        
        Parses patterns like:
        ```tsx
        // filepath: components/theme-provider.tsx
        'use client';
        ...code...
        ```
        
        Also handles:
        - // path: components/file.tsx
        - // file: components/file.tsx
        """
        files = []
        if not text or not isinstance(text, str):
            return files
        
        # Find all code blocks
        code_block_pattern = r"```(?:tsx|typescript|ts|js|jsx|json)?\s*\n(.*?)```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        
        for code_content in matches:
            code_content = code_content.strip()
            if not code_content:
                continue
            
            # Try to extract filepath from first line comment
            filepath = None
            lines = code_content.split('\n')
            first_line = lines[0].strip() if lines else ""
            
            # Pattern: // filepath: path/to/file.tsx
            filepath_patterns = [
                r"^//\s*filepath:\s*(.+)$",
                r"^//\s*path:\s*(.+)$",
                r"^//\s*file:\s*(.+)$",
                r"^//\s*(.+\.(?:tsx|ts|js|jsx|json))$",  # // components/file.tsx
            ]
            
            for pattern in filepath_patterns:
                match = re.match(pattern, first_line, re.IGNORECASE)
                if match:
                    filepath = match.group(1).strip()
                    # Remove the filepath comment from code
                    code_content = '\n'.join(lines[1:]).strip()
                    break
            
            if filepath:
                files.append({
                    "path": filepath,
                    "code": code_content
                })
                logger.info(f"Extracted file: {filepath} ({len(code_content)} chars)")
        
        return files
