"""Pydantic schemas for implementation plan API endpoints."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CreatePlanRequest(BaseModel):
    """Request to create a new implementation plan."""

    user_request: str = Field(..., min_length=5, max_length=2000,
                               description="User's feature request or description")
    project_id: int = Field(..., description="ID of the project to create plan for")


class ApproveRejectRequest(BaseModel):
    """Request to approve or reject a plan."""

    comment: Optional[str] = Field(None, max_length=500,
                                    description="Optional comment explaining the decision")


class UpdateTaskRequest(BaseModel):
    """Request to update task completion status."""

    completed: bool = Field(..., description="Whether the task is completed")


class TaskResponse(BaseModel):
    """Response model for a single task."""

    id: int
    plan_id: int
    category: str
    description: str
    order_index: int
    completed: bool
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanResponse(BaseModel):
    """Response model for an implementation plan."""

    id: int
    project_id: int
    title: str
    user_request: str
    status: str
    estimated_time: Optional[str] = None
    total_tasks: int
    completed_tasks: int
    progress: float
    markdown_content: Optional[str] = None
    file_path: str
    walkthrough_path: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tasks: List[TaskResponse] = []

    class Config:
        from_attributes = True


class PlanListResponse(BaseModel):
    """Response model for a list of plans (without full task details)."""

    id: int
    project_id: int
    title: str
    user_request: str
    status: str
    estimated_time: Optional[str] = None
    total_tasks: int
    completed_tasks: int
    progress: float
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MarkdownResponse(BaseModel):
    """Response model for markdown content."""

    markdown: str
    file_path: Optional[str] = None
