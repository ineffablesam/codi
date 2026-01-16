"""Tool Definitions and Execution for the Coding Agent.

Provides tools for:
- File operations (read, write, edit, list, search)
- Code execution (sandboxed Python, bash commands)
- Docker preview builds
- Git operations

Based on baby-code reference with additions for Docker and Git.
"""
import fnmatch
import os
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent.executor import execute_code
from app.services.infrastructure.docker import get_docker_service
from app.services.infrastructure.git import LocalGitService


# Limits for file content
MAX_FILE_LINES = 500
MAX_LINE_LENGTH = 500


@dataclass
class AgentContext:
    """Context passed to agent tools during execution."""
    project_id: int
    user_id: int
    project_folder: str
    project_slug: Optional[str] = None
    current_branch: str = "main"
    framework: Optional[str] = None
    task_id: Optional[str] = None
    
    # Services (lazy loaded)
    _docker_service: Any = field(default=None, repr=False)
    _git_service: Any = field(default=None, repr=False)
    
    @property
    def docker_service(self):
        """Get Docker service (lazy load)."""
        if self._docker_service is None:
            from app.services.infrastructure.docker import get_docker_service
            self._docker_service = get_docker_service()
        return self._docker_service
    
    @property
    def git_service(self):
        """Get Git service (lazy load)."""
        if self._git_service is None:
            from app.services.infrastructure.git import LocalGitService
            self._git_service = LocalGitService(project_folder=self.project_folder)
        return self._git_service


