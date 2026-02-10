"""
Response Schemas
Pydantic models for API responses
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class PlanningResponse(BaseModel):
    """Planning agent response"""
    plan: Dict[str, Any]
    model: str
    totalTasks: int
    estimatedHours: Optional[float] = None
    conversationId: Optional[int] = None


class ChatResponse(BaseModel):
    """General chat response"""
    message: str
    model: str
    conversationId: Optional[int] = None


class ConversationResponse(BaseModel):
    """Conversation record"""
    id: int
    type: str
    status: str
    createdAt: datetime
    lastMessageAt: Optional[datetime] = None
    totalTokens: int = 0
    estimatedCost: float = 0.0


class ContextResponse(BaseModel):
    """User context response"""
    userId: str
    channelName: Optional[str] = None
    channelType: Optional[str] = None
    contentGoals: Optional[str] = None
    uploadFrequency: Optional[str] = None
    isTeam: bool = False
    updatedAt: datetime


class UsageStatsResponse(BaseModel):
    """User usage statistics"""
    userId: str
    requestsToday: int
    requestsLastMinute: int
    lifetimeTokens: int
    estimatedCost: float


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str


class TaskManagerResponse(BaseModel):
    """[DEPRECATED] Task Manager agent response - TaskManager has been removed"""
    status: str  # "success", "error", "partial"
    action: Optional[str] = None  # "create", "search", "update", "get_one", "add_notes"
    message: str  # Human-readable summary
    data: Optional[Dict[str, Any]] = None  # Structured result data (tasks, counts, IDs, etc.)
    error: Optional[str] = None  # Error message if status is "error"
    metadata: Optional[Dict[str, Any]] = None  # Operation metadata (count, duration, etc.)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "action": "create",
                "message": "Created 5 tasks successfully",
                "data": {
                    "created_count": 5,
                    "task_ids": ["id1", "id2", "id3", "id4", "id5"]
                },
                "metadata": {
                    "operation_time_ms": 250
                }
            }
        }
