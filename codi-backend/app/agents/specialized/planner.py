"""Planner agent for strategic task decomposition."""
import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.agents.base import AgentContext, BaseAgent
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PlanStep(BaseModel):
    """A single step in the execution plan."""

    id: int = Field(..., description="Unique step ID")
    description: str = Field(..., description="What this step accomplishes")
    agent: str = Field(..., description="Which agent should execute this step")
    dependencies: List[int] = Field(
        default_factory=list,
        description="IDs of steps that must complete before this one",
    )
    file_path: Optional[str] = Field(None, description="Primary file affected by this step")
    action: str = Field(..., description="Action type: create, update, delete, analyze, review")


class ExecutionPlan(BaseModel):
    """Complete execution plan for a user request."""

    user_request: str = Field(..., description="Original user request")
    summary: str = Field(..., description="Brief summary of what will be done")
    steps: List[PlanStep] = Field(..., description="Ordered list of steps to execute")
    estimated_time_seconds: int = Field(120, description="Estimated time to complete")


class PlannerAgent(BaseAgent):
    """Agent responsible for analyzing user requests and creating execution plans.

    The Planner breaks down complex requests into atomic steps that other agents
    can execute independently. It understands the existing codebase structure
    and coordinates work across agents.
    """

    name = "planner"
    description = "Strategic task decomposition and coordination"

    system_prompt = """You are the Planner Agent for Codi, a multi-platform AI development platform.

Your role is to analyze user requests and create detailed execution plans that other specialized agents will follow.

## Your Responsibilities:
1. Understand the user's intent from their natural language request
2. DETECT the project framework from the repository structure
3. Break down complex requests into atomic, executable steps
4. Assign each step to the CORRECT platform-specific agent
5. Define dependencies between steps
6. Estimate time requirements

## Framework Detection:
Analyze the project files to detect the framework:
- **Flutter**: Look for pubspec.yaml, lib/*.dart files
- **React**: Look for package.json with "react", src/*.tsx files
- **Next.js**: Look for package.json with "next", app/ or pages/ directory
- **React Native**: Look for package.json with "react-native", App.tsx

## Available Agents:

### Platform-Specific Engineers (choose based on detected framework):
- flutter_engineer: Dart/Flutter code, widgets, state management (GetX)
- react_engineer: React/TypeScript code, hooks, components
- nextjs_engineer: Next.js App Router, Server/Client Components, API routes
- react_native_engineer: React Native components, navigation, native modules

### Support Agents (use for all platforms):
- code_reviewer: Reviews code changes for quality and best practices
- git_operator: Handles version control (branches, commits, pushes)
- build_deploy: Triggers builds and deployments
- backend_integration: Sets up Supabase/Firebase/Serverpod
- memory: Logs operations and maintains history

## Agent Selection Rules:
1. ALWAYS use the correct engineer for the project's framework
2. Use backend_integration for database/auth setup tasks
3. Always include code_reviewer after code changes
4. Always include git_operator to commit changes
5. Use build_deploy only when explicitly requested

## Planning Guidelines:
1. Each step should do ONE thing
2. File operations should be atomic (one file per step)
3. Always include a code review step after code changes
4. Always commit changes after review passes
5. Build and deploy only after commits
6. Consider the existing project structure - read files first if needed
7. Use descriptive step descriptions

## Output Format:
Return a JSON execution plan with this structure:
{{
    "user_request": "Original request",
    "summary": "Brief summary of what will be done",
    "detected_framework": "flutter|react|nextjs|react_native|unknown",
    "steps": [
        {{
            "id": 1,
            "description": "What this step does",
            "agent": "agent_name",
            "dependencies": [],
            "file_path": "path/to/file",
            "action": "create|update|delete|analyze|review"
        }}
    ],
    "estimated_time_seconds": 120
}}"""

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the planner."""

        @tool
        def list_project_files(path: str = "") -> str:
            """List files in the project repository.

            Args:
                path: Directory path to list (empty for root)

            Returns:
                JSON string with file listing
            """
            try:
                files = self.git_service.list_files(
                    path=path,
                    ref=self.context.current_branch,
                )
                return json.dumps([f.__dict__ for f in files], indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})

        @tool
        def read_file_content(file_path: str) -> str:
            """Read the content of a file in the repository.

            Args:
                file_path: Path to the file to read

            Returns:
                File content as string
            """
            try:
                content = self.git_service.get_file_content(
                    file_path=file_path,
                    ref=self.context.current_branch,
                )
                return content
            except Exception as e:
                return f"Error reading file: {e}"

        @tool
        def get_project_structure() -> str:
            """Get the overall project structure.

            Returns:
                JSON string with project structure summary
            """
            try:
                # Get root files
                root_files = self.git_service.list_files(
                    path="",
                    ref=self.context.current_branch,
                )

                # Get lib directory if it exists
                lib_files = []
                try:
                    lib_files = self.git_service.list_files(
                        path="lib",
                        ref=self.context.current_branch,
                    )
                except Exception:
                    pass

                structure = {
                    "root": [f.name for f in root_files],
                    "lib": [f.name for f in lib_files],
                }

                return json.dumps(structure, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})

        return [list_project_files, read_file_content, get_project_structure]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an execution plan for the user's request.

        Args:
            input_data: Dictionary with 'user_message' key

        Returns:
            Dictionary with 'plan' key containing ExecutionPlan
        """
        user_message = input_data.get("user_message", "")

        if not user_message:
            raise ValueError("No user message provided")

        # Emit start status
        await self.emit_status(
            status="started",
            message=f"Analyzing your request: '{user_message[:100]}...' if len(user_message) > 100 else '{user_message}'",
        )

        try:
            # First, understand the project structure
            await self.emit_status(
                status="in_progress",
                message="Analyzing project structure",
            )

            # Get project structure
            project_structure = await self.execute_tool(
                "get_project_structure",
                {},
            )

            # Create the planning prompt
            planning_prompt = f"""
User Request: {user_message}

Current Project Structure:
{project_structure}

Project Path: {self.context.project_folder or "Not configured"}
Current Branch: {self.context.current_branch}

Create a detailed execution plan to fulfill this request. Consider the existing project structure and determine what files need to be created or modified.

Return ONLY a valid JSON object with the execution plan.
"""

            # Get the plan from the LLM
            await self.emit_status(
                status="planning",
                message="Creating execution plan",
            )

            response = await self.invoke([HumanMessage(content=planning_prompt)])

            # Parse the response
            response_text = response.content
            if isinstance(response_text, list):
                response_text = response_text[0] if response_text else ""

            # Extract JSON from response
            plan_json = self._extract_json(str(response_text))

            if not plan_json:
                # Create a default plan
                plan_json = {
                    "user_request": user_message,
                    "summary": "Process user request",
                    "steps": [
                        {
                            "id": 1,
                            "description": f"Analyze and implement: {user_message}",
                            "agent": "flutter_engineer",
                            "dependencies": [],
                            "action": "create",
                        },
                        {
                            "id": 2,
                            "description": "Review changes",
                            "agent": "code_reviewer",
                            "dependencies": [1],
                            "action": "review",
                        },
                        {
                            "id": 3,
                            "description": "Commit changes",
                            "agent": "git_operator",
                            "dependencies": [2],
                            "action": "create",
                        },
                    ],
                    "estimated_time_seconds": 120,
                }

            # Validate and create ExecutionPlan
            plan = ExecutionPlan(**plan_json)

            # Emit completion
            await self.emit_status(
                status="completed",
                message=f"Created execution plan with {len(plan.steps)} steps",
                details={
                    "total_steps": len(plan.steps),
                    "steps": [step.description for step in plan.steps],
                    "estimated_time": f"{plan.estimated_time_seconds // 60}m {plan.estimated_time_seconds % 60}s",
                },
            )

            return {"plan": plan}

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            await self.emit_error(
                error=str(e),
                message="Failed to create execution plan",
            )
            raise

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from text.

        Args:
            text: Text that may contain JSON

        Returns:
            Parsed JSON dict or None
        """
        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Look for JSON in code blocks
        import re

        json_patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"\{[\s\S]*\}",
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the match
                    clean = match.strip()
                    if not clean.startswith("{"):
                        continue
                    return json.loads(clean)
                except json.JSONDecodeError:
                    continue

        return None