# =============================================================================
# TOOL DEFINITIONS (JSON schemas for LLM)
# =============================================================================

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Returns content with line numbers. Large files are automatically truncated. Use offset/limit to read specific sections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to project root)"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed). Optional."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read. Optional."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a new file or overwrite existing file. Creates parent directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (relative to project root)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Edit an existing file by replacing a specific string. The old_string must match exactly and appear only once. Use for surgical edits instead of rewriting entire files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit (relative to project root)"
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace. Must match exactly once."
                },
                "new_string": {
                    "type": "string",
                    "description": "The string to replace it with"
                }
            },
            "required": ["path", "old_string", "new_string"]
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory. Supports recursive listing and glob pattern filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory to list (relative to project root, defaults to root)",
                    "default": "."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "If true, list files recursively",
                    "default": False
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.py', '*.dart')"
                }
            },
            "required": []
        }
    },
    {
        "name": "search_files",
        "description": "Search for a text pattern across files. Returns matching lines with file paths and line numbers. Great for finding function definitions, usages, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text pattern to search for (case-insensitive)"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (relative to project root)",
                    "default": "."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional glob pattern to filter files (e.g., '*.py')"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "run_python",
        "description": """Execute Python code in a sandboxed environment.

Use this to test code, run calculations, or verify implementations.

Restrictions:
- No file I/O (use read_file/write_file instead)
- No network access
- No dangerous imports
- 30 second timeout""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "run_bash",
        "description": """Execute a bash command in the project directory and return the output.

Use this to:
- Run shell commands (ls, cat, grep, etc.)
- Install dependencies (npm install, pip install, flutter pub get)
- Run build commands (npm run build, flutter build)
- Run tests (pytest, npm test, flutter test)
- Git operations (git status, git diff, etc.)

The command runs with a 60 second timeout.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "git_commit",
        "description": "Commit all current changes to the local Git repository with a descriptive message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message describing the changes"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "docker_preview",
        "description": """Build and deploy a Docker preview of the project.

This will:
1. Build a Docker image from the project (uses cache for speed)
2. Start a container with the preview
3. Return the preview URL accessible via Traefik routing

Use after making changes to see the live preview.
Tip: Use rebuild=False after the first build for faster iterations.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "rebuild": {
                    "type": "boolean",
                    "description": "Force full rebuild without cache. Use False for faster builds after first deploy.",
                    "default": False
                }
            },
            "required": []
        }
    },
    {
        "name": "initial_deploy",
        "description": """Run initial setup and deployment for a new project.
        
This runs:
1. npm install (generates package-lock.json)
2. Initial Docker build and deploy

CRITICAL: Run this IMMEDIATELY after creating a new project or pushing a starter template, BEFORE making any code changes.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def read_file(path: str, context: AgentContext, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
    """Read file contents with line numbers and optional pagination."""
    full_path = os.path.join(context.project_folder, path)
    
    try:
        with open(full_path, 'r') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Apply offset and limit
        start = 0
        end = len(lines)

        if offset is not None:
            start = max(0, offset - 1)
        if limit is not None:
            end = min(start + limit, len(lines))
        elif total_lines > MAX_FILE_LINES and offset is None:
            end = MAX_FILE_LINES

        selected_lines = lines[start:end]

        # Add line numbers and truncate long lines
        numbered = []
        for i, line in enumerate(selected_lines, start=start + 1):
            line = line.rstrip('\n')
            if len(line) > MAX_LINE_LENGTH:
                line = line[:MAX_LINE_LENGTH] + "..."
            numbered.append(f"{i:4} | {line}")

        result = '\n'.join(numbered)

        # Add truncation notice
        if end < total_lines:
            result += f"\n\n[Showing lines {start + 1}-{end} of {total_lines} total]"
            result += f"\nUse read_file with offset={end + 1} to see more."

        return result

    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except UnicodeDecodeError:
        return f"Error: Cannot read binary file: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str, context: AgentContext) -> str:
    """Write content to a file."""
    full_path = os.path.join(context.project_folder, path)
    
    try:
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        lines = content.count('\n') + 1
        return f"Successfully wrote {len(content)} bytes ({lines} lines) to {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def edit_file(path: str, old_string: str, new_string: str, context: AgentContext) -> str:
    """Edit a file by replacing old_string with new_string."""
    full_path = os.path.join(context.project_folder, path)
    
    try:
        with open(full_path, 'r') as f:
            content = f.read()

        if old_string not in content:
            return f"Error: Could not find the specified text in {path}. Make sure old_string matches exactly."

        count = content.count(old_string)
        if count > 1:
            return f"Error: Found {count} occurrences. Please provide a more specific old_string."

        new_content = content.replace(old_string, new_string, 1)

        with open(full_path, 'w') as f:
            f.write(new_content)

        old_lines = old_string.count('\n') + 1
        new_lines = new_string.count('\n') + 1
        return f"Successfully edited {path}: replaced {old_lines} line(s) with {new_lines} line(s)"

    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error editing file: {e}"


def list_files(context: AgentContext, path: str = ".", recursive: bool = False, pattern: Optional[str] = None) -> str:
    """List files in a directory with optional recursion and filtering."""
    full_path = os.path.join(context.project_folder, path)
    
    try:
        p = Path(full_path)
        entries = []

        if recursive:
            for entry in sorted(p.rglob("*")):
                if entry.is_file():
                    rel_path = entry.relative_to(p)
                    parts = rel_path.parts
                    # Skip hidden and common ignored directories
                    if any(part.startswith('.') for part in parts):
                        continue
                    if any(part in ['node_modules', '__pycache__', 'venv', '.git', 'build', '.dart_tool'] for part in parts):
                        continue
                    if pattern and not fnmatch.fnmatch(entry.name, pattern):
                        continue
                    entries.append(str(rel_path))
        else:
            for entry in sorted(p.iterdir()):
                if entry.name.startswith('.'):
                    continue
                if pattern and not fnmatch.fnmatch(entry.name, pattern):
                    continue
                if entry.is_dir():
                    entries.append(f"{entry.name}/")
                else:
                    entries.append(entry.name)

        if not entries:
            return f"No files found in {path}" + (f" matching '{pattern}'" if pattern else "")

        if len(entries) > 100:
            entries = entries[:100]
            entries.append(f"... and more files (limited to 100)")

        return '\n'.join(entries)

    except FileNotFoundError:
        return f"Error: Directory not found: {path}"
    except NotADirectoryError:
        return f"Error: Not a directory: {path}"
    except Exception as e:
        return f"Error listing directory: {e}"


def search_files(pattern: str, context: AgentContext, path: str = ".", file_pattern: Optional[str] = None) -> str:
    """Search for a text pattern across files."""
    full_path = os.path.join(context.project_folder, path)
    
    try:
        p = Path(full_path)
        results = []
        files_searched = 0
        max_results = 50

        for file_path in p.rglob("*"):
            if not file_path.is_file():
                continue

            rel_path = file_path.relative_to(p)
            parts = rel_path.parts
            if any(part.startswith('.') for part in parts):
                continue
            if any(part in ['node_modules', '__pycache__', 'venv', '.git', 'build', '.dart_tool'] for part in parts):
                continue

            if file_pattern and not fnmatch.fnmatch(file_path.name, file_pattern):
                continue

            try:
                with open(file_path, 'r') as f:
                    files_searched += 1
                    for i, line in enumerate(f, 1):
                        if pattern.lower() in line.lower():
                            display_line = line.rstrip()
                            if len(display_line) > 200:
                                display_line = display_line[:200] + "..."
                            results.append(f"{rel_path}:{i}: {display_line}")
                            if len(results) >= max_results:
                                results.append(f"\n... (stopped at {max_results} results)")
                                return '\n'.join(results)
            except (UnicodeDecodeError, PermissionError):
                continue

        if not results:
            return f"No matches found for '{pattern}' in {files_searched} files"

        return '\n'.join(results)

    except Exception as e:
        return f"Error searching: {e}"


def run_python(code: str) -> str:
    """Execute Python code in the sandbox."""
    success, output = execute_code(code)
    if success:
        return f"Execution successful:\n{output}"
    else:
        return f"Execution failed:\n{output}"


def run_bash(command: str, context: AgentContext) -> str:
    """Execute a bash command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=context.project_folder
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n--- stderr ---\n"
            output += result.stderr

        max_length = 10000
        if len(output) > max_length:
            output = output[:max_length] + "\n... (output truncated)"

        if result.returncode == 0:
            return output if output else "(command completed with no output)"
        else:
            return f"Command failed (exit code {result.returncode}):\n{output}"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds"
    except Exception as e:
        return f"Error executing command: {e}"


def git_commit(message: str, context: AgentContext) -> str:
    """Commit all changes to the local Git repository."""
    try:
        git_service = context.git_service
        
        # Stage all changes
        git_service.repo.git.add(A=True)
        
        # Create commit
        commit = git_service.commit(message=message, all_changes=True)
        
        return f"Successfully committed: {commit.short_sha} - {message}"
    except Exception as e:
        return f"Error committing changes: {e}"


async def initial_deploy(context: AgentContext) -> str:
    """Run initial Docker deployment for a new project.
    
    Docker handles all dependencies via `npm ci` inside the container.
    This ensures dependencies are only installed once (in Docker) and
    takes advantage of BuildKit cache mounts for fast rebuilds.
    
    Returns:
        Result message with deployment status
    """
    from app.utils.logging import get_logger
    logger = get_logger(__name__)
    
    # NOTE: We do NOT run npm install on the host!
    # Docker's `npm ci` handles dependencies inside the container.
    # This prevents double dependency installation and enables caching.
    
    # Build and deploy Docker container (no nocache - let caching work)
    deploy_result = await docker_preview(context, rebuild=False)
    
    return deploy_result


async def docker_preview(context: AgentContext, rebuild: bool = False) -> str:
    """Build and deploy a Docker preview of the project.
    
    Uses smart cache invalidation for faster builds:
    - Skips build entirely if no changes detected
    - Uses Docker layer caching for incremental rebuilds
    - Only uses nocache=True when force rebuild requested
    """
    try:
        docker_service = context.docker_service
        
        # Generate image and container names
        image_tag = f"codi/{context.project_slug}:latest"
        container_name = f"codi-preview-{context.project_slug}"
        
        # Smart cache check - skip build if nothing changed
        if not rebuild:
            should_skip, reason = docker_service.should_skip_build(
                context.project_folder, image_tag
            )
            if should_skip:
                # Check if container already exists and is running
                existing = await docker_service.get_container(container_name)
                if existing and existing.is_running:
                    domain = os.getenv("CODI_DOMAIN", "codi.local")
                    preview_url = f"http://{context.project_slug}.{domain}"
                    return f"""Build skipped: {reason}

Container is already running.
Preview URL: {preview_url}"""
        
        # Build the image (nocache only for explicit force rebuild)
        build_result = await docker_service.build_image(
            project_path=context.project_folder,
            image_tag=image_tag,
            framework=context.framework or "auto",
            nocache=rebuild,  # Only nocache when explicitly requested
        )
        
        if not build_result.success:
            return f"Build failed:\n{build_result.error}\n\nBuild logs:\n" + "\n".join(build_result.build_logs[-20:])
        
        # Check if container already exists
        existing = await docker_service.get_container(container_name)
        if existing:
            await docker_service.remove_container(container_name, force=True)
        
        # Determine framework and port
        framework = context.framework or docker_service.detect_framework(context.project_folder)
        target_port = 3000 if framework == "nextjs" else 80
        
        # Create Traefik labels for subdomain routing
        domain = os.getenv("CODI_DOMAIN", "codi.local")
        labels = {
            "traefik.enable": "true",
            f"traefik.http.routers.{container_name}.rule": f"Host(`{context.project_slug}.{domain}`)",
            f"traefik.http.routers.{container_name}.entrypoints": "web",
            f"traefik.http.services.{container_name}.loadbalancer.server.port": str(target_port),
            "codi.project_id": str(context.project_id),
            "codi.project_slug": context.project_slug,
        }
        
        # Create and start container
        container_info = await docker_service.create_container(
            image=image_tag,
            name=container_name,
            labels=labels,
            auto_start=True,
        )
        
        # Wait for application to be ready
        is_healthy = await docker_service.wait_for_container_healthy(container_name)
        if not is_healthy:
            # Re-fetch container info to get latest status
            container_info = await docker_service.get_container(container_name)
            status = container_info.status.value if container_info else "unknown"
            return f"""Preview container started but health check failed.
            
Status: {status}
The application might still be starting or there might be an issue with the build.
Please check the logs or wait a moment before trying again."""
        
        preview_url = f"http://{context.project_slug}.{domain}"
        
        # Broadcast deployment success for frontend refresh
        from app.api.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project(
            context.project_id,
            {
                "type": "deployment_complete",
                "preview_url": preview_url,
                "project_slug": context.project_slug,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        # Update project in database with deployment URL
        from app.core.database import get_db_context
        from app.models.project import Project
        from sqlalchemy import update
        
        async with get_db_context() as session:
            await session.execute(
                update(Project)
                .where(Project.id == context.project_id)
                .values(
                    deployment_url=preview_url,
                    last_build_status="success",
                    updated_at=datetime.utcnow()
                )
            )
            await session.commit()
            
        return f"""Preview deployed successfully!

Container: {container_info.short_id}
Status: {container_info.status.value}
Preview URL: {preview_url}

Build logs (last 10 lines):
""" + "\n".join(build_result.build_logs[-10:])
        
    except Exception as e:
        return f"Error deploying preview: {e}"


# =============================================================================
# TOOL ROUTER
# =============================================================================

async def execute_tool(tool_name: str, tool_input: Dict[str, Any], context: AgentContext) -> str:
    """Route tool calls to their implementations.
    
    Args:
        tool_name: Name of the tool to execute
        tool_input: Tool arguments
        context: Agent context with project info
        
    Returns:
        Tool result as string
    """
    try:
        if tool_name == "read_file":
            return read_file(
                tool_input["path"],
                context,
                tool_input.get("offset"),
                tool_input.get("limit")
            )
        elif tool_name == "write_file":
            return write_file(tool_input["path"], tool_input["content"], context)
        elif tool_name == "edit_file":
            return edit_file(
                tool_input["path"],
                tool_input["old_string"],
                tool_input["new_string"],
                context
            )
        elif tool_name == "list_files":
            return list_files(
                context,
                tool_input.get("path", "."),
                tool_input.get("recursive", False),
                tool_input.get("pattern")
            )
        elif tool_name == "search_files":
            return search_files(
                tool_input["pattern"],
                context,
                tool_input.get("path", "."),
                tool_input.get("file_pattern")
            )
        elif tool_name == "run_python":
            return run_python(tool_input["code"])
        elif tool_name == "run_bash":
            return run_bash(tool_input["command"], context)
        elif tool_name == "git_commit":
            return git_commit(tool_input["message"], context)
        elif tool_name == "docker_preview":
            return await docker_preview(context, tool_input.get("rebuild", False))
        elif tool_name == "initial_deploy":
            return await initial_deploy(context)
        else:
            return f"Error: Unknown tool: {tool_name}"
    except Exception as e:
        return f"Error executing {tool_name}: {e}"
