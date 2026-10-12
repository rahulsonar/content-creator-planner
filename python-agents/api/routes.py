"""
API Routes
FastAPI route definitions for agent endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from schemas.requests import (
    ChatRequest
)
from schemas.responses import (
    ChatResponse
)
from api.middleware import verify_internal_request
from agents import PlanningAgent, ModelOrchestrator, ContextManagerAgent
from agents.workflow_orchestrator import WorkflowOrchestrator
from models import create_model_client
from storage.conversation import ConversationStorage
from storage.database import db_manager
from storage.agent_call_log import agent_call_logger
from storage.redis_client import get_redis_client
from utils.logger import logger
from utils.cleanup_orphaned_agents import orphaned_cleaner
from config.settings import settings
import httpx

# Initialize conversation storage
conversation_storage = ConversationStorage()

router = APIRouter()

# Webhook configuration
NEXTJS_WEBHOOK_URL = settings.NEXTJS_WEBHOOK_URL if hasattr(settings, 'NEXTJS_WEBHOOK_URL') else "http://app:3000/api/chat/webhook"
INTERNAL_API_SECRET = settings.INTERNAL_API_SECRET


async def _handle_dummy_chat(
    request: ChatRequest,
    user_id: int,
    conversation_storage: ConversationStorage
) -> ChatResponse:
    """
    Handle chat request with dummy AI responses (no API calls)
    
    Args:
        request: Chat request
        user_id: User ID (integer)
        conversation_storage: Conversation storage instance
        
    Returns:
        Dummy chat response
    """
    logger.info(f"[DUMMY MODE] Processing chat for user: {user_id}")
    
    # Create or get conversation
    conversation_id = request.conversationId
    if not conversation_id:
        # Use first 60 chars of message as title
        title = request.message[:60] + "..." if len(request.message) > 60 else request.message
        conversation_id = await conversation_storage.create_conversation(
            user_id=user_id,
            conversation_type="planning",
            title=title
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


async def notify_websocket(conversation_id: int, message: str = None, role: str = "assistant", model: str = None, status: str = None, error: str = None):
    """
    Send webhook notification to Next.js to update WebSocket clients
    
    Args:
        conversation_id: The conversation ID (integer)
        message: The assistant's message (if completed)
        role: Message role
        model: Model used
        status: Status update (e.g., "processing")
        error: Error message (if failed)
    """
    try:
        payload = {
            "conversationId": conversation_id,
        }
        
        if message:
            payload["message"] = message
            payload["role"] = role
            payload["model"] = model
        
        if status:
            payload["status"] = status
        
        if error:
            payload["error"] = error
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                NEXTJS_WEBHOOK_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Secret": INTERNAL_API_SECRET,
                }
            )
            
            if response.status_code == 200:
                logger.info(f"[Webhook] Successfully notified WebSocket for conversation {conversation_id}")
            else:
                logger.warning(f"[Webhook] Failed to notify WebSocket: {response.status_code}")
    except Exception as e:
        logger.error(f"[Webhook] Error sending webhook notification: {e}")
        # Don't raise - webhook failure shouldn't break the main flow


async def process_chat_background(
    conversation_id: int,
    user_id: str,
    message: str,
    context: dict,
    message_id: str,
    conversation_messages: list,
    user_name: str | None = None
):
    """
    Background task to process chat message with agent
    
    Args:
        conversation_id: Conversation ID (integer)
        user_id: User ID
        message: User's message
        context: User context
        message_id: Unique message ID for tracking
        conversation_messages: Full conversation history
        user_name: Optional user name for personalization
    """
    try:
        logger.info(f"[Background] Processing message for conversation {conversation_id}")
        
        # Notify that processing has started
        await notify_websocket(conversation_id, status="processing")
        
        # Check if workflow orchestrator is enabled
        use_workflow = getattr(settings, 'USE_WORKFLOW_ORCHESTRATOR', False)
        
        if use_workflow:
            await process_with_workflow_orchestrator(
                conversation_id=conversation_id,
                user_id=user_id,
                message=message,
                context=context,
                message_id=message_id,
                conversation_messages=conversation_messages,
                user_name=user_name
            )
        else:
            await process_with_planner_agent(
                conversation_id=conversation_id,
                user_id=user_id,
                message=message,
                context=context,
                message_id=message_id,
                conversation_messages=conversation_messages,
                user_name=user_name
            )
        
    except Exception as e:
        logger.error(f"[Background] Error processing chat: {e}")
        # Notify of error
        await notify_websocket(
            conversation_id,
            error=str(e)
        )


async def process_with_workflow_orchestrator(
    conversation_id: int,
    user_id: str,
    message: str,
    context: dict,
    message_id: str,
    conversation_messages: list,
    user_name: str | None = None
):
    """
    Process chat message using the WorkflowOrchestrator (Plan → Execute → Synthesize → Replan)
    
    Args:
        conversation_id: Conversation ID (integer)
        user_id: User ID
        message: User's message
        context: User context
        message_id: Unique message ID for tracking
        conversation_messages: Full conversation history
        user_name: Optional user name for personalization
    """
    try:
        logger.info(f"[Workflow] Starting workflow orchestration for conversation {conversation_id}")
        
        # Get models from orchestrator
        planner_model = ModelOrchestrator.get_model_for_agent("planning")
        context_model = ModelOrchestrator.get_model_for_agent("context_manager")
        
        # Initialize clients
        metadata_base = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "message_id": message_id
        }
        
        planner_client = create_model_client(planner_model, metadata={**metadata_base, "agent_name": "planning"})
        context_client = create_model_client(context_model, metadata={**metadata_base, "agent_name": "context_manager"})
        synthesizer_client = create_model_client(planner_model, metadata={**metadata_base, "agent_name": "synthesizer"})
        
        # Get database session and Redis client
        async with db_manager.get_session() as db_session:
            redis_client = await get_redis_client(settings)
            
            # Create supporting agents
            context_manager = ContextManagerAgent(context_client, db_session=db_session)
            
            
            # Create PlanningAgent in workflow mode
            # In workflow mode, planner only has access to utility tools (redis, context reading)
            # Execution tools (manage_user_tasks, delegate_to_agents) are filtered out
            # This ensures planner creates task plans instead of executing tasks directly
            planner_agent = PlanningAgent(
                planner_client,
                enable_openai_tools=True,  # Keep tools enabled
                workflow_mode=True,  # But restrict to planning-only tools
                context_manager_agent=context_manager,
                conversation_storage=conversation_storage,
                redis_client=redis_client
            )
            
            # Set user information
            if user_name:
                planner_agent._current_user_name = user_name
            
            # Load conversation history
            if conversation_messages:
                planner_agent.load_conversation_history(conversation_messages)
            
            # Create WorkflowOrchestrator
            orchestrator = WorkflowOrchestrator(
                planner_agent=planner_agent,
                model_client=synthesizer_client,
                redis_client=redis_client,
                conversation_storage=conversation_storage,
                context_manager_agent=context_manager,
                websocket_manager=None,  # Will use notify_websocket function instead
                max_iterations=getattr(settings, 'MAX_WORKFLOW_ITERATIONS', 3)
            )
            
            # Execute workflow
            result = await orchestrator.execute_workflow(
                user_query=message,
                conversation_id=conversation_id,
                message_id=message_id,
                user_id=user_id,
                user_name=user_name
            )
            
            # Extract response
            response_message = result.get('message', 'Request processed.')
            metadata = result.get('metadata', {})
            
            # Save assistant response
            await conversation_storage.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_message,
                model=planner_model
            )
            
            # Notify WebSocket clients of completion
            await notify_websocket(
                conversation_id,
                message=response_message,
                role="assistant",
                model=planner_model
            )
            
            logger.info(
                f"[Workflow] Completed in {metadata.get('iterations', 1)} iteration(s), "
                f"{metadata.get('total_tasks_executed', 0)} tasks executed"
            )
            
    except Exception as e:
        logger.error(f"[Workflow] Error in workflow orchestration: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def process_with_planner_agent(
    conversation_id: int,
    user_id: str,
    message: str,
    context: dict,
    message_id: str,
    conversation_messages: list,
    user_name: str | None = None
):
    """
    Process chat message using the original PlanningAgent (legacy flow)
    
    Args:
        conversation_id: Conversation ID (integer)
        user_id: User ID
        message: User's message
        context: User context
        message_id: Unique message ID for tracking
        conversation_messages: Full conversation history
        user_name: Optional user name for personalization
    """
    try:
        logger.info(f"[Background] Processing message for conversation {conversation_id}")
        
        # Notify that processing has started
        await notify_websocket(conversation_id, status="processing")
        
        # Get models from orchestrator (reads from env config)
        planner_model = ModelOrchestrator.get_model_for_agent("planning")
        context_model = ModelOrchestrator.get_model_for_agent("context_manager")
        
        logger.info(f"[Models] Planning Agent: {planner_model}, Context Manager: {context_model}")
        
        # Initialize clients with metadata for API tracking
        metadata = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "agent_name": "planning"
        }
        client = create_model_client(planner_model, metadata=metadata)
        
        # Create context manager agent with database session
        context_metadata = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "agent_name": "context_manager"
        }
        context_client = create_model_client(context_model, metadata=context_metadata)
        
        # Get database session
        async with db_manager.get_session() as db_session:
            # Get Redis client
            redis_client = await get_redis_client(settings)
            
            context_manager = ContextManagerAgent(context_client, db_session=db_session)
            
        
            agent = PlanningAgent(
                client, 
                enable_openai_tools=settings.ENABLE_OPENAI_TOOLS, 
                context_manager_agent=context_manager,
                conversation_storage=conversation_storage,
                redis_client=redis_client
            )
            
            # Set user information for personalization
            if user_name:
                agent._current_user_name = user_name
            
            # Load conversation history into agent
            if conversation_messages:
                agent.load_conversation_history(conversation_messages)
            
            # Load user context from storage and add tracking IDs
            user_context = context or {}
            user_context["user_id"] = user_id
            user_context["user_name"] = user_name
            user_context["conversation_id"] = conversation_id
            user_context["message_id"] = message_id
            
            logger.info(f"[Background] Processing message with context: user={user_id}, conv={conversation_id}, msg={message_id}")
            
            response = await agent.process_message(message, user_context)
        
        # Save assistant response with the actual model used
        await conversation_storage.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
            model=planner_model
        )
        
        # Notify WebSocket clients of completion
        await notify_websocket(
            conversation_id,
            message=response,
            role="assistant",
            model=planner_model
        )
        
        logger.info(f"[Background] Completed processing for conversation {conversation_id}")
        
    except Exception as e:
        logger.error(f"[Background] Error processing chat: {e}")
        # Notify of error
        await notify_websocket(
            conversation_id,
            error=str(e)
        )


@router.post("/planning/chat")
async def planning_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user_info: tuple[str, str | None] = Depends(verify_internal_request)
):
    """
    Planning agent chat endpoint for content strategy conversations
    
    Args:
        request: Chat message with conversation history
        user_info: Tuple of (user_id, user_name) from authentication
        
    Returns:
        Agent response
    """
    try:
        # Unpack user_id and user_name from the tuple
        user_id, user_name = user_info
        logger.info(f"Processing planning chat for user: {user_id} ({user_name})")
        
        # Check if dummy AI mode is enabled
        if settings.USE_DUMMY_AI:
            return await _handle_dummy_chat(request, user_id, conversation_storage)
        
        # Generate unique message ID for tracking this user message across all agent calls
        message_id = agent_call_logger.generate_message_id()
        logger.info(f"[ROUTES] Generated message_id: {message_id} for user {user_id}")
        
        # Create or get conversation
        conversation_id = request.conversationId
        if not conversation_id:
            # Use first 60 chars of message as title
            title = request.message[:60] + "..." if len(request.message) > 60 else request.message
            conversation_id = await conversation_storage.create_conversation(
                user_id=user_id,
                conversation_type="planning",
                title=title
            )
        # Note: Anonymous user logic removed - all users must be authenticated
        # If conversation exists, it already belongs to the current user
        
        # Save user message
        await conversation_storage.save_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        
        # Load full conversation history
        conversation = await conversation_storage.get_conversation(conversation_id)
        conversation_messages = conversation.get("messages", []) if conversation else []
        
        # Add background task to process the message
        background_tasks.add_task(
            process_chat_background,
            conversation_id=conversation_id,
            user_id=user_id,
            message=request.message,
            context=request.context,
            message_id=message_id,
            conversation_messages=conversation_messages,
            user_name=user_name
        )
        
        # Return immediately with 202 Accepted
        logger.info(f"[ROUTES] Queued background task for conversation {conversation_id}")
        
        return ChatResponse(
            message="Processing your request...",
            model="processing",
            conversationId=conversation_id
        )
        
    except Exception as e:
        logger.error(f"Error in planning chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/cleanup-orphaned-agents")
async def cleanup_orphaned_agents(max_age_minutes: int = 30):
    """
    Cleanup orphaned agent calls stuck in IN_PROGRESS state
    
    Args:
        max_age_minutes: Maximum age in minutes before considering a call orphaned (default: 30)
        
    Returns:
        Cleanup statistics
    """
    try:
        logger.info(f"Starting orphaned agent cleanup (max_age: {max_age_minutes} minutes)")
        result = await orphaned_cleaner.cleanup_orphaned_calls(max_age_minutes)
        logger.info(f"Orphaned agent cleanup completed: {result}")
        return {
            "success": True,
            "cleanup": result
        }
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/orphaned-agents/stats")
async def get_orphaned_stats(max_age_minutes: int = 30):
    """
    Get statistics about orphaned agent calls without cleaning them up
    
    Args:
        max_age_minutes: Threshold for considering calls orphaned (default: 30)
        
    Returns:
        Statistics about orphaned calls
    """
    try:
        logger.info(f"Fetching orphaned agent statistics (max_age: {max_age_minutes} minutes)")
        stats = await orphaned_cleaner.get_orphaned_statistics(max_age_minutes)
        return {
            "success": True,
            "statistics": stats,
            "threshold_minutes": max_age_minutes
        }
    except Exception as e:
        logger.error(f"Failed to get orphaned stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

