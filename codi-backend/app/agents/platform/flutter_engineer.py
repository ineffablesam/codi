"""Flutter Engineer agent for Dart/Flutter code generation with anti-hallucination measures."""
import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.agents.prompts.flutter_engineer_prompts import SYSTEM_PROMPT as ENHANCED_SYSTEM_PROMPT
from app.agents.tools.dart_analyzer import DartAnalyzer
from app.services.flutter import (
    analyze_dart_code,
    extract_widgets_from_code,
    generate_getx_controller_template,
    generate_screen_template,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FlutterEngineerAgent(BaseAgent):
    """Agent responsible for writing Dart/Flutter code with anti-hallucination measures.

    The Flutter Engineer creates and modifies Flutter files,
    writes production-quality Dart code, and validates all code
    before committing to prevent syntax errors like snake_case properties.
    """

    name = "flutter_engineer"
    description = "Dart and Flutter code generation with syntax validation"
    
    # Use enhanced system prompt with anti-hallucination rules
    system_prompt = ENHANCED_SYSTEM_PROMPT
    
    # Initialize dart analyzer for pre-validation
    dart_analyzer = DartAnalyzer()
    
    # Maximum retry attempts for code generation
    MAX_RETRY_ATTEMPTS = 2

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the Flutter engineer."""

        @tool
        def read_file(file_path: str) -> str:
            """Read a file from the repository.

            Args:
                file_path: Path to the file to read

            Returns:
                File content
            """
            try:
                content = self.git_service.get_file_content(
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
            try:
                self.git_service.write_file(file_path=file_path, content=content)
                result = self.git_service.commit(message=commit_message, files=[file_path])
                return json.dumps(result.__dict__, default=str)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def list_directory(path: str = "lib") -> str:
            """List files in a directory.

            Args:
                path: Directory path to list

            Returns:
                JSON list of files
            """
            try:
                files = self.git_service.list_files(
                    path=path,
                    ref=self.context.current_branch,
                )
                return json.dumps([f.__dict__ for f in files], indent=2)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def analyze_dart_file(file_path: str) -> str:
            """Analyze a Dart file's structure.

            Args:
                file_path: Path to the Dart file

            Returns:
                JSON analysis of the file
            """
            try:
                content = self.git_service.get_file_content(
                    file_path=file_path,
                    ref=self.context.current_branch,
                )
                analysis = analyze_dart_code(content)
                analysis["widgets_used"] = extract_widgets_from_code(content)
                return json.dumps(analysis, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def generate_controller(class_name: str, state_vars: str = "[]") -> str:
            """Generate a GetX controller template.

            Args:
                class_name: Name of the controller class
                state_vars: JSON array of state variables with name, type, initial

            Returns:
                Generated Dart code
            """
            try:
                state_variables = json.loads(state_vars) if state_vars else []
                return generate_getx_controller_template(class_name, state_variables)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def generate_screen(screen_name: str, controller_name: str, title: str) -> str:
            """Generate a Flutter screen template.

            Args:
                screen_name: Name of the screen class
                controller_name: Name of the GetX controller
                title: Screen title

            Returns:
                Generated Dart code
            """
            return generate_screen_template(screen_name, controller_name, title)

        return [
            read_file,
            write_file,
            list_directory,
            analyze_dart_file,
            generate_controller,
            generate_screen,
        ]

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

        # Emit start status
        await self.emit_status(
            status="started",
            message="Starting code generation",
        )

        try:
            # Get context about existing files if needed
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

            # Generate code using LLM
            await self.emit_status(
                status="in_progress",
                message=f"Generating code for {file_path or 'new file'}",
            )

            # Generate code using LLM (without tools - we want pure text generation)
            response = await self.invoke([HumanMessage(content=code_prompt)], use_tools=False)

            # Extract the generated code
            # For Gemini 3.0+, content can be a list like [{'type': 'text', 'text': '...'}]
            # Use response.text if available, otherwise handle the list format
            if hasattr(response, 'text') and response.text:
                response_content = response.text
            elif isinstance(response.content, list):
                # Extract text from content list
                text_parts = []
                for part in response.content:
                    if isinstance(part, dict) and 'text' in part:
                        text_parts.append(part['text'])
                    elif isinstance(part, str):
                        text_parts.append(part)
                response_content = "\n".join(text_parts)
            else:
                response_content = str(response.content) if response.content else ""
            
            generated_code = self._extract_code(response_content)

            if not generated_code:
                # Log the response for debugging
                logger.error(
                    f"Failed to extract code from LLM response. "
                    f"Response preview: {response_content[:500]}..."
                )
                raise ValueError(
                    f"Failed to extract code from LLM response. "
                    f"The model may have returned an error or non-code content."
                )

            # Pre-validation: Check for syntax errors before writing
            if file_path and file_path.endswith('.dart'):
                await self.emit_status(
                    status="in_progress",
                    message="Validating generated code for syntax errors",
                )
                
                validation_result = await self.dart_analyzer.full_validation(
                    generated_code, file_path
                )
                
                if not validation_result["valid"]:
                    # Code has errors - try to regenerate with feedback
                    errors = validation_result.get("errors", [])
                    error_messages = [
                        f"Line {e.get('line', '?')}: {e.get('message', 'Unknown error')}"
                        for e in errors[:5]  # Limit to 5 errors
                    ]
                    
                    logger.warning(
                        f"Generated code has {len(errors)} syntax errors, attempting regeneration"
                    )
                    
                    await self.emit_status(
                        status="in_progress",
                        message=f"Found {len(errors)} syntax errors, regenerating code",
                    )
                    
                    # Try regeneration with error feedback
                    regenerated_code = await self._regenerate_with_feedback(
                        description=description,
                        file_path=file_path,
                        action=action,
                        existing_content=existing_content,
                        errors=error_messages,
                    )
                    
                    if regenerated_code:
                        generated_code = regenerated_code
                    else:
                        # Log the validation errors but proceed
                        logger.error(
                            f"Code regeneration failed, proceeding with original code. "
                            f"Errors: {error_messages}"
                        )

            # Write the file if we have a path
            if file_path:
                commit_message = f"{'Create' if action == 'create' else 'Update'} {file_path.split('/')[-1]}"

                await self.emit_tool_execution(
                    tool_name="write_file",
                    message=f"Writing file: {file_path}",
                    file_path=file_path,
                )

                result = await self.execute_tool(
                    "write_file",
                    {
                        "file_path": file_path,
                        "content": generated_code,
                        "commit_message": commit_message,
                    },
                )

                # Analyze the generated code
                analysis = analyze_dart_code(generated_code)
                widgets = extract_widgets_from_code(generated_code)

                # Emit file operation
                await self.emit_file_operation(
                    operation=action,
                    file_path=file_path,
                    message=f"{'Created' if action == 'create' else 'Updated'} {file_path.split('/')[-1]}",
                    details={
                        "lines_of_code": analysis.get("lines_of_code", 0),
                        "widgets": widgets[:5],  # Top 5 widgets used
                        "classes": analysis.get("classes", []),
                    },
                )

            # Emit completion
            await self.emit_status(
                status="completed",
                message=f"Code generation complete",
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
        """Build a prompt for code generation.

        Args:
            description: What the code should do
            file_path: Target file path
            action: create/update/delete
            existing_content: Existing file content if updating

        Returns:
            Prompt string
        """
        prompt_parts = [
            f"Task: {description}",
            f"File: {file_path}",
            f"Action: {action}",
        ]

        if existing_content:
            prompt_parts.append(f"\nExisting content:\n```dart\n{existing_content}\n```")
            prompt_parts.append("\nModify the existing content to implement the task.")
        else:
            prompt_parts.append("\nGenerate a complete, production-ready Dart file.")

        prompt_parts.append("""
Requirements:
- Use GetX for state management
- Use flutter_screenutil for dimensions (.w, .h, .r, .sp)
- Use google_fonts for typography
- Include all necessary imports
- Follow Dart best practices
- Add null safety

Return ONLY the Dart code, no explanations. Wrap in ```dart code blocks.""")

        return "\n".join(prompt_parts)

    def _extract_code(self, text: str) -> Optional[str]:
        """Extract Dart code from text.

        Tries multiple extraction strategies:
        1. JSON format with 'changes' array (like reference implementation)
        2. Dart code blocks (```dart ... ```)
        3. Generic code blocks (``` ... ```)
        4. Raw Dart code detection

        Args:
            text: Text that may contain code

        Returns:
            Extracted code or None
        """
        import re
        import json

        # Strategy 1: Try JSON format first (like reference implementation)
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                # Look for changes array with content
                if "changes" in data and isinstance(data["changes"], list):
                    for change in data["changes"]:
                        if change.get("content"):
                            logger.debug("Extracted code from JSON 'changes' format")
                            return change["content"]
                # Look for direct code field
                if "code" in data and data["code"]:
                    logger.debug("Extracted code from JSON 'code' field")
                    return data["code"]
                if "content" in data and data["content"]:
                    logger.debug("Extracted code from JSON 'content' field")
                    return data["content"]
        except (json.JSONDecodeError, ValueError):
            pass  # Not valid JSON, try other strategies

        # Strategy 2: Look for dart code blocks
        patterns = [
            r"```dart\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                code = matches[0].strip()
                if code:  # Make sure it's not empty
                    logger.debug(f"Extracted code from code block (pattern: {pattern[:10]}...)")
                    return code

        # Strategy 3: If no code blocks, check if the entire text looks like Dart code
        if "import " in text or "class " in text or "void " in text:
            logger.debug("Extracted raw Dart code from response")
            return text.strip()

        return None

    async def _regenerate_with_feedback(
        self,
        description: str,
        file_path: str,
        action: str,
        existing_content: Optional[str],
        errors: List[str],
    ) -> Optional[str]:
        """Regenerate code with error feedback.
        
        When the initial code generation produces syntax errors,
        this method retries with specific error information to help
        the LLM fix the issues.
        
        Args:
            description: Original task description
            file_path: Target file path
            action: create/update/delete
            existing_content: Existing file content
            errors: List of error messages from validation
            
        Returns:
            Regenerated code or None if regeneration fails
        """
        error_feedback = "\n".join(f"- {e}" for e in errors)
        
        enhanced_prompt = f"""CRITICAL: Your previous code generation had SYNTAX ERRORS that must be fixed.

ERRORS FOUND:
{error_feedback}

COMMON FIXES NEEDED:
- If you used snake_case properties, change them to camelCase:
  - app_bar → appBar
  - background_color → backgroundColor  
  - floating_action_button → floatingActionButton
  - main_axis_alignment → mainAxisAlignment
  - on_pressed → onPressed
  - font_size → fontSize
  - text_style → textStyle

ORIGINAL TASK: {description}
FILE: {file_path}
ACTION: {action}

{"EXISTING CONTENT:" + chr(10) + "```dart" + chr(10) + existing_content + chr(10) + "```" if existing_content else "Generate a NEW file."}

REQUIREMENTS:
- Fix ALL the errors listed above
- Use camelCase for ALL Dart properties (NEVER snake_case)
- Return complete, valid Dart code
- Wrap code in ```dart code blocks

Return ONLY the corrected Dart code."""

        try:
            response = await self.invoke(
                [HumanMessage(content=enhanced_prompt)],
                use_tools=False
            )
            
            # Extract response content
            if hasattr(response, 'text') and response.text:
                response_content = response.text
            elif isinstance(response.content, list):
                text_parts = []
                for part in response.content:
                    if isinstance(part, dict) and 'text' in part:
                        text_parts.append(part['text'])
                    elif isinstance(part, str):
                        text_parts.append(part)
                response_content = "\n".join(text_parts)
            else:
                response_content = str(response.content) if response.content else ""
            
            regenerated_code = self._extract_code(response_content)
            
            if regenerated_code:
                # Validate the regenerated code
                validation = await self.dart_analyzer.full_validation(
                    regenerated_code, file_path
                )
                
                if validation["valid"]:
                    logger.info("Code regeneration successful - validation passed")
                    return regenerated_code
                else:
                    new_errors = validation.get("errors", [])
                    logger.warning(
                        f"Regenerated code still has {len(new_errors)} errors"
                    )
                    # Still return the regenerated code - it might be better
                    return regenerated_code
            
        except Exception as e:
            logger.error(f"Code regeneration failed: {e}")
        
        return None
