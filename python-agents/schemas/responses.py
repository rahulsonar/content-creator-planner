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
    conversationId: Optional[str] = None


class ChatResponse(BaseModel):
    """General chat response"""
    message: str
    model: str
    conversationId: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation record"""
    id: str
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
