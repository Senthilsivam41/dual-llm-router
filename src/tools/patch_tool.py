import os
from typing import Dict, Any

def apply_patch(file_path: str, new_content: str, workspace_root: str = ".") -> Dict[str, Any]:
    """Applies patch or writes updated content to target file safely within workspace."""
    abs_root = os.path.abspath(workspace_root)
    target_path = os.path.abspath(os.path.join(abs_root, file_path))
    
    if not target_path.startswith(abs_root):
        return {"success": False, "error": f"Path '{file_path}' outside workspace root"}
    
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {"success": True, "file_path": file_path, "bytes_written": len(new_content)}
    except Exception as e:
        return {"success": False, "error": str(e)}
