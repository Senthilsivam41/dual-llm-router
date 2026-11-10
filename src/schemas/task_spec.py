from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from ..verification.decimals import parse_decimal_string


class Check(BaseModel):
    """One expected value the executor's tests must assert."""

    id: str = Field(min_length=1)
    source: Literal["report", "edge"]
    description: str = Field(min_length=1)
    expected_value: str
    planner_value: str
    required: bool
    reason: str = ""

    @field_validator("expected_value", "planner_value")
    @classmethod
    def values_are_decimal_strings(cls, value: str) -> str:
        text = value.strip()
        parse_decimal_string(text)
        return text

    @model_validator(mode="after")
    def enforce_source_rules(self) -> "Check":
        if self.source == "report":
            if not self.required:
                raise ValueError("report checks are always required")
            return self
        if self.source == "edge":
            if not self.reason.strip():
                raise ValueError("edge checks need a reason")
            return self
        raise ValueError(f"unsupported check source: {self.source}")


class TaskSpec(BaseModel):
    goal: str = Field(..., description="High-level goal or task summary")
    target_files: List[str] = Field(default_factory=list, description="Files to inspect, create, or modify")
    acceptance_criteria: List[str] = Field(..., description="Measurable criteria to verify task completion")
    step_by_step_plan: List[str] = Field(..., description="Ordered list of execution steps")
    notes: Optional[str] = Field(None, description="Additional context or constraints for executor")
    checks: Optional[List[Check]] = Field(
        None,
        description="Structured expected values. Omitted for tasks that predate the issue-to-fix demo.",
    )

    @model_validator(mode="after")
    def enforce_check_rules(self) -> "TaskSpec":
        if not self.checks:
            self.checks = None
            return self
        ids = [check.id for check in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("check ids must be unique")
        required_edge = any(check.source == "edge" and check.required for check in self.checks)
        if not required_edge:
            raise ValueError("at least one edge-case check must be required")
        return self
