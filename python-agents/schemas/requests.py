"""
Request Schemas
Pydantic models for API request validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class OnboardingStartRequest(BaseModel):
    """Request to start onboarding"""
    conversationId: Optional[str] = None


class OnboardingMessageRequest(BaseModel):
    """Onboarding message from user"""
    conversationId: str
    message: str = Field(..., min_length=1, max_length=5000)


class PlanningRequest(BaseModel):
    """Request to generate project plan"""
    projectDescription: str = Field(..., min_length=10, max_length=5000)
    conversationId: Optional[str] = None
    userContext: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """General chat request"""
    message: str = Field(..., min_length=1, max_length=5000)
    conversationId: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class TaskCreateRequest(BaseModel):
    """Request to create tasks from plan"""
    planId: str
    tasks: List[Dict[str, Any]]
    userId: str


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
