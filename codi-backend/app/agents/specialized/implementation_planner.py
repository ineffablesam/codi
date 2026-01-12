"""
Implementation Planner Agent

Creates detailed TODO-driven implementation plans with user approval workflow.
Stores plans in .codi/ folder and tracks progress through iterations.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, BaseAgent
from app.core.database import get_db_context
from app.models.plan import ImplementationPlan, PlanStatus, PlanTask
from app.models.project import Project
from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


# System prompt for the planning agent
PLANNER_SYSTEM_PROMPT = """You are the Implementation Planner agent for Codi.

Your role is to create detailed, actionable implementation plans that break down user requests into atomic tasks.

## Core Responsibilities:

1. **Analyze User Requests**: Understand what the user wants to build
2. **Create TODO Lists**: Generate markdown with checkboxes [ ] for each task
3. **Provide Implementation Strategy**: Step-by-step execution plan
4. **Identify Files**: List files to create and modify
5. **Assess Risks**: Highlight potential issues
6. **Set Success Criteria**: Define what "done" looks like

## Output Format:

You MUST generate a valid markdown document with this EXACT structure:

```markdown
# Implementation Plan: [Feature Name]

**Created**: [ISO timestamp]
**Status**: pending_review
**Estimated Time**: [X hours/days]

## Overview
[2-3 sentence description of what will be implemented]

## Prerequisites
- [ ] Analyze existing codebase structure
- [ ] Identify affected files and components
- [ ] Review design requirements

## Implementation Tasks

### 1. [Category Name]
- [ ] [Specific task with clear acceptance criteria]
- [ ] [Another specific task]

### 2. [Another Category]
- [ ] [Task description]

## Implementation Strategy

### Phase 1: [Phase Name] (Est. X min)
1. [Step-by-step instructions]
2. [Next step]

### Phase 2: [Phase Name] (Est. X min)
1. [Detailed steps]

## Files to Create
- `path/to/file1.dart` - [Purpose]
- `path/to/file2.py` - [Purpose]

## Files to Modify
- `path/to/existing.dart` - [What changes]
- `path/to/another.py` - [What changes]

## Potential Risks
- ⚠️ [Risk description] → [Mitigation strategy]

## Success Criteria
- ✅ [Measurable success criterion]
- ✅ [Another criterion]
```

## Critical Rules:

1. **Be Specific**: Every task must be atomic and actionable
2. **Use Checkboxes**: Every task MUST start with `- [ ]`
3. **Estimate Time**: Provide realistic time estimates for each phase
4. **List All Files**: Explicitly list every file that will be created or modified
5. **Identify Risks**: Think about what could go wrong
6. **Define Success**: Clear, measurable criteria for completion

## Examples of Good vs Bad Tasks:

❌ BAD: "Create profile screen"
✅ GOOD: "Create ProfileScreen widget with header, bio section, and edit button in lib/features/profile/views/profile_screen.dart"

❌ BAD: "Add navigation"
✅ GOOD: "Update lib/config/routes.dart to add '/profile' route and configure GetX page binding"

❌ BAD: "Setup state management"
✅ GOOD: "Create ProfileController extending GetxController with reactive user model and edit/save methods"

Now generate a comprehensive implementation plan for the user's request."""


