import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent.tool_tracing import track_tool

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
    session_id: Optional[str] = None
    backend_type: Optional[str] = None
    backend_config: Optional[Dict[str, Any]] = None
    
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
    {
        "name": "env_list",
        "description": """List all environment variables for the project.
        
Shows all environment variables with their keys, values (decrypted), contexts, and descriptions.
Useful to understand what configuration is available.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Optional: filter by context (docker-compose, server-config, flutter-build, general)"
                }
            },
            "required": []
        }
    },
    {
        "name": "env_get",
        "description": """Get the value of a specific environment variable.
        
Returns the decrypted value if it's a secret.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Environment variable key (e.g., 'DATABASE_URL', 'API_KEY')"
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "env_set",
        "description": """Set or update an environment variable.
        
Creates a new variable or updates an existing one. Values marked as secrets will be encrypted.
After setting, run env_sync to write changes to the .env file.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Environment variable key (UPPERCASE_WITH_UNDERSCORES)"
                },
                "value": {
                    "type": "string",
                    "description": "Value to set"
                },
                "is_secret": {
                    "type": "boolean",
                    "description": "Whether this value should be encrypted (default: false)",
                    "default": False
                },
                "context": {
                    "type": "string",
                    "description": "Context: docker-compose, server-config, flutter-build, or general (default: general)",
                    "default": "general"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description of what this variable is for"
                }
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "env_delete",
        "description": """Delete an environment variable.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Environment variable key to delete"
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "env_sync",
        "description": """Sync environment variables to the project's .env file.
        
Writes all environment variables (or filtered by context) to the .env file.
Use this after making changes with env_set to persist them to disk.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Optional: only sync variables with this context"
                },
                "include_secrets": {
                    "type": "boolean",
                    "description": "Whether to include secret values (default: true)",
                    "default": True
                }
            },
            "required": []
        }
    },
]

# Serverpod-specific tools - only available when project has backend_type='serverpod'
SERVERPOD_TOOLS = [
    {
        "name": "serverpod_add_model",
        "description": """Create a new Serverpod data model in the protocol directory.

This will:
1. Create a YAML model file in {project}_server/lib/src/protocol/
2. Run 'dart run serverpod generate' to regenerate code
3. The model will be available in both server and client packages

Example fields: [{name: 'id', type: 'int'}, {name: 'title', type: 'String'}, {name: 'createdAt', type: 'DateTime'}]""",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "Name of the model in PascalCase (e.g., 'Todo', 'UserProfile')"
                },
                "fields": {
                    "type": "array",
                    "description": "List of field definitions",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Field name in camelCase"},
                            "type": {"type": "string", "description": "Dart type (String, int, bool, DateTime, etc.)"},
                            "nullable": {"type": "boolean", "description": "Whether field is nullable", "default": False}
                        },
                        "required": ["name", "type"]
                    }
                },
                "table_name": {
                    "type": "string",
                    "description": "Database table name (optional, defaults to lowercase model name)"
                }
            },
            "required": ["model_name", "fields"]
        }
    },
    {
        "name": "serverpod_add_endpoint",
        "description": """Create a new Serverpod API endpoint.

This will:
1. Create a Dart endpoint file in {project}_server/lib/src/endpoints/
2. Run 'dart run serverpod generate' to regenerate code
3. The endpoint will be callable from Flutter via client.{endpoint_name}.{method_name}()

Each method becomes an RPC-callable function from the client.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "endpoint_name": {
                    "type": "string",
                    "description": "Name of the endpoint in camelCase (e.g., 'todo', 'user')"
                },
                "methods": {
                    "type": "array",
                    "description": "List of endpoint methods to create",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Method name in camelCase"},
                            "return_type": {"type": "string", "description": "Return type (String, int, List<Model>, etc.)"},
                            "parameters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string"}
                                    }
                                }
                            },
                            "description": {"type": "string", "description": "Optional docstring for the method"}
                        },
                        "required": ["name", "return_type"]
                    }
                }
            },
            "required": ["endpoint_name", "methods"]
        }
    },
    {
        "name": "serverpod_migrate_database",
        "description": """Create and apply database migrations for Serverpod.

This will:
1. Run 'dart run serverpod create-migration' to create migration files
2. Run 'dart run serverpod migrate' to apply migrations to the database

Use after adding or modifying models with 'table:' directive.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Force migration even if there are warnings",
                    "default": False
                }
            },
            "required": []
        }
    },
    {
        "name": "serverpod_get_logs",
        "description": """Get logs from Serverpod Docker containers.

Fetches recent log output from the specified service container.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service to get logs from: 'serverpod', 'postgres', or 'redis'",
                    "enum": ["serverpod", "postgres", "redis"]
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of log lines to return (default: 100)",
                    "default": 100
                }
            },
            "required": ["service"]
        }
    },
    {
        "name": "serverpod_restart",
        "description": """Restart Serverpod services.

Use after making changes that require a server restart, such as modifying endpoints or regenerating code.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Specific service to restart (optional, restarts serverpod by default)",
                    "enum": ["serverpod", "postgres", "redis", "flutter", "all"]
                }
            },
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


# Track which projects have completed initial deploy to prevent duplicates
_initial_deploy_completed: Dict[int, bool] = {}


async def initial_deploy(context: AgentContext) -> str:
    """Run initial Docker deployment for a new project.
    
    For single-service projects (Next.js, React, Flutter):
    - Uses docker_preview for simple containerization
    
    For multi-service projects (Flutter-Serverpod):
    - Detects docker-compose.yml
    - Uses DockerComposeService for orchestration
    - Waits for all services to be healthy
    
    Returns:
        Result message with deployment status
    """
    from app.utils.logging import get_logger
    from app.services.infrastructure.docker_compose import DockerComposeService
    logger = get_logger(__name__)
    
    # Guard against duplicate initial deploys (InMemory + DB Check)
    if _initial_deploy_completed.get(context.project_id):
        logger.info(f"Initial deploy already completed for project {context.project_id} (cached), skipping")
        return "Initial deployment already completed for this project. Use docker_preview for subsequent builds."

    # Check database for existing deployment
    try:
        from app.core.database import get_db_context
        from app.models.project import Project
        from sqlalchemy import select

        async with get_db_context() as session:
            result = await session.execute(select(Project).where(Project.id == context.project_id))
            project = result.scalar_one_or_none()
            
            if project and (project.last_deployment_at or project.deployment_url):
                _initial_deploy_completed[context.project_id] = True
                logger.info(f"Initial deploy already completed for project {context.project_id} (db check), skipping")
                return "Initial deployment already completed for this project. Use docker_preview for subsequent builds."
    except Exception as e:
        logger.warning(f"Failed to check DB for initial deploy status: {e}")
    
    # Check if project uses docker-compose (multi-service)
    compose_file = DockerComposeService.detect_compose_file(context.project_folder)
    
    if compose_file and context.backend_type == "serverpod":
        logger.info(f"Detected docker-compose project for Serverpod at {compose_file}")
        
        # Ensure environment variables are synced to .env file
        try:
            from app.core.database import get_db_context
            from app.models.environment_variable import EnvironmentVariable
            from app.models.project import Project
            from app.services.domain.environment import EnvironmentService
            from sqlalchemy import select
            
            async with get_db_context() as session:
                # Get project
                result = await session.execute(select(Project).where(Project.id == context.project_id))
                project = result.scalar_one_or_none()
                
                if project:
                    # Get environment variables
                    result = await session.execute(
                        select(EnvironmentVariable).where(EnvironmentVariable.project_id == context.project_id)
                    )
                    env_vars = list(result.scalars().all())
                    
                    if env_vars:
                        # Sync to .env file for docker-compose
                        EnvironmentService.sync_to_file(
                            project=project,
                            variables=env_vars,
                            context=None,
                            include_secrets=True,
                        )
                        logger.info(f"Synced {len(env_vars)} environment variables to .env file")
        except Exception as e:
            logger.warning(f"Failed to sync environment variables: {e}")
        
        # Use docker-compose for multi-service deployment
        success, output = await DockerComposeService.compose_up(
            project_path=context.project_folder,
            detach=True,
            build=True,
        )
        
        if not success:
            return f"Docker Compose deployment failed:\n{output}"
        
        logger.info("Docker Compose up successful, waiting for services to be healthy...")
        
        # Wait for services to be healthy
        all_healthy, health_msg = await DockerComposeService.wait_for_services_healthy(
            project_path=context.project_folder,
            timeout=180,  # 3 minutes
            check_interval=5,
        )
        
        if not all_healthy:
            # Get logs for debugging
            logs = await DockerComposeService.compose_logs(context.project_folder, tail=50)
            return f"Services started but health check failed:\n{health_msg}\n\nRecent logs:\n{logs[-2000:]}"
        
        # Get service statuses
        services = await DockerComposeService.compose_ps(context.project_folder)
        service_summary = "\n".join(f"  ✓ {s.name}: {s.status}" for s in services)
        
        # Mark as completed
        _initial_deploy_completed[context.project_id] = True
        logger.info(f"Initial Docker Compose deploy completed for project {context.project_id}")
        
        # Determine deployment URL (Flutter service)
        domain = os.getenv("CODI_DOMAIN", "codi.local")
        preview_url = f"http://{context.project_slug}.{domain}"
        
        return f"""Initial deployment successful!

All services are healthy:
{service_summary}

Frontend URL: {preview_url}
Serverpod API: http://localhost:8080
Serverpod Insights: http://localhost:8081

Use 'serverpod_get_logs' to view service logs.
Use 'docker_preview' for subsequent deployments after code changes."""
    
    else:
        # Single-service project - use standard docker_preview
        logger.info(f"Using standard docker_preview for single-service project")
        deploy_result = await docker_preview(context, rebuild=False)
        
        # Mark as completed
        _initial_deploy_completed[context.project_id] = True
        logger.info(f"Initial deploy completed for project {context.project_id}")
        
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
        
        # Save deployment and container to database for logs/tracking
        from app.core.database import get_db_context
        from app.models.project import Project
        from app.models.deployment import Deployment, DeploymentStatus
        from app.models.container import Container, ContainerStatus
        from sqlalchemy import update, select
        import uuid
        
        async with get_db_context() as session:
            # Delete existing container record if exists (new container has different ID)
            # Must be done first since Deployment references Container
            existing_container_result = await session.execute(
                select(Container).where(Container.name == container_name)
            )
            existing_container = existing_container_result.scalar_one_or_none()
            
            if existing_container:
                await session.delete(existing_container)
                await session.flush()
            
            # Create new container record (must exist before Deployment due to FK)
            container = Container(
                id=container_info.id,
                project_id=context.project_id,
                name=container_name,
                image=image_tag.split(":")[0],
                image_tag=image_tag.split(":")[-1] if ":" in image_tag else "latest",
                status=ContainerStatus.RUNNING,
                git_branch=context.current_branch,
                port=target_port,
                is_preview=False,
                started_at=datetime.utcnow(),
            )
            session.add(container)
            await session.flush()
            
            # Archive any existing deployment with same subdomain
            existing_deployment_result = await session.execute(
                select(Deployment).where(Deployment.subdomain == context.project_slug)
            )
            existing_deployment = existing_deployment_result.scalar_one_or_none()
            
            if existing_deployment:
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                existing_deployment.subdomain = f"archived-{timestamp}-{existing_deployment.subdomain}"
                existing_deployment.status = DeploymentStatus.INACTIVE
                session.add(existing_deployment)
                await session.flush()
            
            # Create deployment record (references container_id)
            deployment_id = str(uuid.uuid4())
            deployment = Deployment(
                id=deployment_id,
                project_id=context.project_id,
                container_id=container_info.id,
                subdomain=context.project_slug,
                url=preview_url,
                status=DeploymentStatus.ACTIVE,
                framework=framework,
                git_branch=context.current_branch,
                is_preview=False,
                is_production=True,
                deployed_at=datetime.utcnow(),
            )
            session.add(deployment)
            
            # Update project with deployment info
            await session.execute(
                update(Project)
                .where(Project.id == context.project_id)
                .values(
                    deployment_url=preview_url,
                    last_deployment_at=datetime.utcnow(),
                    last_build_status="success",
                    updated_at=datetime.utcnow(),
                )
            )
            
            await session.commit()
        
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
        
        # Broadcast LLM-generated deployment summary
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage
            from app.core.config import settings
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=settings.gemini_api_key,
                temperature=0.7,
            )
            
            summary_prompt = """Generate a brief deployment success message. Mention:
- The preview is ready and live
- Be celebratory but professional
- Under 2 sentences
- No emojis
- No technical details"""
            
            response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
            summary = response.content.strip().strip('"').strip("'") if isinstance(response.content, str) else "Deployment complete! Your preview is ready."
            
            await connection_manager.broadcast_to_project(
                context.project_id,
                {
                    "type": "agent_response",
                    "message": summary,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            # Fallback - still broadcast a message even if LLM fails
            await connection_manager.broadcast_to_project(
                context.project_id,
                {
                    "type": "agent_response", 
                    "message": "Deployment complete! Your preview is now live.",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            
        return f"""Preview deployed successfully!

Container: {container_info.short_id}
Status: {container_info.status.value}
Preview URL: {preview_url}

Build logs (last 10 lines):
""" + "\n".join(build_result.build_logs[-10:])
        
    except Exception as e:
        return f"Error deploying preview: {e}"


# =============================================================================
# SERVERPOD TOOL IMPLEMENTATIONS
# =============================================================================

async def serverpod_add_model(
    model_name: str,
    fields: List[Dict[str, Any]],
    context: AgentContext,
    table_name: Optional[str] = None,
) -> str:
    """Create a new Serverpod data model in the protocol directory."""
    try:
        # Determine project name from folder structure
        project_folder = Path(context.project_folder)
        
        # Find the server package directory
        server_dirs = list(project_folder.glob("*_server"))
        if not server_dirs:
            return "Error: Could not find Serverpod server package. Expected *_server directory."
        
        server_dir = server_dirs[0]
        protocol_dir = server_dir / "lib" / "src" / "protocol"
        protocol_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate YAML content
        yaml_lines = [f"class: {model_name}"]
        
        if table_name:
            yaml_lines.append(f"table: {table_name}")
        else:
            yaml_lines.append(f"table: {model_name.lower()}")
        
        yaml_lines.append("fields:")
        
        for field in fields:
            field_name = field.get("name")
            field_type = field.get("type")
            nullable = field.get("nullable", False)
            
            if nullable:
                yaml_lines.append(f"  {field_name}: {field_type}?")
            else:
                yaml_lines.append(f"  {field_name}: {field_type}")
        
        yaml_content = "\n".join(yaml_lines) + "\n"
        
        # Write the model file
        model_file = protocol_dir / f"{model_name.lower()}.yaml"
        model_file.write_text(yaml_content, encoding="utf-8")
        
        # Run serverpod generate
        result = subprocess.run(
            ["dart", "run", "serverpod", "generate"],
            cwd=str(server_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            return f"Model created but generation failed:\n{result.stderr}\n\nModel file: {model_file}"
        
        return f"""Successfully created model '{model_name}'!

File: {model_file.relative_to(project_folder)}
Table: {table_name or model_name.lower()}
Fields: {', '.join(f['name'] for f in fields)}

Code regeneration complete. The model is now available in both server and client packages."""
        
    except Exception as e:
        return f"Error creating model: {e}"


async def serverpod_add_endpoint(
    endpoint_name: str,
    methods: List[Dict[str, Any]],
    context: AgentContext,
) -> str:
    """Create a new Serverpod API endpoint."""
    try:
        project_folder = Path(context.project_folder)
        
        # Find the server package directory
        server_dirs = list(project_folder.glob("*_server"))
        if not server_dirs:
            return "Error: Could not find Serverpod server package."
        
        server_dir = server_dirs[0]
        endpoints_dir = server_dir / "lib" / "src" / "endpoints"
        endpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Dart endpoint code
        class_name = endpoint_name[0].upper() + endpoint_name[1:] + "Endpoint"
        
        code_lines = [
            "import 'package:serverpod/serverpod.dart';",
            "",
            f"/// {endpoint_name.title()} endpoint for API operations.",
            f"class {class_name} extends Endpoint {{",
        ]
        
        for method in methods:
            method_name = method.get("name")
            return_type = method.get("return_type", "String")
            params = method.get("parameters", [])
            description = method.get("description", f"{method_name} operation")
            
            # Build parameter string
            param_parts = ["Session session"]
            for p in params:
                param_parts.append(f"{p.get('type', 'String')} {p.get('name')}")
            param_str = ", ".join(param_parts)
            
            code_lines.extend([
                "",
                f"  /// {description}",
                f"  Future<{return_type}> {method_name}({param_str}) async {{",
                f"    // TODO: Implement {method_name}",
                f"    throw UnimplementedError('Method {method_name} not implemented');",
                "  }",
            ])
        
        code_lines.append("}")
        code_lines.append("")
        
        code_content = "\n".join(code_lines)
        
        # Write the endpoint file
        endpoint_file = endpoints_dir / f"{endpoint_name}_endpoint.dart"
        endpoint_file.write_text(code_content, encoding="utf-8")
        
        # Run serverpod generate
        result = subprocess.run(
            ["dart", "run", "serverpod", "generate"],
            cwd=str(server_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            return f"Endpoint created but generation failed:\n{result.stderr}\n\nEndpoint file: {endpoint_file}"
        
        method_names = [m['name'] for m in methods]
        return f"""Successfully created endpoint '{endpoint_name}'!

File: {endpoint_file.relative_to(project_folder)}
Class: {class_name}
Methods: {', '.join(method_names)}

Usage from Flutter: client.{endpoint_name}.{method_names[0]}()

Code regeneration complete."""
        
    except Exception as e:
        return f"Error creating endpoint: {e}"


async def serverpod_migrate_database(context: AgentContext, force: bool = False) -> str:
    """Create and apply database migrations."""
    try:
        project_folder = Path(context.project_folder)
        
        # Find the server package directory
        server_dirs = list(project_folder.glob("*_server"))
        if not server_dirs:
            return "Error: Could not find Serverpod server package."
        
        server_dir = server_dirs[0]
        
        # Create migration
        create_result = subprocess.run(
            ["dart", "run", "serverpod", "create-migration"],
            cwd=str(server_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if create_result.returncode != 0 and not force:
            return f"Migration creation failed:\n{create_result.stderr}"
        
        # Apply migration
        migrate_cmd = ["dart", "run", "serverpod", "migrate"]
        if force:
            migrate_cmd.append("--force")
            
        migrate_result = subprocess.run(
            migrate_cmd,
            cwd=str(server_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if migrate_result.returncode != 0:
            return f"Migration application failed:\n{migrate_result.stderr}"
        
        return f"""Database migration completed successfully!

Create output: {create_result.stdout or 'No output'}
Migrate output: {migrate_result.stdout or 'No output'}"""
        
    except Exception as e:
        return f"Error running migration: {e}"


async def serverpod_get_logs(
    service: str,
    context: AgentContext,
    tail: int = 100,
) -> str:
    """Get logs from Serverpod Docker containers."""
    try:
        project_slug = context.project_slug or "project"
        
        # Map service to container name
        container_map = {
            "serverpod": f"{project_slug}_serverpod",
            "postgres": f"{project_slug}_postgres",
            "redis": f"{project_slug}_redis",
        }
        
        container_name = container_map.get(service)
        if not container_name:
            return f"Error: Unknown service '{service}'. Use: serverpod, postgres, or redis"
        
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            return f"Error getting logs: {result.stderr}"
        
        logs = result.stdout + result.stderr
        return f"Logs from {service} (last {tail} lines):\n\n{logs}"
        
    except Exception as e:
        return f"Error getting logs: {e}"


async def serverpod_restart(context: AgentContext, service: str = "serverpod") -> str:
    """Restart Serverpod services."""
    try:
        project_slug = context.project_slug or "project"
        project_folder = Path(context.project_folder)
        
        if service == "all":
            # Restart all services using docker-compose
            result = subprocess.run(
                ["docker-compose", "restart"],
                cwd=str(project_folder),
                capture_output=True,
                text=True,
                timeout=120,
            )
        else:
            # Map service to container name
            container_map = {
                "serverpod": f"{project_slug}_serverpod",
                "postgres": f"{project_slug}_postgres",
                "redis": f"{project_slug}_redis",
                "flutter": f"{project_slug}_flutter",
            }
            
            container_name = container_map.get(service)
            if not container_name:
                return f"Error: Unknown service '{service}'"
            
            result = subprocess.run(
                ["docker", "restart", container_name],
                capture_output=True,
                text=True,
                timeout=60,
            )
        
        if result.returncode != 0:
            return f"Error restarting {service}: {result.stderr}"
        
        return f"Successfully restarted {service}!\n\n{result.stdout}"
        
    except Exception as e:
        return f"Error restarting service: {e}"


# =============================================================================
# TOOL ROUTER
# =============================================================================


# =============================================================================
# ENVIRONMENT MANAGEMENT TOOLS
# =============================================================================

async def env_list(context: AgentContext, filter_context: Optional[str] = None) -> str:
    """List all environment variables for the project."""
    try:
        from app.core.database import get_db_context
        from app.models.environment_variable import EnvironmentVariable
        from sqlalchemy import select
        
        async with get_db_context() as session:
            query = select(EnvironmentVariable).where(
                EnvironmentVariable.project_id == context.project_id
            )
            
            if filter_context:
                query = query.where(EnvironmentVariable.context == filter_context)
            
            query = query.order_by(EnvironmentVariable.context, EnvironmentVariable.key)
            
            result = await session.execute(query)
            variables = result.scalars().all()
            
            if not variables:
                return "No environment variables found for this project."
            
            # Format output
            lines = ["Environment Variables:", ""]
            current_context = None
            
            for var in variables:
                if var.context != current_context:
                    current_context = var.context
                    lines.append(f"## {current_context.upper()} ##")
                
                value_display = var.get_value()
                if var.is_secret:
                    value_display = "***" + value_display[-4:] if len(value_display) > 4 else "***"
                
                line = f"{var.key}={value_display}"
                if var.description:
                    line += f" # {var.description}"
                lines.append(line)
                lines.append("")
            
            return "\n".join(lines)
            
    except Exception as e:
        return f"Error listing environment variables: {e}"


async def env_get(context: AgentContext, key: str) -> str:
    """Get the value of a specific environment variable."""
    try:
        from app.core.database import get_db_context
        from app.models.environment_variable import EnvironmentVariable
        from sqlalchemy import select
        
        async with get_db_context() as session:
            result = await session.execute(
                select(EnvironmentVariable).where(
                    EnvironmentVariable.project_id == context.project_id,
                    EnvironmentVariable.key == key,
                )
            )
            var = result.scalar_one_or_none()
            
            if not var:
                return f"Environment variable '{key}' not found."
            
            value = var.get_value()
            info = f"{key}={value}"
            if var.description:
                info += f"\n\nDescription: {var.description}"
            info += f"\nContext: {var.context}"
            info += f"\nSecret: {'Yes' if var.is_secret else 'No'}"
            
            return info
            
    except Exception as e:
        return f"Error getting environment variable: {e}"


async def env_set(
    context: AgentContext,
    key: str,
    value: str,
    is_secret: bool = False,
    var_context: str = "general",
    description: Optional[str] = None,
) -> str:
    """Set or update an environment variable."""
    try:
        from app.core.database import get_db_context
        from app.models.environment_variable import EnvironmentVariable
        from sqlalchemy import select
        
        # Validate key format
        if not all(c.isupper() or c.isdigit() or c == "_" for c in key):
            return f"Error: Key must be UPPERCASE_WITH_UNDERSCORES format"
        
        if key[0].isdigit():
            return f"Error: Key cannot start with a number"
        
        # Validate context
        valid_contexts = {"docker-compose", "server-config", "flutter-build", "general"}
        if var_context not in valid_contexts:
            return f"Error: Context must be one of: {', '.join(valid_contexts)}"
        
        async with get_db_context() as session:
            # Check if variable already exists
            result = await session.execute(
                select(EnvironmentVariable).where(
                    EnvironmentVariable.project_id == context.project_id,
                    EnvironmentVariable.key == key,
                )
            )
            existing_var = result.scalar_one_or_none()
            
            if existing_var:
                # Update existing variable
                existing_var.set_value(value, is_secret=is_secret)
                existing_var.context = var_context
                if description:
                    existing_var.description = description
                action = "Updated"
            else:
                # Create new variable
                new_var = EnvironmentVariable(
                    project_id=context.project_id,
                    key=key,
                    context=var_context,
                    description=description,
                )
                new_var.set_value(value, is_secret=is_secret)
                session.add(new_var)
                action = "Created"
            
            await session.commit()
            
            return f"{action} environment variable '{key}' in context '{var_context}'.\n\nRemember to run env_sync to write changes to .env file."
            
    except Exception as e:
        return f"Error setting environment variable: {e}"


async def env_delete(context: AgentContext, key: str) -> str:
    """Delete an environment variable."""
    try:
        from app.core.database import get_db_context
        from app.models.environment_variable import EnvironmentVariable
        from sqlalchemy import select
        
        async with get_db_context() as session:
            result = await session.execute(
                select(EnvironmentVariable).where(
                    EnvironmentVariable.project_id == context.project_id,
                    EnvironmentVariable.key == key,
                )
            )
            var = result.scalar_one_or_none()
            
            if not var:
                return f"Environment variable '{key}' not found."
            
            await session.delete(var)
            await session.commit()
            
            return f"Deleted environment variable '{key}'.\n\nRemember to run env_sync to update .env file."
            
    except Exception as e:
        return f"Error deleting environment variable: {e}"


async def env_sync(
    context: AgentContext,
    filter_context: Optional[str] = None,
    include_secrets: bool = True,
) -> str:
    """Sync environment variables to the project's .env file."""
    try:
        from app.core.database import get_db_context
        from app.models.environment_variable import EnvironmentVariable
        from app.models.project import Project
        from app.services.domain.environment import EnvironmentService
        from sqlalchemy import select
        
        async with get_db_context() as session:
            # Get project
            result = await session.execute(
                select(Project).where(Project.id == context.project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                return "Error: Project not found"
            
            # Get environment variables
            query = select(EnvironmentVariable).where(
                EnvironmentVariable.project_id == context.project_id
            )
            
            if filter_context:
                query = query.where(EnvironmentVariable.context == filter_context)
            
            result = await session.execute(query)
            variables = list(result.scalars().all())
            
            if not variables:
                return "No environment variables to sync."
            
            # Sync to file
            file_path = EnvironmentService.sync_to_file(
                project=project,
                variables=variables,
                context=filter_context,
                include_secrets=include_secrets,
            )
            
            context_msg = f" with context '{filter_context}'" if filter_context else ""
            return f"Successfully synced {len(variables)} environment variable(s){context_msg} to:\n{file_path}"
            
    except Exception as e:
        return f"Error syncing environment variables: {e}"


# =============================================================================
# TOOL EXECUTION DISPATCHER
# =============================================================================

async def execute_tool(
    tool_name: str, 
    tool_input: Dict[str, Any], 
    context: AgentContext,
    user_prompt: Optional[str] = None
) -> str:
    """Route tool calls to their implementations with automatic Opik tracing.
    
    Args:
        tool_name: Name of the tool to execute
        tool_input: Tool arguments
        context: Agent context with project info
        user_prompt: Original user prompt that triggered this tool (for session grouping)
        
    Returns:
        Tool result as string
    """
    # Create a traced wrapper for the tool execution
    @track_tool(tool_name)
    async def _execute_tool_traced(**kwargs):
        """Wrapped tool execution with tracing."""
        _tool_name = kwargs.pop('_tool_name')
        _tool_input = kwargs.pop('_tool_input')
        _context = kwargs.pop('context')
        
        if _tool_name == "read_file":
            return read_file(
                _tool_input["path"],
                _context,
                _tool_input.get("offset"),
                _tool_input.get("limit")
            )
        elif _tool_name == "write_file":
            return write_file(_tool_input["path"], _tool_input["content"], _context)
        elif _tool_name == "edit_file":
            return edit_file(
                _tool_input["path"],
                _tool_input["old_string"],
                _tool_input["new_string"],
                _context
            )
        elif _tool_name == "list_files":
            return list_files(
                _context,
                _tool_input.get("path", "."),
                _tool_input.get("recursive", False),
                _tool_input.get("pattern")
            )
        elif _tool_name == "search_files":
            return search_files(
                _tool_input["pattern"],
                _context,
                _tool_input.get("path", "."),
                _tool_input.get("file_pattern")
            )
        elif _tool_name == "run_python":
            return run_python(_tool_input["code"])
        elif _tool_name == "run_bash":
            return run_bash(_tool_input["command"], _context)
        elif _tool_name == "git_commit":
            return git_commit(_tool_input["message"], _context)
        elif _tool_name == "docker_preview":
            return await docker_preview(_context, _tool_input.get("rebuild", False))
        elif _tool_name == "initial_deploy":
            return await initial_deploy(_context)
        # Serverpod tools
        elif _tool_name == "serverpod_add_model":
            return await serverpod_add_model(
                _tool_input["model_name"],
                _tool_input["fields"],
                _context,
                _tool_input.get("table_name"),
            )
        elif _tool_name == "serverpod_add_endpoint":
            return await serverpod_add_endpoint(
                _tool_input["endpoint_name"],
                _tool_input["methods"],
                _context,
            )
        elif _tool_name == "serverpod_migrate_database":
            return await serverpod_migrate_database(
                _context,
                _tool_input.get("force", False),
            )
        elif _tool_name == "serverpod_get_logs":
            return await serverpod_get_logs(
                _tool_input["service"],
                _context,
                _tool_input.get("tail", 100),
            )
        elif _tool_name == "serverpod_restart":
            return await serverpod_restart(
                _context,
                _tool_input.get("service", "serverpod"),
            )
        # Environment management tools
        elif _tool_name == "env_list":
            return await env_list(_context, _tool_input.get("context"))
        elif _tool_name == "env_get":
            return await env_get(_context, _tool_input["key"])
        elif _tool_name == "env_set":
            return await env_set(
                _context,
                _tool_input["key"],
                _tool_input["value"],
                _tool_input.get("is_secret", False),
                _tool_input.get("context", "general"),
                _tool_input.get("description"),
            )
        elif _tool_name == "env_delete":
            return await env_delete(_context, _tool_input["key"])
        elif _tool_name == "env_sync":
            return await env_sync(
                _context,
                _tool_input.get("context"),
                _tool_input.get("include_secrets", True),
            )
        else:
            return f"Error: Unknown tool: {_tool_name}"
    
    # Execute the traced tool
    try:
        return await _execute_tool_traced(
            _tool_name=tool_name,
            _tool_input=tool_input,
            context=context,
            user_prompt=user_prompt,
        )
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


