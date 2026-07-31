import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


_PATH_COMMANDS = {"cat", "ls", "mkdir", "touch"}
_ARGUMENT_FREE_COMMANDS = {"pwd"}
_TEXT_COMMANDS = {"echo"}
_ALLOWED_COMMANDS = _PATH_COMMANDS | _ARGUMENT_FREE_COMMANDS | _TEXT_COMMANDS


def _is_within_workspace(path: str, workspace_root: str) -> bool:
    """Check if a path is within the workspace root (resolves symlinks)."""
    try:
        resolved_path = Path(path).resolve()
        resolved_root = Path(workspace_root).resolve()
        return resolved_root in resolved_path.parents or resolved_path == resolved_root
    except Exception:
        return False


def _validate_command_paths(args: list[str], workspace_root: str) -> Optional[str]:
    """Return an error when a command argument can address outside the workspace."""
    command = args[0]
    command_args = args[1:]

    if command in _ARGUMENT_FREE_COMMANDS and command_args:
        return f"Command '{command}' does not accept arguments"

    if command not in _PATH_COMMANDS:
        return None

    for argument in command_args:
        if argument == "--":
            continue
        if argument.startswith("-"):
            if "/" in argument or ".." in argument:
                return f"Unsafe option rejected: '{argument}'"
            continue

        candidate = Path(workspace_root, argument)
        if Path(argument).is_absolute() or not _is_within_workspace(
            str(candidate), workspace_root
        ):
            return f"Path argument escapes workspace: '{argument}'"

    return None


def run_shell(command: str, workspace_root: str = ".", timeout_seconds: int = 120) -> Dict[str, Any]:
    """Execute a capability-limited command inside workspace root.
    
    Security features:
    - No shell=True (prevents shell injection)
    - Only a small allowlist of non-interpreter commands is available
    - Filesystem arguments must resolve within workspace_root
    """
    abs_root = os.path.abspath(workspace_root)
    
    if not _is_within_workspace(abs_root, workspace_root):
        return {
            "success": False,
            "error": f"Workspace root {workspace_root} is not within allowed workspace",
        }

    try:
        args = shlex.split(command)
        if not args:
            return {"success": False, "error": "Empty command"}

        executable = args[0]
        if executable not in _ALLOWED_COMMANDS:
            return {
                "success": False,
                "error": f"Command not allowed: '{executable}'",
            }

        path_error = _validate_command_paths(args, abs_root)
        if path_error:
            return {"success": False, "error": path_error}
        
        res = subprocess.run(
            args,
            shell=False,
            cwd=abs_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "success": res.returncode == 0,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout_seconds}s"}
    except FileNotFoundError:
        return {"success": False, "error": f"Command not found: {args[0]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
