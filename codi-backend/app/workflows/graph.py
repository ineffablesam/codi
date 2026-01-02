"""LangGraph workflow graph definition with streaming support.

Refactored to match the reference implementation pattern:
- Direct LLM instantiation per node (no class-based agents for LLM calls)
- Streaming support for code generation
- Simplified response handling
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import END, StateGraph

from app.config import settings
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager
from app.workflows.state import (
    WorkflowState,
    get_next_executable_step,
    mark_step_completed,
    mark_step_failed,
)

logger = get_logger(__name__)


# =============================================================================
# PROMPTS (matching reference implementation)
# =============================================================================

PLANNER_PROMPT = """You are the Planner Agent for Codi, an AI-powered development platform.

Your role is to analyze user requests and decompose them into atomic, executable steps.

## Available Agents:
- flutter_engineer: Writes Flutter/Dart code, UI components, state management
- code_reviewer: Reviews code for quality, security, and best practices
- git_operator: Handles Git operations (branch, commit, push, PR)

## Output Format:
Provide a JSON plan with the following structure:
{{
  "summary": "Brief description of what will be done",
  "steps": [
    {{
      "step_number": 1,
      "agent": "agent_name",
      "action": "specific action to take",
      "description": "detailed description of what to do"
    }}
  ]
}}

## Guidelines:
- Be specific about file paths and changes
- Include code review steps for any code changes
- Always end with Git commit
- Keep plans simple and focused

Project: {project_name}
Repository: {repo_full_name}
"""

FLUTTER_ENGINEER_PROMPT = """You are the Flutter Engineer Agent for Codi.

Your role is to write high-quality Flutter/Dart code for mobile and web applications.

## CRITICAL RULES FOR MODIFICATIONS:
1. If modifying an existing file, you MUST preserve ALL existing code
2. Only change the EXACT lines necessary for the requested change
3. Do NOT reformat, reorganize, or "improve" other parts of the code
4. Do NOT add comments or documentation unless explicitly requested
5. Do NOT remove imports or other code unless explicitly requested
6. Match the existing code style exactly (indentation, spacing, naming)

## Code Standards:
- Use const constructors where possible
- Prefer final variables
- Write null-safe code using Dart 3.0+ features
- Handle loading and error states

## Output Format:
Return JSON with your changes:
{{
  "changes": [
    {{
      "path": "lib/path/to/file.dart",
      "action": "create" | "modify",
      "content": "full file content with minimal changes",
      "description": "what this change does",
      "lines_changed": 1,
      "lines_preserved": 150
    }}
  ]
}}

## IMPORTANT:
- When action is "modify", the content MUST include the ENTIRE existing file with ONLY the targeted lines changed
- The "lines_changed" and "lines_preserved" fields help track minimal changes
- If the user asks to "change", "update", "fix", or "modify" something, make the smallest possible change

Current task: {task_description}

{existing_file_section}

Current files in project:
{current_files}
"""


CODE_REVIEWER_PROMPT = """You are the Code Reviewer Agent for Codi.

Your role is to review code changes for quality, security, and best practices.

## Review Criteria:
1. Correctness: Does the code do what it's supposed to?
2. Security: Are there any security vulnerabilities?
3. Performance: Are there any performance issues?
4. Style: Does it follow Flutter/Dart coding standards?

## Output Format:
{{
  "approved": true | false,
  "issues": ["list of issues found"],
  "suggestions": ["list of improvement suggestions"],
  "severity": "none" | "minor" | "major" | "critical"
}}

## Guidelines:
- Approve if issues are minor and don't block functionality
- Be constructive and specific

