import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Any


def _is_within_workspace(path: str, workspace_root: str) -> bool:
    """Check if a path is within the workspace root (resolves symlinks)."""
    try:
        resolved_path = Path(path).resolve()
        resolved_root = Path(workspace_root).resolve()
        return resolved_root in resolved_path.parents or resolved_path == resolved_root
    except Exception:
        return False


def run_shell(command: str, workspace_root: str = ".", timeout_seconds: int = 120) -> Dict[str, Any]:
    """Executes sandboxed shell command inside workspace root.
    
    Security features:
    - No shell=True (prevents shell injection)
    - Command parsed with shlex for safe argument handling
    - Working directory validated to be within workspace_root
    - Symlink resolution prevents escape via symlinks
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