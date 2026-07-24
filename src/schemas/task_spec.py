from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

class TaskSpec(BaseModel):
    goal: str = Field(..., description="High-level goal or task summary")
    target_files: List[str] = Field(default_factory=list, description="Files to inspect, create, or modify")
    acceptance_criteria: List[str] = Field(..., description="Measurable criteria to verify task completion")
    step_by_step_plan: List[str] = Field(..., description="Ordered list of execution steps")
    notes: Optional[str] = Field(None, description="Additional context or constraints for executor")
