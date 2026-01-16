"""
API Routes
FastAPI route definitions for agent endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from schemas.requests import (
    PlanningRequest,
    ChatRequest
)
from schemas.responses import (
    PlanningResponse,
    ChatResponse
)
from api.middleware import verify_internal_request
from agents import PlanningAgent, ModelOrchestrator
from agents.context_manager import ContextManagerAgent
from models import OpenAIClient
from storage.conversation import ConversationStorage
from storage.database import db_manager
from utils.logger import logger
from config.settings import settings

# Initialize conversation storage
conversation_storage = ConversationStorage()

router = APIRouter()


async def _handle_dummy_chat(
    request: ChatRequest,
    user_id: str,
    conversation_storage: ConversationStorage
) -> ChatResponse:
    """
    Handle chat request with dummy AI responses (no API calls)
    
    Args:
        request: Chat request
        user_id: User ID
        conversation_storage: Conversation storage instance
        
    Returns:
        Dummy chat response
    """
    logger.info(f"[DUMMY MODE] Processing chat for user: {user_id}")
    
    # Create or get conversation
    conversation_id = request.conversationId
    if not conversation_id:
        conversation_id = await conversation_storage.create_conversation(
            user_id=user_id,
            conversation_type="planning",
            title="Planning Chat (Dummy Mode)"
        )
    
    # Save user message
    await conversation_storage.save_message(
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    
    # Generate dummy response based on message content
    user_msg_lower = request.message.lower()
    
    if any(word in user_msg_lower for word in ["hello", "hi", "hey"]):
        dummy_response = "Hello! I'm running in dummy mode. I can help you with content planning, but I'm not making real AI API calls right now. What would you like to work on?"
    elif any(word in user_msg_lower for word in ["task", "plan", "project"]):
        dummy_response = """I can help you with that! Here's a sample plan:

**Content Creation Project Plan**

1. **Research Phase** (2 hours)
   - Identify target audience
   - Research trending topics
   - Compile reference materials

2. **Content Strategy** (3 hours)
   - Define content pillars
   - Create content calendar
   - Plan distribution channels

3. **Production** (5 hours)
   - Script/outline creation
   - Recording/writing
   - Editing and refinement

Note: This is a dummy response. Enable real AI for personalized planning."""
    elif any(word in user_msg_lower for word in ["help", "what can you do"]):
        dummy_response = """I can assist with:
- Content project planning
- Task breakdown and estimation
- Content strategy discussions
- Resource allocation

Currently in DUMMY MODE - responses are static. Set USE_DUMMY_AI=false to enable real AI capabilities."""
    else:
        dummy_response = f"[Dummy AI Response] I received your message: \"{request.message[:100]}...\"\n\nThis is a placeholder response. In real mode, I would analyze your request and provide personalized content planning assistance. To enable real AI, set USE_DUMMY_AI=false in your environment."
    
    # Save assistant response
    await conversation_storage.save_message(
        conversation_id=conversation_id,
        role="assistant",
        content=dummy_response,
        model="dummy-ai"
    )
    
    return ChatResponse(
        message=dummy_response,
        conversationId=conversation_id,
        model="dummy-ai",
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )


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
        
        # Check if dummy AI mode is enabled
        if settings.USE_DUMMY_AI:
            return await _handle_dummy_chat(request, user_id, conversation_storage)
        
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
        client = OpenAIClient(model=model_name)
        
        # Create context manager agent with database session
        context_client = OpenAIClient(model="gpt-4")
        
        # Get database session
        async for db_session in db_manager.get_session():
            context_manager = ContextManagerAgent(context_client, db_session=db_session)
        
            agent = PlanningAgent(
                client, 
                enable_openai_tools=settings.ENABLE_OPENAI_TOOLS, 
                context_manager_agent=context_manager,
                conversation_storage=conversation_storage
            )
            
            # Load conversation history into agent
            if conversation_messages:
                agent.load_conversation_history(conversation_messages)
            
            # Load user context from storage and add user_id and conversation_id
            user_context = request.context or {}
            user_context["user_id"] = user_id
            user_context["conversation_id"] = conversation_id
            
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

