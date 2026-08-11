import os
from pathlib import Path
from typing import Any, Dict


def _secure_open_flags() -> int | None:
    if (
        os.open not in os.supports_dir_fd
        or os.mkdir not in os.supports_dir_fd
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
    ):
        return None
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def apply_patch(
    file_path: str,
    new_content: str,
    workspace_root: str = ".",
) -> Dict[str, Any]:
    """Write a file through pinned directory descriptors without following symlinks."""
    if os.path.isabs(file_path):
        return {"success": False, "error": f"Absolute paths not allowed: '{file_path}'"}

    relative_path = Path(file_path)
    if ".." in relative_path.parts:
        return {
            "success": False,
            "error": f"Parent directory traversal not allowed: '{file_path}'",
        }
    parts = [part for part in relative_path.parts if part not in ("", ".")]
    if not parts:
        return {"success": False, "error": "file_path must name a file"}

    directory_flags = _secure_open_flags()
    if directory_flags is None:
        return {
            "success": False,
            "error": "Secure descriptor-relative writes are unsupported on this platform",
        }

    workspace = Path(workspace_root).resolve()
    directory_fds = []
    file_fd = None
    try:
        root_fd = os.open(workspace, directory_flags)
        directory_fds.append(root_fd)
        parent_fd = root_fd

        for component in parts[:-1]:
            try:
                os.mkdir(component, mode=0o777, dir_fd=parent_fd)
            except FileExistsError:
                pass
            parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            directory_fds.append(parent_fd)

        file_flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
        file_fd = os.open(parts[-1], file_flags, 0o666, dir_fd=parent_fd)
        with os.fdopen(file_fd, "w", encoding="utf-8") as f:
            file_fd = None
            f.write(new_content)
            f.flush()
            os.fsync(f.fileno())
        return {
            "success": True,
            "file_path": file_path,
            "bytes_written": len(new_content.encode("utf-8")),
        }
    except (OSError, ValueError) as exc:
        return {"success": False, "error": str(exc)}
    finally:
        if file_fd is not None:
            os.close(file_fd)
        for directory_fd in reversed(directory_fds):
            os.close(directory_fd)
