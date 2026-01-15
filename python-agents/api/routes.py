"""
API Routes
FastAPI route definitions for agent endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from schemas.requests import (
    OnboardingStartRequest,
    OnboardingMessageRequest,
    PlanningRequest,
    ChatRequest
)
from schemas.responses import (
    OnboardingResponse,
    PlanningResponse,
    ChatResponse
)
from api.middleware import verify_internal_request
from agents import OnboardingAgent, PlanningAgent, ModelOrchestrator
from models import OpenAIClient, AnthropicClient
from utils.logger import logger

router = APIRouter()


@router.post("/onboarding/start")
async def start_onboarding(
    request: OnboardingStartRequest,
    user_id: str = Depends(verify_internal_request)
):
    """
    Start onboarding conversation
    
    Args:
        request: Onboarding start request
        user_id: Authenticated user ID from header
        
    Returns:
        Welcome message
    """
    try:
        logger.info(f"Starting onboarding for user: {user_id}")
        
        # Select model
        model_name = ModelOrchestrator.select_model("onboarding_initial")
        
        # Initialize client and agent
        if "gpt" in model_name:
            client = OpenAIClient(model=model_name)
        else:
            client = AnthropicClient(model=model_name)
        
        agent = OnboardingAgent(client)
        welcome_message = await agent.start_onboarding()
        
        return OnboardingResponse(
            message=welcome_message,
            conversationId=request.conversationId,
            model=model_name
        )
        
    except Exception as e:
        logger.error(f"Error starting onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboarding/message")
async def onboarding_message(
    request: OnboardingMessageRequest,
    user_id: str = Depends(verify_internal_request)
):
    """
    Process onboarding message
    
    Args:
        request: User message
        user_id: Authenticated user ID
        
    Returns:
        Agent response
    """
    try:
        logger.info(f"Processing onboarding message for user: {user_id}")
        
        # TODO: Load conversation from storage
        # TODO: Restore agent state
        
        # Select model
        model_name = ModelOrchestrator.select_model("onboarding_initial")
        
        # Initialize client and agent
        if "gpt" in model_name:
            client = OpenAIClient(model=model_name)
        else:
            client = AnthropicClient(model=model_name)
        
        agent = OnboardingAgent(client)
        response = await agent.process_message(request.message)
        
        # TODO: Save conversation to storage
        
        return OnboardingResponse(
            message=response,
            conversationId=request.conversationId,
            model=model_name
        )
        
    except Exception as e:
        logger.error(f"Error processing onboarding message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/planning/generate")
async def generate_plan(
    request: PlanningRequest,
    user_id: str = Depends(verify_internal_request)
):
    """
    Generate a content project plan
    
    Args:
        request: Planning request with project description
        user_id: Authenticated user ID
        
    Returns:
        Generated plan with tasks
    """
    try:
        logger.info(f"Generating plan for user: {user_id}")
        
        # TODO: Load user context from storage
        user_context = {}
        
        # Select model
        model_name = ModelOrchestrator.select_model("planning")
        
        # Initialize client and agent
        if "gpt" in model_name:
            client = OpenAIClient(model=model_name)
        else:
            client = AnthropicClient(model=model_name)
        
        agent = PlanningAgent(client)
        plan = await agent.generate_plan(request.projectDescription, user_context)
        
        # TODO: Save plan to storage
        
        return PlanningResponse(
            plan=plan,
            model=model_name,
            totalTasks=len(plan.get("tasks", []))
        )
        
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user_id: str = Depends(verify_internal_request)
):
    """
    General chat endpoint
    
    Args:
        request: Chat message
        user_id: Authenticated user ID
        
    Returns:
        Agent response
    """
    try:
        logger.info(f"Processing chat message for user: {user_id}")
        
        # Select model
        model_name = ModelOrchestrator.select_model("chat")
        
        # Initialize client
        if "gpt" in model_name:
            client = OpenAIClient(model=model_name)
        else:
            client = AnthropicClient(model=model_name)
        
        # Generate response
        messages = [{"role": "user", "content": request.message}]
        response = await client.generate_completion(messages)
        
        return ChatResponse(
            message=response,
            model=model_name
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