Changes to review:
{changes}
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_llm() -> ChatGoogleGenerativeAI:
    """Create a fresh LLM instance for each node invocation."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=1.0,
    )


def extract_json_from_response(content: str) -> Dict[str, Any]:
    """Extract JSON from LLM response content.
    
    Handles:
    - JSON wrapped in ```json ... ``` code blocks
    - Raw JSON in the response
    - Malformed responses (returns empty dict)
    """
    if not content:
        return {}
    
    # Try to strip code block wrappers
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(code_block_pattern, content, re.DOTALL)
    if match:
        content = match.group(1).strip()
    
    # Find JSON object
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
    
    return {}


async def broadcast_status(project_id: int, agent: str, status: str, message: str) -> None:
    """Send agent status update via WebSocket."""
    await connection_manager.send_agent_status(
        project_id=project_id,
        agent=agent,
        status=status,
        message=message,
    )


# =============================================================================
# AGENT NODES (Reference implementation pattern)
# =============================================================================

async def planner_node(state: WorkflowState) -> WorkflowState:
    """Planner agent node - creates execution plan.
    
    Uses direct LLM invocation matching reference implementation.
    """
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "planner", "started", "Analyzing request...")
    
    llm = create_llm()
    
    system_prompt = PLANNER_PROMPT.format(
        project_name=state.get("repo_full_name", "").split("/")[-1] if state.get("repo_full_name") else "project",
        repo_full_name=state.get("repo_full_name", ""),
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {state['user_message']}\n\nCreate a detailed execution plan."),
    ]
    
    try:
        # Stream the response for real-time updates
        full_content = ""
        chunk_count = 0
        
        async for chunk in llm.astream(messages):
            chunk_text = ""
            if hasattr(chunk, 'content'):
                if isinstance(chunk.content, list):
                    chunk_text = " ".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in chunk.content
                    )
                elif chunk.content:
                    chunk_text = str(chunk.content)
            
            if chunk_text:
                full_content += chunk_text
                chunk_count += 1
                
                # Send streaming updates every few chunks
                if chunk_count % 5 == 0:
                    await connection_manager.broadcast_to_project(
                        project_id,
                        {
                            "type": "llm_stream",
                            "agent": "planner",
                            "chunk": chunk_text,
                            "accumulated_length": len(full_content),
                        }
                    )
        
        logger.debug(f"Planner response content length: {len(full_content)}")
        
        plan_data = extract_json_from_response(full_content)
        
        # Build plan steps from response
        plan_steps = []
        for step in plan_data.get("steps", []):
            if not isinstance(step, dict):
                continue
            plan_steps.append({
                "id": step.get("step_number", len(plan_steps) + 1),
                "description": step.get("description", state["user_message"]),
                "agent": step.get("agent", "flutter_engineer"),
                "action": step.get("action", "implement"),
                "status": "pending",
                "result": None,
                "dependencies": [],
                "file_path": None,
            })
        
        # Default plan if none parsed
        if not plan_steps:
            plan_steps = [
                {"id": 1, "description": state["user_message"], "agent": "flutter_engineer", "action": "implement", "status": "pending", "result": None, "dependencies": [], "file_path": None},
                {"id": 2, "description": "Review code changes", "agent": "code_reviewer", "action": "review", "status": "pending", "result": None, "dependencies": [], "file_path": None},
                {"id": 3, "description": "Commit changes", "agent": "git_operator", "action": "commit", "status": "pending", "result": None, "dependencies": [], "file_path": None},
            ]
        
        # Ensure we have code_reviewer and git_operator steps
        has_reviewer = any(
            s["agent"].lower().replace("_", "").replace("-", "") == "codereviewer" or
            "review" in s["description"].lower()
            for s in plan_steps
        )
        has_git = any(
            s["agent"].lower().replace("_", "").replace("-", "") == "gitoperator" or
            "commit" in s["description"].lower()
            for s in plan_steps
        )
        
        if not has_reviewer:
            plan_steps.append({"id": len(plan_steps) + 1, "description": "Review code changes", "agent": "code_reviewer", "action": "review", "status": "pending", "result": None, "dependencies": [], "file_path": None})
        if not has_git:
            plan_steps.append({"id": len(plan_steps) + 1, "description": "Commit changes", "agent": "git_operator", "action": "commit", "status": "pending", "result": None, "dependencies": [], "file_path": None})
        
        await broadcast_status(project_id, "planner", "completed", f"Plan created with {len(plan_steps)} steps")
        
        return {
            **state,
            "plan": {
                "user_request": state["user_message"],
                "summary": plan_data.get("summary", "Process user request"),
                "steps": plan_steps,
                "estimated_time_seconds": 120,
            },
            "plan_steps": plan_steps,
            "current_agent": "planner",
            "next_agent": plan_steps[0]["agent"] if plan_steps else "flutter_engineer",
        }
        
    except Exception as e:
        logger.error(f"Planner failed: {e}")
        await broadcast_status(project_id, "planner", "failed", str(e))
        return {
            **state,
            "has_error": True,
            "error_message": str(e),
            "is_complete": True,
        }


async def flutter_engineer_node(state: WorkflowState) -> WorkflowState:
    """Flutter Engineer agent node - generates code with streaming and surgical editing.
    
    Uses direct LLM invocation with astream() for real-time updates.
    Fetches existing files from GitHub to enable minimal, surgical edits.
    """
    step = get_next_executable_step(state)
    if not step or step["agent"] != "flutter_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    repo_full_name = state.get("repo_full_name")
    current_branch = state.get("current_branch", "main")
    github_token = state.get("github_token", "")
    
    await broadcast_status(project_id, "flutter_engineer", "started", f"Working on: {task_description[:50]}...")
    
    # Classify task type to determine if surgical edit is needed
    surgical_keywords = ['change', 'update', 'modify', 'fix', 'correct', 'adjust', 
                         'rename', 'replace', 'swap', 'alter', 'set']
    is_surgical_edit = any(kw in task_description.lower() for kw in surgical_keywords)
    
    llm = create_llm()
    
    # Build file context from existing code_changes
    current_files = ""
    if state.get("code_changes"):
        for path, content in list(state["code_changes"].items())[:3]:
            current_files += f"\n### {path}\n```dart\n{content[:500]}\n```\n"
    
    # Try to fetch existing file from GitHub for surgical edits
    existing_file_section = ""
    if is_surgical_edit and repo_full_name and github_token:
        # Try to infer target file from task description
        target_file = None
        
        # Common Flutter file patterns
        file_patterns = {
            'main': 'lib/main.dart',
            'home': 'lib/features/home/views/home_screen.dart',
            'app bar': 'lib/main.dart',
            'appbar': 'lib/main.dart',
            'title': 'lib/main.dart',
        }
        
        for pattern, file_path in file_patterns.items():
            if pattern in task_description.lower():
                target_file = file_path
                break
        
        # If no pattern matched, default to main.dart for modifications
        if not target_file:
            target_file = 'lib/main.dart'
        
        # Fetch existing file content
        try:
            from app.services.github import GitHubService
            github_service = GitHubService(access_token=github_token)
            
            await connection_manager.send_tool_execution(
                project_id=project_id,
                agent="flutter_engineer",
                tool="read_file",
                message=f"Reading existing file: {target_file}",
                file_path=target_file,
            )
            
            existing_content = github_service.get_file_content(
                repo_full_name=repo_full_name,
                file_path=target_file,
                ref=current_branch,
            )
            
            line_count = len(existing_content.split('\n'))
            existing_file_section = f"""## EXISTING FILE TO MODIFY:
