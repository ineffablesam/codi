"""Pydantic schemas for Opik tracing API."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EvaluationResponse(BaseModel):
    """Evaluation response schema."""
    id: str
    trace_id: str
    metric_name: str
    score: float
    reason: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TraceResponse(BaseModel):
    """Trace response schema."""
    id: str
    user_id: int
    project_id: Optional[int] = None
    parent_trace_id: Optional[str] = None
    trace_type: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    evaluations: Optional[List[EvaluationResponse]] = None
    
    class Config:
        from_attributes = True


class TraceListResponse(BaseModel):
    """List of traces with pagination."""
    traces: List[TraceResponse]
    total: int
    page: int
    page_size: int


class SummarizeCodeRequest(BaseModel):
    """Request to summarize code."""
    code: str = Field(..., description="Code to summarize")
    instruction: str = Field(default="Explain what this code does", description="What to focus on")
    density_iterations: int = Field(default=2, ge=1, le=5, description="Number of refinement passes")
    model: str = Field(default="gemini-3-flash-preview", description="Gemini model to use")


class SummarizeCodeResponse(BaseModel):
    """Response from code summarization."""
    summary: str
    trace_id: Optional[str] = None
    quality_score: Optional[float] = None
    quality_reason: Optional[str] = None


class OpikSettingsUpdate(BaseModel):
    """Update user's Opik settings."""
    opik_enabled: Optional[bool] = None
    opik_workspace: Optional[str] = None


class OpikSettingsResponse(BaseModel):
    """User's Opik settings."""
    opik_enabled: bool
    opik_workspace: Optional[str] = None
    has_api_key: bool  # Don't return the actual key
