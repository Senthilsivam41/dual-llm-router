import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    SHELL = "shell"
    RUN_SHELL = "run_shell"
    PATCH = "patch"
    APPLY_PATCH = "apply_patch"


class ShellAction(BaseModel):
    type: str = Field(default=ActionType.SHELL, pattern=f"^({ActionType.SHELL.value}|{ActionType.RUN_SHELL.value})$")
    command: str = Field(min_length=1, max_length=10000)
    timeout: Optional[int] = Field(default=120, ge=1, le=300)


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


ActionModel = Union[ShellAction, PatchAction]


def validate_action(action: Dict[str, Any]) -> ActionModel:
    action_type = action.get("type")
    if not action_type:
        raise ValueError("Action missing required 'type' field")

    try:
        action_enum = ActionType(action_type)
    except ValueError:
        raise ValueError(f"Unsupported action type: {action_type}")

    model_map = {
        ActionType.SHELL: ShellAction,
        ActionType.RUN_SHELL: ShellAction,
        ActionType.PATCH: PatchAction,
        ActionType.APPLY_PATCH: PatchAction,
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
