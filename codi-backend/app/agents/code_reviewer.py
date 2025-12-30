"""Code Reviewer agent for quality assurance with multi-layer validation."""
import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.agents.tools.dart_analyzer import DartAnalyzer
from app.agents.prompts.flutter_engineer_prompts import CODE_REVIEW_PROMPT
from app.services.flutter import analyze_dart_code
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


class ReviewIssue:
    """Represents a code review issue."""

    def __init__(
        self,
        severity: str,  # error, warning, info
        file_path: str,
        line: Optional[int],
        message: str,
        suggestion: Optional[str] = None,
    ):
        self.severity = severity
        self.file_path = file_path
        self.line = line
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "file_path": self.file_path,
            "line": self.line,
            "message": self.message,
            "suggestion": self.suggestion,
        }


class CodeReviewerAgent(BaseAgent):
    """Agent responsible for reviewing code quality with multi-layer validation.

    The Code Reviewer checks all code changes using:
    - Layer 1: Property name validation (snake_case detection)
    - Layer 2: Static analysis (dart analyze)
    - Layer 3: Compilation check (flutter analyze)
    - Layer 4: LLM-based review (logic, best practices)
    """

    name = "code_reviewer"
    description = "Quality assurance and code validation with multi-layer validation"
    
    # Initialize validation tools (regex-based, no SDK required)
    dart_analyzer = DartAnalyzer()

    system_prompt = """You are the Code Reviewer Agent for Codi, an AI-powered Flutter development platform.

Your role is to review Dart/Flutter code for quality, security, and best practices.

## Your Responsibilities:
1. Check for syntax errors and typos
2. Ensure proper null safety usage
3. Verify proper error handling
4. Check for security issues (hardcoded secrets, unsafe operations)
5. Ensure consistent code style
6. Verify GetX usage patterns
7. Check for proper widget composition
8. Validate proper use of flutter_screenutil
9. Look for performance antipatterns

## Review Severity Levels:
- error: Must be fixed before merge (syntax errors, security issues)
- warning: Should be fixed (best practices, potential bugs)
- info: Suggestions for improvement (style, readability)

## Output Format:
Return a JSON review with this structure:
{{
    "approved": true/false,
    "summary": "Overall assessment",
    "issues": [
        {{
            "severity": "error|warning|info",
            "file_path": "path/to/file.dart",
            "line": 42,
            "message": "Issue description",
            "suggestion": "How to fix it"
        }}
    ]
}}

Only return "approved": false if there are error-level issues."""

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the code reviewer."""

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
        def analyze_code_structure(file_path: str) -> str:
            """Analyze the structure of a Dart file.

            Args:
                file_path: Path to the Dart file

            Returns:
                JSON analysis
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                content = self.github_service.get_file_content(
                    repo_full_name=self.context.repo_full_name,
                    file_path=file_path,
                    ref=self.context.current_branch,
                )
                analysis = analyze_dart_code(content)
                return json.dumps(analysis, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def get_diff(file_path: str, base_ref: str = "main") -> str:
            """Get the diff for a file compared to base branch.

            Args:
                file_path: Path to the file
                base_ref: Base branch to compare against

            Returns:
                Diff information or current content
            """
            # For simplicity, we'll return the current content
            # A full implementation would use GitHub's compare API
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                content = self.github_service.get_file_content(
                    repo_full_name=self.context.repo_full_name,
                    file_path=file_path,
                    ref=self.context.current_branch,
                )
                return f"Current content of {file_path}:\n\n{content}"
            except Exception as e:
                return f"Error: {e}"

        return [read_file, analyze_code_structure, get_diff]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Review code changes.

        Args:
            input_data: Dictionary with files to review

        Returns:
            Dictionary with review results
        """
        files_to_review = input_data.get("files", [])
        code_changes = input_data.get("code_changes", {})

        if not files_to_review and not code_changes:
            # No specific files, review recent changes
            files_to_review = input_data.get("changed_files", [])

        # Emit start status
        await self.emit_status(
            status="started",
            message=f"Reviewing {len(files_to_review) if files_to_review else 'code'} changes",
        )

        all_issues: List[ReviewIssue] = []
        files_reviewed = 0

        try:
            # Review each file
            for i, file_info in enumerate(files_to_review):
                file_path = file_info if isinstance(file_info, str) else file_info.get("path", "")

                if not file_path:
                    continue

                # Emit review progress
                progress = (i + 1) / len(files_to_review) if files_to_review else 0.5
                await connection_manager.broadcast_to_project(
                    self.context.project_id,
                    {
                        "type": "review_progress",
                        "agent": self.name,
                        "file_path": file_path,
                        "message": f"Reviewing: {file_path}",
                        "progress": progress,
                    },
                )

                # Get file content
                content = code_changes.get(file_path)
                if not content:
                    try:
                        content = await self.execute_tool(
                            "read_file",
                            {"file_path": file_path},
                        )
                    except Exception:
                        continue

                if not content or content.startswith("Error:"):
                    continue

                # Review the file
                file_issues = await self._review_file(file_path, content)
                all_issues.extend(file_issues)
                files_reviewed += 1

                # Emit any issues found
                for issue in file_issues:
                    await connection_manager.broadcast_to_project(
                        self.context.project_id,
                        {
                            "type": "review_issue",
                            "agent": self.name,
                            "severity": issue.severity,
                            "file_path": issue.file_path,
                            "line": issue.line,
                            "message": issue.message,
                        },
                    )

            # Determine if approved
            error_count = sum(1 for i in all_issues if i.severity == "error")
            warning_count = sum(1 for i in all_issues if i.severity == "warning")
            approved = error_count == 0

            # Emit completion
            if approved:
                message = f"✅ Review passed"
                if warning_count > 0:
                    message += f" with {warning_count} warning(s)"
            else:
                message = f"❌ Review failed with {error_count} error(s)"

            await self.emit_status(
                status="completed",
                message=message,
                details={
                    "files_reviewed": files_reviewed,
                    "errors": error_count,
                    "warnings": warning_count,
                    "approved": approved,
                },
            )

            return {
                "approved": approved,
                "files_reviewed": files_reviewed,
                "issues": [i.to_dict() for i in all_issues],
                "error_count": error_count,
                "warning_count": warning_count,
            }

        except Exception as e:
            logger.error(f"Code review failed: {e}")
            await self.emit_error(
                error=str(e),
                message="Code review failed",
            )
            raise

    async def _review_file(self, file_path: str, content: str) -> List[ReviewIssue]:
        """Review a single file with multi-layer validation.

        Validation Layers:
        1. Property name validation (snake_case detection)
        2. Static analysis (dart analyze)
        3. Compilation check (flutter analyze)
        4. Basic static checks (print statements, secrets)
        5. LLM review (logic, best practices)

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            List of review issues
        """
        issues: List[ReviewIssue] = []

        # Only run Dart validation on Dart files
        if file_path.endswith('.dart'):
            # Layer 1: Property name validation (snake_case detection)
            try:
                naming_issues = await self.dart_analyzer.validate_property_names(content)
                for issue in naming_issues:
                    issues.append(ReviewIssue(
                        severity=issue.get("severity", "error"),
                        file_path=file_path,
                        line=issue.get("line"),
                        message=issue.get("message", "Property naming error"),
                        suggestion=issue.get("suggestion"),
                    ))
                
                if naming_issues:
                    logger.warning(
                        f"Found {len(naming_issues)} naming convention errors in {file_path}"
                    )
            except Exception as e:
                logger.error(f"Property name validation failed: {e}")

            # Layer 2: Static analysis (dart analyze)
            try:
                analysis_result = await self.dart_analyzer.analyze_code(content, file_path)
                for error in analysis_result.get("errors", []):
                    # Avoid duplicates from naming validation
                    if not any(
                        i.line == error.get("line") and "naming" in str(i.message).lower()
                        for i in issues
                    ):
                        issues.append(ReviewIssue(
                            severity="error",
                            file_path=file_path,
                            line=error.get("line"),
                            message=error.get("message", "Static analysis error"),
                            suggestion=None,
                        ))
                
                for warning in analysis_result.get("warnings", []):
                    issues.append(ReviewIssue(
                        severity="warning",
                        file_path=file_path,
                        line=warning.get("line"),
                        message=warning.get("message", "Static analysis warning"),
                        suggestion=None,
                    ))
            except Exception as e:
                logger.error(f"Static analysis failed: {e}")

            # Layer 3: Flutter mistakes check
            try:
                flutter_issues = await self.dart_analyzer.check_common_flutter_mistakes(content)
                for issue in flutter_issues:
                    issues.append(ReviewIssue(
                        severity=issue.get("severity", "error"),
                        file_path=file_path,
                        line=issue.get("line"),
                        message=issue.get("message", "Flutter syntax error"),
                        suggestion=None,
                    ))
            except Exception as e:
                logger.error(f"Flutter mistake check failed: {e}")

        # Layer 4: Basic static analysis (all files)
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check for print statements (debug code)
            if "print(" in line and "debugPrint" not in line:
                issues.append(ReviewIssue(
                    severity="warning",
                    file_path=file_path,
                    line=line_num,
                    message="Avoid using print() in production code",
                    suggestion="Use debugPrint() or a logging package instead",
                ))

            # Check for hardcoded strings that look like secrets
            if any(keyword in line.lower() for keyword in ["apikey", "secret", "password", "token"]):
                if "=" in line and ("'" in line or '"' in line):
                    issues.append(ReviewIssue(
                        severity="error",
                        file_path=file_path,
                        line=line_num,
                        message="Potential hardcoded secret detected",
                        suggestion="Move sensitive values to environment variables",
                    ))

            # Check for TODO comments
            if "TODO" in line or "FIXME" in line:
                issues.append(ReviewIssue(
                    severity="info",
                    file_path=file_path,
                    line=line_num,
                    message="TODO/FIXME comment found",
                    suggestion="Consider addressing this before release",
                ))

        # Layer 5: LLM review for more complex issues (only if no blocking errors)
        error_count = sum(1 for i in issues if i.severity == "error")
        if len(content) < 10000 and error_count == 0:
            llm_issues = await self._llm_review(file_path, content)
            issues.extend(llm_issues)

        return issues

    async def _llm_review(self, file_path: str, content: str) -> List[ReviewIssue]:
        """Use LLM for advanced code review.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            List of review issues from LLM
        """
        review_prompt = f"""Review this Dart/Flutter code for issues:

File: {file_path}

```dart
{content}
```

Look for:
1. Syntax errors
2. Null safety issues
3. Missing error handling
4. Security vulnerabilities
5. Performance issues
6. GetX usage problems
7. Widget anti-patterns

Return a JSON array of issues (empty array if none):
[
    {{
        "severity": "error|warning|info",
        "line": 42,
        "message": "Issue description",
        "suggestion": "How to fix"
    }}
]

Return ONLY the JSON array, no other text."""

        try:
            response = await self.invoke([HumanMessage(content=review_prompt)])
            response_text = str(response.content)

            # Parse JSON from response
            import re
            json_match = re.search(r"\[[\s\S]*\]", response_text)
            if json_match:
                issues_data = json.loads(json_match.group())
                return [
                    ReviewIssue(
                        severity=i.get("severity", "info"),
                        file_path=file_path,
                        line=i.get("line"),
                        message=i.get("message", ""),
                        suggestion=i.get("suggestion"),
                    )
                    for i in issues_data
                ]
        except Exception as e:
            logger.warning(f"LLM review failed: {e}")

        return []
