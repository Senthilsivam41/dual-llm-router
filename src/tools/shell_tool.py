import subprocess
import os
from typing import Dict, Any

def run_shell(command: str, workspace_root: str = ".", timeout_seconds: int = 30) -> Dict[str, Any]:
    """Executes sandboxed shell command inside workspace root."""
    abs_root = os.path.abspath(workspace_root)
    try:
        res = subprocess.run(
            command,
            shell=True,
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
    except Exception as e:
        return {"success": False, "error": str(e)}
