"""
Request Schemas
Pydantic models for API request validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any



class PlanningRequest(BaseModel):
    """Request to generate project plan"""
    projectDescription: str = Field(..., min_length=10, max_length=5000)
    conversationId: Optional[int] = None
    userContext: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """General chat request"""
    message: str = Field(..., min_length=1, max_length=5000)
    conversationId: Optional[int] = None
    context: Optional[Dict[str, Any]] = None


class TaskCreateRequest(BaseModel):
    """Request to create tasks from plan"""
    planId: str
    tasks: List[Dict[str, Any]]
    userId: str


class TaskUpdateRequest(BaseModel):
    """Request to update a single task"""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # TODO, IN_PROGRESS, REVIEW, BLOCKED, COMPLETED, CANCELLED
    priority: Optional[str] = None  # LOW, MEDIUM, HIGH, URGENT
    estimatedHours: Optional[float] = None
    actualHours: Optional[float] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    dueDate: Optional[str] = None
    completedAt: Optional[str] = None
    assignedTo: Optional[str] = None
    aiContext: Optional[str] = None
    aiSuggestions: Optional[str] = None
    tags: Optional[List[str]] = None
    labels: Optional[List[str]] = None


class TaskBatchUpdateRequest(BaseModel):
    """Request to update multiple tasks in batch"""
    tasks: List[Dict[str, Any]]  # Each item must have "id" + optional update fields


class ContextUpdateRequest(BaseModel):
    """Request to update user context"""
    channelName: Optional[str] = None
    channelType: Optional[str] = None
    channelTopic: Optional[str] = None
    channelSize: Optional[str] = None
    ageGroup: Optional[str] = None
    location: Optional[str] = None
    isTeam: Optional[bool] = None
    teamSize: Optional[int] = None
    uploadFrequency: Optional[str] = None
    contentGoals: Optional[str] = None
    challenges: Optional[str] = None
    thoughtProcess: Optional[str] = None