The following file exists and must be modified surgically. Preserve ALL existing code, only change the specific parts needed:

File: {target_file} ({line_count} lines)
```dart
{existing_content}
```

IMPORTANT: Your output MUST contain the complete file with ONLY the minimal changes applied. Do NOT remove or restructure any existing code.
"""
            await broadcast_status(
                project_id, "flutter_engineer", "in_progress", 
                f"Read {target_file} ({line_count} lines), applying surgical edit..."
            )
            
        except ValueError as e:
            logger.warning(f"Could not read existing file: {e}")
            existing_file_section = ""
        except Exception as e:
            logger.warning(f"Error fetching file from GitHub: {e}")
            existing_file_section = ""
    
    system_prompt = FLUTTER_ENGINEER_PROMPT.format(
        task_description=task_description,
        existing_file_section=existing_file_section,
        current_files=current_files or "No files loaded yet",
    )
    
    human_prompt = f"""Task: {task_description}

{"This is a SURGICAL EDIT task. Make the SMALLEST possible change to accomplish the task. Preserve all existing code." if is_surgical_edit else "Provide the complete file changes needed."}

Return JSON with format:
{{
  "changes": [
    {{"path": "lib/path/to/file.dart", "action": "{"modify" if is_surgical_edit else "create"}", "content": "complete file content", "description": "what this does", "lines_changed": N, "lines_preserved": M}}
  ]
}}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]
    
    try:
        # Stream the response for real-time updates
        full_content = ""
        chunk_count = 0
        
        async for chunk in llm.astream(messages):
            chunk_text = ""
            if hasattr(chunk, 'content'):
                if isinstance(chunk.content, list):
                    chunk_text = " ".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in chunk.content
                    )
                elif chunk.content:
                    chunk_text = str(chunk.content)
            
            if chunk_text:
                full_content += chunk_text
                chunk_count += 1
                
                # Send streaming updates every few chunks
                if chunk_count % 5 == 0:
                    await connection_manager.broadcast_to_project(
                        project_id,
                        {
                            "type": "llm_stream",
                            "agent": "flutter_engineer",
                            "chunk": chunk_text,
                            "accumulated_length": len(full_content),
                        }
                    )
        
        logger.debug(f"Flutter engineer response ({len(full_content)} chars): {full_content[:500]}")
        
        # Parse changes from response
        changes = []
        data = extract_json_from_response(full_content)
        
        if data.get("changes"):
            for change in data["changes"]:
                if isinstance(change, dict) and change.get("content"):
                    changes.append({
                        "path": change.get("path", "lib/main.dart"),
                        "action": change.get("action", "modify"),
                        "content": change["content"],
                        "description": change.get("description", task_description),
                        "lines_changed": change.get("lines_changed", 0),
                        "lines_preserved": change.get("lines_preserved", 0),
                    })
        
        # Fallback: extract dart code block
        if not changes:
            dart_pattern = r'```dart\s*(.*?)\s*```'
            matches = re.findall(dart_pattern, full_content, re.DOTALL)
            if matches:
                changes.append({
                    "path": "lib/main.dart",
                    "action": "modify",
                    "content": matches[0].strip(),
                    "description": task_description,
                    "lines_changed": 0,
                    "lines_preserved": 0,
                })
        
        # Update code changes in state
        code_changes = state.get("code_changes", {}).copy()
        for change in changes:
            code_changes[change["path"]] = change["content"]
            
            # Build detailed message with change stats
            lines_changed = change.get("lines_changed", 0)
            lines_preserved = change.get("lines_preserved", 0)
            if lines_changed or lines_preserved:
                message = f"{change['description']} (modified {lines_changed} lines, preserved {lines_preserved} lines)"
            else:
                message = change["description"]
            
            await connection_manager.send_file_operation(
                project_id=project_id,
                agent="flutter_engineer",
                operation=change["action"],
                file_path=change["path"],
                message=message,
                details={
                    "lines_changed": lines_changed,
                    "lines_preserved": lines_preserved,
                    "is_surgical": is_surgical_edit,
                },
            )
        
        if not changes:
            logger.warning(f"No code extracted from response. Content preview: {full_content[:300]}")
            await broadcast_status(project_id, "flutter_engineer", "warning", "No code changes extracted")
        else:
            status_msg = f"Generated {len(changes)} file(s)"
            if is_surgical_edit:
                status_msg = f"✅ Applied surgical edit to {len(changes)} file(s)"
            await broadcast_status(project_id, "flutter_engineer", "completed", status_msg)
        
        new_state = mark_step_completed(state, step["id"], {"changes": changes})
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "flutter_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Flutter engineer failed: {e}")
        await broadcast_status(project_id, "flutter_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def code_reviewer_node(state: WorkflowState) -> WorkflowState:
    """Code Reviewer agent node - reviews code changes."""
    step = get_next_executable_step(state)
    if not step or step["agent"] != "code_reviewer":
        # If no explicit review step, check if we have changes to review
        if not state.get("code_changes"):
            return state
        step = {"id": -1, "agent": "code_reviewer"}
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "code_reviewer", "started", "Reviewing code changes...")
    
    llm = create_llm()
    
    # Format changes for review
    changes_str = ""
    for path, content in state.get("code_changes", {}).items():
        changes_str += f"\n### {path}\n```dart\n{content[:2000]}\n```\n"
    
    system_prompt = CODE_REVIEWER_PROMPT.format(changes=changes_str or "No changes to review")
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Review the code changes above and provide your assessment."),
    ]
    
    try:
        # Stream the response for real-time updates
        full_content = ""
        chunk_count = 0
        
        async for chunk in llm.astream(messages):
            chunk_text = ""
            if hasattr(chunk, 'content'):
                if isinstance(chunk.content, list):
                    chunk_text = " ".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in chunk.content
                    )
                elif chunk.content:
                    chunk_text = str(chunk.content)
            
            if chunk_text:
                full_content += chunk_text
                chunk_count += 1
                
                # Send streaming updates every few chunks
                if chunk_count % 5 == 0:
                    await connection_manager.broadcast_to_project(
                        project_id,
                        {
                            "type": "llm_stream",
                            "agent": "code_reviewer",
                            "chunk": chunk_text,
                            "accumulated_length": len(full_content),
                        }
                    )
        
        logger.debug(f"Code reviewer response length: {len(full_content)}")
        
        review_data = extract_json_from_response(full_content)
        
        review_result = {
            "approved": review_data.get("approved", True),
            "issues": review_data.get("issues", []),
            "suggestions": review_data.get("suggestions", []),
            "severity": review_data.get("severity", "none"),
        }
        
        status = "approved" if review_result["approved"] else "needs_revision"
        await broadcast_status(project_id, "code_reviewer", "completed", f"Review {status}")
        
        new_state = dict(state)
        new_state["review_result"] = review_result
        new_state["current_agent"] = "code_reviewer"
        
        if step["id"] >= 0:
            new_state = mark_step_completed(new_state, step["id"], review_result)
        
        return new_state
        
    except Exception as e:
        logger.error(f"Code reviewer failed: {e}")
        await broadcast_status(project_id, "code_reviewer", "failed", str(e))
        if step["id"] >= 0:
            return mark_step_failed(state, step["id"], str(e))
        return state


