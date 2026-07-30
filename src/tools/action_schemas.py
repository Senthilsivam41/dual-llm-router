import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    SHELL = "shell"
    PATCH = "patch"
    APPLY_PATCH = "apply_patch"
    READ = "read"
    WRITE = "write"
    LIST = "list"
    GLOB = "glob"
    GREP = "grep"
    TASK = "task"


class ShellAction(BaseModel):
    type: str = Field(default=ActionType.SHELL, pattern=f"^{ActionType.SHELL.value}$")
    command: str = Field(min_length=1, max_length=10000)
    cwd: Optional[str] = None
    timeout: Optional[int] = Field(default=120, ge=1, le=300)

    @field_validator("cwd")
    @classmethod
    def validate_cwd(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if os.path.isabs(v):
                raise ValueError("cwd must be relative path")
            if ".." in Path(v).parts:
                raise ValueError("cwd cannot contain parent directory references")
        return v


class PatchAction(BaseModel):
    type: str = Field(pattern=f"^({ActionType.PATCH.value}|{ActionType.APPLY_PATCH.value})$")
    file_path: str = Field(min_length=1)
    patch: Optional[str] = Field(default=None, min_length=1)
    content: Optional[str] = Field(default=None, min_length=1)

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if os.path.isabs(v):
            raise ValueError("file_path must be relative path")
        if ".." in Path(v).parts:
            raise ValueError("file_path cannot contain parent directory references")
        return v

    @field_validator("patch", "content", mode="before")
    @classmethod
    def validate_patch_or_content(cls, v):
        return v

    def model_post_init(self, __context):
        if self.patch is None and self.content is None:
            raise ValueError("Either 'patch' or 'content' field is required")
        if self.patch is None:
            self.patch = self.content


class ReadAction(BaseModel):
    type: str = Field(default=ActionType.READ, pattern=f"^{ActionType.READ.value}$")
    file_path: str = Field(min_length=1)
    offset: Optional[int] = Field(default=None, ge=0)
    limit: Optional[int] = Field(default=None, ge=1, le=10000)

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if os.path.isabs(v):
            raise ValueError("file_path must be relative path")
        if ".." in Path(v).parts:
            raise ValueError("file_path cannot contain parent directory references")
        return v


class WriteAction(BaseModel):
    type: str = Field(default=ActionType.WRITE, pattern=f"^{ActionType.WRITE.value}$")
    file_path: str = Field(min_length=1)
    content: str

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if os.path.isabs(v):
            raise ValueError("file_path must be relative path")
        if ".." in Path(v).parts:
            raise ValueError("file_path cannot contain parent directory references")
        return v


class ListAction(BaseModel):
    type: str = Field(default=ActionType.LIST, pattern=f"^{ActionType.LIST.value}$")
    path: str = Field(default=".")
    recursive: bool = False

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if os.path.isabs(v):
            raise ValueError("path must be relative path")
        if ".." in Path(v).parts:
            raise ValueError("path cannot contain parent directory references")
        return v


class GlobAction(BaseModel):
    type: str = Field(default=ActionType.GLOB, pattern=f"^{ActionType.GLOB.value}$")
    pattern: str = Field(min_length=1)
    path: Optional[str] = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if os.path.isabs(v):
                raise ValueError("path must be relative path")
            if ".." in Path(v).parts:
                raise ValueError("path cannot contain parent directory references")
        return v


class GrepAction(BaseModel):
    type: str = Field(default=ActionType.GREP, pattern=f"^{ActionType.GREP.value}$")
    pattern: str = Field(min_length=1)
    path: Optional[str] = None
    include: Optional[str] = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if os.path.isabs(v):
                raise ValueError("path must be relative path")
            if ".." in Path(v).parts:
                raise ValueError("path cannot contain parent directory references")
        return v


class TaskAction(BaseModel):
    type: str = Field(default=ActionType.TASK, pattern=f"^{ActionType.TASK.value}$")
    description: str = Field(min_length=1, max_length=500)
    prompt: str = Field(min_length=1, max_length=10000)


ActionModel = Union[
    ShellAction,
    PatchAction,
    ReadAction,
    WriteAction,
    ListAction,
    GlobAction,
    GrepAction,
    TaskAction,
]


def validate_action(action: Dict[str, Any]) -> ActionModel:
    action_type = action.get("type")
    if not action_type:
        raise ValueError("Action missing required 'type' field")

    try:
        action_enum = ActionType(action_type)
    except ValueError:
        raise ValueError(f"Unknown action type: {action_type}")

    model_map = {
        ActionType.SHELL: ShellAction,
        ActionType.PATCH: PatchAction,
        ActionType.APPLY_PATCH: PatchAction,
        ActionType.READ: ReadAction,
        ActionType.WRITE: WriteAction,
        ActionType.LIST: ListAction,
        ActionType.GLOB: GlobAction,
        ActionType.GREP: GrepAction,
        ActionType.TASK: TaskAction,
    }

    model = model_map.get(action_enum)
    if not model:
        raise ValueError(f"No validator for action type: {action_type}")

    return model(**action)


def validate_actions(actions: List[Dict[str, Any]]) -> List[ActionModel]:
    validated = []
    for i, action in enumerate(actions):
        try:
            validated.append(validate_action(action))
        except Exception as e:
            raise ValueError(f"Action {i} validation failed: {e}")
    return validated