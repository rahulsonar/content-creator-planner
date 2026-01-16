"""
API Routes
FastAPI route definitions for agent endpoints
"""
from typing import Optional
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
from storage.conversation import ConversationStorage
from utils.logger import logger

# Initialize conversation storage
conversation_storage = ConversationStorage()

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
        
        # Create or get conversation ID
        conversation_id = request.conversationId
        if not conversation_id:
            conversation_id = await conversation_storage.create_conversation(
                user_id=user_id,
                conversation_type="onboarding",
                title="Onboarding Conversation"
            )
        
        # Select model
        model_name = ModelOrchestrator.select_model("onboarding_initial")
        
        # Initialize client and agent
        if "gpt" in model_name:
            client = OpenAIClient(model=model_name)
        else:
            client = AnthropicClient(model=model_name)
        
        agent = OnboardingAgent(client)
        welcome_message = await agent.start_onboarding()
        
        # Save assistant message to conversation
        await conversation_storage.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=welcome_message,
            model=model_name
        )
        
        return OnboardingResponse(
            message=welcome_message,
            conversationId=conversation_id,
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
        
        # Load conversation from storage
        conversation = await conversation_storage.get_conversation(request.conversationId)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Save user message
        await conversation_storage.save_message(
            conversation_id=request.conversationId,
            role="user",
            content=request.message
        )
        
        # Select model
        model_name = ModelOrchestrator.select_model("onboarding_initial")
        
        # Initialize client and agent
        if "gpt" in model_name:
            client = OpenAIClient(model=model_name)
        else:
            client = AnthropicClient(model=model_name)
        
        agent = OnboardingAgent(client)
        response = await agent.process_message(request.message)
        
        # Save assistant response
        await conversation_storage.save_message(
            conversation_id=request.conversationId,
            role="assistant",
            content=response,
            model=model_name
        )
        
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
        
        from config.settings import settings
        agent = PlanningAgent(client, enable_openai_tools=settings.ENABLE_OPENAI_TOOLS)
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


@router.post("/planning/chat")
async def planning_chat(
    request: ChatRequest,
    user_id: str = Depends(verify_internal_request)
):
    """
    Planning agent chat endpoint for content strategy conversations
    
    Args:
        request: Chat message with conversation history
        user_id: Authenticated user ID
        
    Returns:
        Agent response
    """
    try:
        logger.info(f"Processing planning chat for user: {user_id}")
        
        # Create or get conversation
        conversation_id = request.conversationId
        if not conversation_id:
            conversation_id = await conversation_storage.create_conversation(
                user_id=user_id,
                conversation_type="planning",
                title="Planning Chat"
            )
        else:
            # If conversation exists, check if it needs to be claimed by authenticated user
            conversation = await conversation_storage.get_conversation(conversation_id)
            if conversation and conversation.get("userId") == "anonymous" and user_id != "anonymous":
                # Claim this anonymous conversation for the authenticated user
                await conversation_storage.update_conversation_user(conversation_id, user_id)
                logger.info(f"Claimed anonymous conversation {conversation_id} for user {user_id}")
        
        # Save user message
        await conversation_storage.save_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        
        # Load full conversation history
        conversation = await conversation_storage.get_conversation(conversation_id)
        conversation_messages = conversation.get("messages", []) if conversation else []
        
        # Select model
        model_name = ModelOrchestrator.select_model("planning")
        
        # Initialize client and agent
        if "gpt" in model_name:
            client = OpenAIClient(model=model_name)
        else:
            client = AnthropicClient(model=model_name)
        
        from config.settings import settings
        agent = PlanningAgent(client, enable_openai_tools=settings.ENABLE_OPENAI_TOOLS)
        
        # Load conversation history into agent
        if conversation_messages:
            agent.load_conversation_history(conversation_messages)
        
        # Load user context from storage
        user_context = request.context or {}
        
        response = await agent.process_message(request.message, user_context)
        
        # Save assistant response
        await conversation_storage.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
            model=model_name
        )
        
        return ChatResponse(
            message=response,
            model=model_name,
            conversationId=conversation_id
        )
        
    except Exception as e:
        logger.error(f"Error in planning chat: {e}")
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
        
        # Create or get conversation
        conversation_id = request.conversationId if hasattr(request, 'conversationId') else None
        if not conversation_id:
            conversation_id = await conversation_storage.create_conversation(
                user_id=user_id,
                conversation_type="chat",
                title="General Chat"
            )
        else:
            # If conversation exists, check if it needs to be claimed by authenticated user
            conversation = await conversation_storage.get_conversation(conversation_id)
            if conversation and conversation.get("userId") == "anonymous" and user_id != "anonymous":
                # Claim this anonymous conversation for the authenticated user
                await conversation_storage.update_conversation_user(conversation_id, user_id)
                logger.info(f"Claimed anonymous conversation {conversation_id} for user {user_id}")
        
        # Save user message
        await conversation_storage.save_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        
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
        
        # Save assistant response
        await conversation_storage.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
            model=model_name
        )
        
        return ChatResponse(
            message=response,
            model=model_name,
            conversationId=conversation_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_conversations(
    user_id: str = Depends(verify_internal_request),
    conversation_type: Optional[str] = None,
    limit: int = 10
):
    """
    Get user's conversation history
    
    Args:
        user_id: Authenticated user ID
        conversation_type: Optional filter by type (onboarding, planning, chat)
        limit: Maximum results to return
        
    Returns:
        List of conversations
    """
    try:
        logger.info(f"Retrieving conversations for user: {user_id}")
        
        conversations = await conversation_storage.get_user_conversations(
            user_id=user_id,
            conversation_type=conversation_type,
            limit=limit
        )
        
        return {
            "conversations": conversations,
            "count": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(verify_internal_request)
):
    """
    Get a specific conversation by ID
    
    Args:
        conversation_id: Conversation identifier
        user_id: Authenticated user ID (for authorization)
        
    Returns:
        Conversation data
    """
    try:
        logger.info(f"Retrieving conversation {conversation_id} for user: {user_id}")
        
        conversation = await conversation_storage.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Verify user owns this conversation or conversation is anonymous
        if conversation["userId"] != user_id and conversation["userId"] != "anonymous":
            raise HTTPException(status_code=403, detail="Access denied")
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