async def git_operator_node(state: WorkflowState) -> WorkflowState:
    """Git Operator agent node - commits changes to GitHub.
    
    Uses the GitOperatorAgent class since it needs GitHub API access.
    """
    from app.agents.base import AgentContext
    from app.agents.git_operator import GitOperatorAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "git_operator":
        return state
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "git_operator", "started", "Committing changes...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        github_token=state.get("github_token", ""),
        repo_full_name=state["repo_full_name"],
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = GitOperatorAgent(context)
    
    try:
        files = [
            {"path": path, "content": content}
            for path, content in state.get("code_changes", {}).items()
        ]
        
        result = await agent.run({
            "operation": "commit",
            "files": files,
            "message": f"feat: {state['user_message'][:50]}",
        })
        
        await connection_manager.send_git_operation(
            project_id=project_id,
            operation="commit",
            message=f"Committed {len(files)} file(s)",
            commit_sha=result.get("commit_sha"),
            files_changed=len(files),
        )
        
        await broadcast_status(project_id, "git_operator", "completed", "Changes committed")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["git_result"] = result
        new_state["current_agent"] = "git_operator"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Git operator failed: {e}")
        await broadcast_status(project_id, "git_operator", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def build_deploy_node(state: WorkflowState) -> WorkflowState:
    """Build Deploy agent node - handles CI/CD."""
    from app.agents.base import AgentContext
    from app.agents.build_deploy import BuildDeployAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "build_deploy":
        return state
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "build_deploy", "started", "Starting build...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        github_token=state.get("github_token", ""),
        repo_full_name=state["repo_full_name"],
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = BuildDeployAgent(context)
    
    try:
        result = await agent.run({"branch": state["current_branch"]})
        
        await broadcast_status(project_id, "build_deploy", "completed", "Build completed")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["build_result"] = result
        new_state["current_agent"] = "build_deploy"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Build deploy failed: {e}")
        await broadcast_status(project_id, "build_deploy", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def react_engineer_node(state: WorkflowState) -> WorkflowState:
    """React Engineer agent node - generates React/TypeScript code."""
    from app.agents.base import AgentContext
    from app.agents.react_engineer import ReactEngineerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "react_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    
    await broadcast_status(project_id, "react_engineer", "started", f"Working on: {task_description[:50]}...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        github_token=state.get("github_token", ""),
        repo_full_name=state["repo_full_name"],
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = ReactEngineerAgent(context)
    
    try:
        result = await agent.run({"step": step})
        
        # Update code changes
        code_changes = state.get("code_changes", {}).copy()
        if result.get("file_path") and result.get("code"):
            code_changes[result["file_path"]] = result["code"]
        
        await broadcast_status(project_id, "react_engineer", "completed", "Code generation complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "react_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"React engineer failed: {e}")
        await broadcast_status(project_id, "react_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def nextjs_engineer_node(state: WorkflowState) -> WorkflowState:
    """Next.js Engineer agent node - generates Next.js App Router code."""
    from app.agents.base import AgentContext
    from app.agents.nextjs_engineer import NextjsEngineerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "nextjs_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    
    await broadcast_status(project_id, "nextjs_engineer", "started", f"Working on: {task_description[:50]}...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        github_token=state.get("github_token", ""),
        repo_full_name=state["repo_full_name"],
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = NextjsEngineerAgent(context)
    
    try:
        result = await agent.run({"step": step})
        
        code_changes = state.get("code_changes", {}).copy()
        if result.get("file_path") and result.get("code"):
            code_changes[result["file_path"]] = result["code"]
        
        await broadcast_status(project_id, "nextjs_engineer", "completed", "Code generation complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "nextjs_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Next.js engineer failed: {e}")
        await broadcast_status(project_id, "nextjs_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def react_native_engineer_node(state: WorkflowState) -> WorkflowState:
    """React Native Engineer agent node - generates React Native code."""
    from app.agents.base import AgentContext
    from app.agents.react_native_engineer import ReactNativeEngineerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "react_native_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    
    await broadcast_status(project_id, "react_native_engineer", "started", f"Working on: {task_description[:50]}...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        github_token=state.get("github_token", ""),
        repo_full_name=state["repo_full_name"],
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = ReactNativeEngineerAgent(context)
    
    try:
        result = await agent.run({"step": step})
        
        code_changes = state.get("code_changes", {}).copy()
        if result.get("file_path") and result.get("code"):
            code_changes[result["file_path"]] = result["code"]
        
        await broadcast_status(project_id, "react_native_engineer", "completed", "Code generation complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "react_native_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"React Native engineer failed: {e}")
        await broadcast_status(project_id, "react_native_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def backend_integration_node(state: WorkflowState) -> WorkflowState:
    """Backend Integration agent node - sets up Supabase/Firebase/Serverpod."""
    from app.agents.base import AgentContext
    from app.agents.backend_integration import BackendIntegrationAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "backend_integration":
        return state
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "backend_integration", "started", "Setting up backend integration...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        github_token=state.get("github_token", ""),
        repo_full_name=state["repo_full_name"],
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = BackendIntegrationAgent(context)
    
    try:
        # Detect framework and backend from state or step
        framework = state.get("detected_framework", "flutter")
        backend_type = step.get("backend_type", "supabase")
        
        result = await agent.run({
            "step": step,
            "framework": framework,
            "backend_type": backend_type,
        })
        
        await broadcast_status(project_id, "backend_integration", "completed", f"Backend integration complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["current_agent"] = "backend_integration"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Backend integration failed: {e}")
        await broadcast_status(project_id, "backend_integration", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def memory_node(state: WorkflowState) -> WorkflowState:
    """Memory agent node - logs operations to database."""
    from app.agents.base import AgentContext
    from app.agents.memory import MemoryAgent
    
    project_id = state["project_id"]
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        github_token="",
        repo_full_name=state["repo_full_name"],
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = MemoryAgent(context)
    
    try:
        started_at = datetime.fromisoformat(state["started_at"])
        duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        
        # Use lowercase enum values to match PostgreSQL
        operation_type = "agent_task_completed" if not state.get("has_error") else "agent_task_failed"
        
        await agent.run({
            "operation_type": operation_type,
            "agent_type": "system",
            "message": f"Task completed: {state['user_message'][:100]}",
            "status": "completed" if not state.get("has_error") else "failed",
            "duration_ms": duration_ms,
            "details": {
                "steps_completed": len([s for s in state.get("plan_steps", []) if s.get("status") == "completed"]),
                "files_changed": len(state.get("code_changes", {})),
            },
        })
        
    except Exception as e:
        logger.error(f"Memory logging failed: {e}")
    
    return {
        **state,
        "current_agent": "memory",
        "is_complete": True,
        "completed_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# ROUTING
# =============================================================================

def route_next_agent(state: WorkflowState) -> Literal["flutter_engineer", "react_engineer", "nextjs_engineer", "react_native_engineer", "backend_integration", "code_reviewer", "git_operator", "build_deploy", "memory", "__end__"]:
    """Determine the next agent to run based on state."""
    if state.get("has_error"):
        return "memory"
    
    if state.get("is_complete"):
        return END
    
    next_step = get_next_executable_step(state)
    
    if next_step:
        agent = next_step["agent"]
        # Map agent names to valid node names
        valid_agents = [
            "flutter_engineer", "react_engineer", "nextjs_engineer", 
            "react_native_engineer", "backend_integration",
            "code_reviewer", "git_operator", "build_deploy", "memory"
        ]
        if agent in valid_agents:
            return agent
        # Default based on detected framework or fall back to flutter
        framework = state.get("detected_framework", "flutter")
        framework_to_agent = {
            "flutter": "flutter_engineer",
            "react": "react_engineer",
            "nextjs": "nextjs_engineer",
            "react_native": "react_native_engineer",
        }
        return framework_to_agent.get(framework, "flutter_engineer")
    
    return "memory"


def create_workflow_graph() -> StateGraph:
    """Create the LangGraph workflow graph with multi-platform support."""
    graph = StateGraph(WorkflowState)
    
    # Core nodes
    graph.add_node("planner", planner_node)
    graph.add_node("flutter_engineer", flutter_engineer_node)
    graph.add_node("code_reviewer", code_reviewer_node)
    graph.add_node("git_operator", git_operator_node)
    graph.add_node("build_deploy", build_deploy_node)
    graph.add_node("memory", memory_node)
    
    # New platform-specific nodes
    graph.add_node("react_engineer", react_engineer_node)
    graph.add_node("nextjs_engineer", nextjs_engineer_node)
    graph.add_node("react_native_engineer", react_native_engineer_node)
    graph.add_node("backend_integration", backend_integration_node)
    
    graph.set_entry_point("planner")
    
    # Edge mapping for all agents
    edge_mapping = {
        "flutter_engineer": "flutter_engineer",
        "react_engineer": "react_engineer",
        "nextjs_engineer": "nextjs_engineer",
        "react_native_engineer": "react_native_engineer",
        "backend_integration": "backend_integration",
        "code_reviewer": "code_reviewer",
        "git_operator": "git_operator",
        "build_deploy": "build_deploy",
        "memory": "memory",
        END: END,
    }
    
    graph.add_conditional_edges("planner", route_next_agent, edge_mapping)
    
    # All engineer agents can route to any other agent
    all_agents = [
        "flutter_engineer", "react_engineer", "nextjs_engineer", 
        "react_native_engineer", "backend_integration",
        "code_reviewer", "git_operator", "build_deploy"
    ]
    for agent in all_agents:
        graph.add_conditional_edges(agent, route_next_agent, edge_mapping)
    
    graph.add_edge("memory", END)
    
    return graph