class ImplementationPlannerAgent(BaseAgent):
    """
    Specialized agent for creating detailed implementation plans with TODO tracking.
    """

    name = "implementation_planner"
    description = "Creates detailed implementation plans with TODO tracking and user approval workflow"
    system_prompt = PLANNER_SYSTEM_PROMPT

    def __init__(self, context: AgentContext) -> None:
        """Initialize the Implementation Planner agent."""
        super().__init__(context)

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the planner - primarily analysis tools."""
        project_folder = self.context.project_folder

        @tool
        def list_project_files(path: str = "") -> str:
            """List files in the project repository.

            Args:
                path: Directory path to list (empty for root)

            Returns:
                JSON string with file listing
            """
            if not project_folder:
                return json.dumps({"error": "No project folder configured"})

            target_path = Path(project_folder) / path
            if not target_path.exists():
                return json.dumps({"error": f"Path not found: {path}"})

            files = []
            dirs = []
            try:
                for item in target_path.iterdir():
                    # Skip hidden files and common excludes
                    if item.name.startswith('.') or item.name in ['node_modules', 'build', '.dart_tool', 'venv', '__pycache__']:
                        continue
                    if item.is_file():
                        files.append(item.name)
                    else:
                        dirs.append(item.name + "/")
            except PermissionError:
                return json.dumps({"error": "Permission denied"})

            return json.dumps({"directories": sorted(dirs), "files": sorted(files)})

        @tool
        def read_file_content(file_path: str) -> str:
            """Read the content of a file in the repository.

            Args:
                file_path: Path to the file to read

            Returns:
                File content as string
            """
            if not project_folder:
                return "Error: No project folder configured"

            target_path = Path(project_folder) / file_path
            if not target_path.exists():
                return f"Error: File not found: {file_path}"

            try:
                content = target_path.read_text(encoding="utf-8")
                # Limit content size
                if len(content) > 10000:
                    content = content[:10000] + "\n... [truncated]"
                return content
            except Exception as e:
                return f"Error reading file: {e}"

        @tool
        def get_project_structure() -> str:
            """Get the overall project structure.

            Returns:
                JSON string with project structure summary
            """
            if not project_folder:
                return json.dumps({"error": "No project folder configured"})

            root_path = Path(project_folder)
            structure = {"directories": [], "key_files": [], "total_files": 0}

            # Important file patterns
            important_patterns = [
                "main.dart", "app.dart", "routes.dart",
                "pubspec.yaml", "README.md", "package.json",
                "main.py", "requirements.txt", "pyproject.toml"
            ]

            try:
                for item in root_path.rglob("*"):
                    if any(part.startswith('.') for part in item.parts):
                        continue
                    if any(skip in str(item) for skip in ['node_modules', 'build', '.dart_tool', 'venv', '__pycache__']):
                        continue

                    if item.is_file():
                        structure["total_files"] += 1
                        rel_path = str(item.relative_to(root_path))
                        if item.name in important_patterns:
                            structure["key_files"].append(rel_path)
                    elif item.is_dir():
                        rel_path = str(item.relative_to(root_path))
                        # Only include first level directories
                        if "/" not in rel_path:
                            structure["directories"].append(rel_path)

            except Exception as e:
                return json.dumps({"error": str(e)})

            return json.dumps(structure, indent=2)

        return [list_project_files, read_file_content, get_project_structure]

    async def create_plan(
        self,
        user_request: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Create a detailed implementation plan for user request.

        Args:
            user_request: User's feature request
            db: Database session

        Returns:
            Dict with plan_id, markdown_content, file_path, status
        """
        self.start_timer()

        try:
            # Notify frontend that planning started
            await self.emit_status(
                status="started",
                message=f"Analyzing your request: '{user_request[:100]}...'",
            )

            # Get project from database
            result = await db.execute(
                select(Project).where(Project.id == self.context.project_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {self.context.project_id} not found")

            # Analyze existing codebase
            await self.emit_status(
                status="in_progress",
                message="Reading existing codebase structure...",
            )

            codebase_context = await self._analyze_codebase(project.local_path)

            # Generate plan with LLM
            await self.emit_status(
                status="in_progress",
                message="Creating detailed implementation plan...",
            )

            messages = [
                HumanMessage(content=f"""User Request: {user_request}

Project Type: {project.framework or 'unknown'} ({project.platform_type or 'unknown'})
Existing Files: {codebase_context.get('total_files', 0)} files

Key Files:
{self._format_file_list(codebase_context.get('key_files', []))}

Directory Structure:
{self._format_dirs(codebase_context.get('directories', []))}

Create a comprehensive implementation plan for this request.""")
            ]

            response = await self.invoke_with_retry(messages)
            plan_markdown = response.content

            # Parse and validate plan
            await self.emit_status(
                status="in_progress",
                message="Validating plan structure...",
            )

            plan_data = self._parse_plan_markdown(plan_markdown)

            # Create .codi directory structure
            codi_dir = Path(project.local_path) / ".codi"
            plans_dir = codi_dir / "plans"
            plans_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            feature_slug = re.sub(r'[^a-z0-9]+', '-', user_request.lower())[:50].strip('-')
            filename = f"{timestamp}-{feature_slug}.md"
            file_path = plans_dir / filename

            # Save plan to file
            file_path.write_text(plan_markdown, encoding="utf-8")

            # Save to database
            db_plan = ImplementationPlan(
                project_id=self.context.project_id,
                title=plan_data['title'],
                user_request=user_request,
                markdown_content=plan_markdown,
                file_path=str(file_path),
                status=PlanStatus.PENDING_REVIEW,
                estimated_time=plan_data['estimated_time'],
                total_tasks=plan_data['total_tasks'],
                completed_tasks=0,
            )
            db.add(db_plan)
            await db.flush()
            await db.refresh(db_plan)

            # Parse tasks and save to database
            order_idx = 0
            for category, tasks in plan_data['tasks'].items():
                for task_desc in tasks:
                    db_task = PlanTask(
                        plan_id=db_plan.id,
                        category=category,
                        description=task_desc,
                        order_index=order_idx,
                        completed=False,
                    )
                    db.add(db_task)
                    order_idx += 1

            await db.commit()
            await db.refresh(db_plan)

            # Send completion status with plan details
            await self.emit_status(
                status="completed",
                message=f"Implementation plan created with {plan_data['total_tasks']} tasks",
                details={
                    "plan_id": db_plan.id,
                    "total_tasks": plan_data['total_tasks'],
                    "estimated_time": plan_data['estimated_time'],
                    "file_path": str(file_path),
                },
            )

            # Send plan_ready event to frontend
            await self._send_plan_ready(
                plan_id=db_plan.id,
                markdown_content=plan_markdown,
            )

            # Log operation
            await self.log_operation(
                operation_type="plan_created",
                message=f"Created implementation plan: {plan_data['title']}",
                status="completed",
                details={"plan_id": db_plan.id, "total_tasks": plan_data['total_tasks']},
                duration_ms=self.get_duration_ms(),
            )

            return {
                "plan_id": db_plan.id,
                "markdown_content": plan_markdown,
                "file_path": str(file_path),
                "status": "pending_review",
                "total_tasks": plan_data['total_tasks'],
                "estimated_time": plan_data['estimated_time'],
            }

        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            await self.emit_status(
                status="failed",
                message=f"Failed to create plan: {str(e)}",
            )
            raise

    async def update_task_status(
        self,
        plan_id: int,
        task_id: int,
        completed: bool,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Update task completion status and tick checkbox in markdown.

        Args:
            plan_id: Plan identifier
            task_id: Task identifier
            completed: Whether task is completed
            db: Database session

        Returns:
            Updated plan status
        """
        # Get task from database
        result = await db.execute(
            select(PlanTask).where(PlanTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update task
        task.completed = completed
        task.completed_at = datetime.utcnow() if completed else None

        # Get plan and update progress
        result = await db.execute(
            select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Count completed tasks
        result = await db.execute(
            select(PlanTask).where(
                PlanTask.plan_id == plan_id,
                PlanTask.completed == True  # noqa
            )
        )
        completed_tasks = len(result.scalars().all())
        if completed:
            completed_tasks += 1  # Include current task being completed

        plan.completed_tasks = completed_tasks

        # Update markdown file - tick checkbox
        await self._update_markdown_checkbox(
            plan.file_path,
            task.description,
            completed,
        )

        await db.commit()

        # Calculate progress
        progress = completed_tasks / plan.total_tasks if plan.total_tasks > 0 else 0

        # Send WebSocket update
        await self._send_task_update(
            plan_id=plan_id,
            task_id=task_id,
            completed=completed,
            progress=progress,
        )

        # Check if all tasks completed
        if completed_tasks >= plan.total_tasks:
            await self._handle_plan_completion(plan, db)

        return {
            "task_id": task_id,
            "completed": completed,
            "progress": progress,
            "total_completed": completed_tasks,
            "total_tasks": plan.total_tasks,
        }

    async def _handle_plan_completion(
        self,
        plan: ImplementationPlan,
        db: AsyncSession,
    ) -> None:
        """Generate walkthrough when all tasks are completed."""
        await self.emit_status(
            status="in_progress",
            message="All tasks completed! Generating walkthrough...",
        )

        # Get all tasks for walkthrough
        result = await db.execute(
            select(PlanTask).where(PlanTask.plan_id == plan.id).order_by(PlanTask.order_index)
        )
        tasks = result.scalars().all()

        # Generate walkthrough
        walkthrough = await self._generate_walkthrough(plan, tasks)

        # Save walkthrough
        codi_dir = Path(plan.file_path).parent.parent
        walkthrough_dir = codi_dir / "walkthroughs"
        walkthrough_dir.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        feature_slug = re.sub(r'[^a-z0-9]+', '-', plan.title.lower())[:50].strip('-')
        walkthrough_filename = f"{timestamp}-{feature_slug}-walkthrough.md"
        walkthrough_path = walkthrough_dir / walkthrough_filename

        walkthrough_path.write_text(walkthrough, encoding="utf-8")

        # Update plan
        plan.status = PlanStatus.COMPLETED
        plan.walkthrough_path = str(walkthrough_path)
        plan.completed_at = datetime.utcnow()
        await db.commit()

        # Send walkthrough to frontend
        await self._send_walkthrough_ready(
            plan_id=plan.id,
            walkthrough_content=walkthrough,
        )

    async def _generate_walkthrough(
        self,
        plan: ImplementationPlan,
        tasks: List[PlanTask],
    ) -> str:
        """Generate comprehensive walkthrough of completed implementation."""
        duration = self._calculate_duration(plan.created_at, datetime.utcnow())
        tasks_summary = self._format_tasks_for_walkthrough(tasks)

        walkthrough_prompt = f"""Generate a comprehensive walkthrough document for this completed implementation.

Original Request: {plan.user_request}
Plan Title: {plan.title}
Total Tasks Completed: {len(tasks)}
Time Taken: {duration}

Tasks Completed:
{tasks_summary}

Create a markdown document with:
1. 🎉 Celebration header
2. Overview of what was built
3. Technical decisions and rationale
4. Key code highlights
5. Files created/modified summary
6. What to test/verify
7. Next steps/future enhancements

Make it celebratory and informative. This is a completion document."""

        messages = [HumanMessage(content=walkthrough_prompt)]
        response = await self.invoke_with_retry(messages)
        return response.content

    def _parse_plan_markdown(self, markdown: str) -> Dict[str, Any]:
        """Parse markdown plan and extract structured data."""
        lines = markdown.split('\n')

        # Extract title
        title = "Untitled Plan"
        for line in lines:
            if line.startswith('# Implementation Plan:'):
                title = line.replace('# Implementation Plan:', '').strip()
                break
            elif line.startswith('# '):
                title = line[2:].strip()
                break

        # Extract estimated time
        estimated_time = "Unknown"
        for line in lines:
            if '**Estimated Time**:' in line or 'Estimated Time:' in line:
                match = re.search(r':\s*(.+?)(?:\*\*|$)', line)
                if match:
                    estimated_time = match.group(1).strip()
                break

        # Extract tasks (lines with - [ ])
        tasks: Dict[str, List[str]] = {}
        current_category = "General"
        task_count = 0

        for i, line in enumerate(lines):
            # Check for category headers (### X. Category or ### Category)
            if line.startswith('### '):
                category_text = line[4:].strip()
                # Remove numbering if present
                category_text = re.sub(r'^\d+\.\s*', '', category_text)
                if category_text:
                    current_category = category_text
                    if current_category not in tasks:
                        tasks[current_category] = []

            # Check for task items (- [ ] Task)
            if re.match(r'^\s*-\s*\[\s*\]\s+', line):
                task_desc = re.sub(r'^\s*-\s*\[\s*\]\s+', '', line).strip()
                if task_desc:
                    if current_category not in tasks:
                        tasks[current_category] = []
                    tasks[current_category].append(task_desc)
                    task_count += 1

        return {
            'title': title,
            'estimated_time': estimated_time,
            'tasks': tasks,
            'total_tasks': task_count,
        }

    async def _update_markdown_checkbox(
        self,
        file_path: str,
        task_description: str,
        completed: bool,
    ) -> None:
        """Update checkbox in markdown file."""
        try:
            path = Path(file_path)
            content = path.read_text(encoding="utf-8")

            # Escape special regex characters in task description
            escaped_desc = re.escape(task_description)

            if completed:
                # Replace unchecked with checked
                pattern = rf'-\s*\[\s*\]\s+{escaped_desc}'
                replacement = f'- [x] {task_description}'
            else:
                # Replace checked with unchecked
                pattern = rf'-\s*\[x\]\s+{escaped_desc}'
                replacement = f'- [ ] {task_description}'

            content = re.sub(pattern, replacement, content, count=1)
            path.write_text(content, encoding="utf-8")

        except Exception as e:
            logger.warning(f"Failed to update markdown checkbox: {e}")

    async def _analyze_codebase(self, project_path: Optional[str]) -> Dict[str, Any]:
        """Analyze existing codebase structure."""
        if not project_path:
            return {"files": [], "key_files": [], "directories": [], "total_files": 0}

        path = Path(project_path)
        if not path.exists():
            return {"files": [], "key_files": [], "directories": [], "total_files": 0}

        files = []
        key_files = []
        directories = []

        # Common important files to look for
        important_patterns = [
            'main.dart', 'app.dart', 'routes.dart',
            'pubspec.yaml', 'README.md', 'package.json',
            'main.py', 'requirements.txt', 'pyproject.toml',
        ]

        try:
            for file_path in path.rglob('*'):
                # Skip hidden and excluded directories
                if any(part.startswith('.') for part in file_path.relative_to(path).parts):
                    continue
                if any(skip in str(file_path) for skip in ['node_modules', 'build', '.dart_tool', 'venv', '__pycache__']):
                    continue

                if file_path.is_file():
                    rel_path = str(file_path.relative_to(path))
                    files.append(rel_path)

                    # Check if it's a key file
                    if file_path.name in important_patterns:
                        key_files.append(rel_path)

                elif file_path.is_dir():
                    rel_path = str(file_path.relative_to(path))
                    if '/' not in rel_path:  # First level only
                        directories.append(rel_path)

        except Exception as e:
            logger.warning(f"Error analyzing codebase: {e}")

        return {
            'files': files[:100],  # Limit to 100 files
            'key_files': key_files,
            'directories': sorted(directories),
            'total_files': len(files),
        }

    def _format_file_list(self, files: List[str]) -> str:
        """Format file list for LLM context."""
        if not files:
            return "- (none found)"
        return '\n'.join(f"- {f}" for f in files[:20])

    def _format_dirs(self, dirs: List[str]) -> str:
        """Format directory list for LLM context."""
        if not dirs:
            return "- (root only)"
        return '\n'.join(f"- {d}/" for d in dirs[:15])

    def _format_tasks_for_walkthrough(self, tasks: List[PlanTask]) -> str:
        """Format tasks for walkthrough generation."""
        output = []
        current_category = None

        for task in tasks:
            if task.category != current_category:
                current_category = task.category
                output.append(f"\n### {current_category}")
            output.append(f"- [x] {task.description}")

        return '\n'.join(output)

    def _calculate_duration(self, start: datetime, end: datetime) -> str:
        """Calculate human-readable duration."""
        if not start or not end:
            return "Unknown"

        delta = end - start
        hours = delta.total_seconds() / 3600

        if hours < 1:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minutes"
        else:
            return f"{hours:.1f} hours"

    async def _send_plan_ready(
        self,
        plan_id: int,
        markdown_content: str,
    ) -> None:
        """Send plan_ready event to frontend."""
        await connection_manager.broadcast_to_project(
            self.context.project_id,
            {
                "type": "plan_ready",
                "plan_id": plan_id,
                "markdown_content": markdown_content,
                "timestamp": datetime.utcnow().isoformat(),
                "action": "show_plan_for_review",
            },
        )

    async def _send_task_update(
        self,
        plan_id: int,
        task_id: int,
        completed: bool,
        progress: float,
    ) -> None:
        """Send task update via WebSocket."""
        await connection_manager.broadcast_to_project(
            self.context.project_id,
            {
                "type": "task_updated",
                "plan_id": plan_id,
                "task_id": task_id,
                "completed": completed,
                "progress": progress,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _send_walkthrough_ready(
        self,
        plan_id: int,
        walkthrough_content: str,
    ) -> None:
        """Send walkthrough_ready event to frontend."""
        await connection_manager.broadcast_to_project(
            self.context.project_id,
            {
                "type": "walkthrough_ready",
                "plan_id": plan_id,
                "walkthrough_content": walkthrough_content,
                "timestamp": datetime.utcnow().isoformat(),
                "action": "show_walkthrough",
            },
        )

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the planner agent.

        Args:
            input_data: Must contain 'user_request' key

        Returns:
            Plan creation result
        """
        user_request = input_data.get("user_request")
        if not user_request:
            raise ValueError("user_request is required in input_data")

        async with get_db_context() as db:
            return await self.create_plan(user_request, db)
