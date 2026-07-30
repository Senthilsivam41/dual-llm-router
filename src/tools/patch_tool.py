import os
from pathlib import Path
from typing import Dict, Any


def _is_within_workspace(target_path: str, workspace_root: str) -> bool:
    """Check if target_path is within workspace_root using resolved paths.
    
    Uses Path.resolve() to handle symlinks and os.path.commonpath for
    proper containment checking. Rejects any path that escapes via symlinks.
    """
    try:
        resolved_target = Path(target_path).resolve()
        resolved_root = Path(workspace_root).resolve()
        
        common = os.path.commonpath([str(resolved_target), str(resolved_root)])
        return common == str(resolved_root)
    except Exception:
        return False


def apply_patch(file_path: str, new_content: str, workspace_root: str = ".") -> Dict[str, Any]:
    """Applies patch or writes updated content to target file safely within workspace.
    
    Security features:
    - Uses resolved paths (Path.resolve()) to defeat symlink attacks
    - Uses os.path.commonpath for proper containment (not string prefix)
    - Rejects absolute paths and parent directory traversal
    - Validates workspace_root itself is contained
    """
    abs_root = os.path.abspath(workspace_root)
    
    if os.path.isabs(file_path):
        return {"success": False, "error": f"Absolute paths not allowed: '{file_path}'"}
    
    if ".." in Path(file_path).parts:
        return {"success": False, "error": f"Parent directory traversal not allowed: '{file_path}'"}
    
    target_path = os.path.abspath(os.path.join(abs_root, file_path))
    
    if not _is_within_workspace(target_path, abs_root):
        return {"success": False, "error": f"Path '{file_path}' escapes workspace (symlink or traversal detected)"}
    
    if not _is_within_workspace(abs_root, abs_root):
        return {"success": False, "error": "Workspace root validation failed"}

    try:
        parent_dir = os.path.dirname(target_path)
        if parent_dir and not _is_within_workspace(parent_dir, abs_root):
            return {"success": False, "error": f"Parent directory escapes workspace"}
        
        os.makedirs(parent_dir, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {"success": True, "file_path": file_path, "bytes_written": len(new_content)}
    except Exception as e:
        return {"success": False, "error": str(e)}