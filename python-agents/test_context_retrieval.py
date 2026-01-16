"""  
Test script to demonstrate context retrieval tool in planner agent
"""
import asyncio
from models.openai_client import OpenAIClient
from agents.planner import PlanningAgent
from agents.context_manager import ContextManagerAgent
from utils.logger import logger


async def test_context_retrieval():
    """Test the planner agent's ability to request context from context manager"""
    
    # Initialize clients and agents
    openai_client = OpenAIClient()
    context_manager = ContextManagerAgent(openai_client)
    planner = PlanningAgent(openai_client, context_manager_agent=context_manager)
    
    test_user_id = "test_user_123"
    
    # Step 1: First, let's save some context (simulate user sharing information)
    logger.info("=" * 60)
    logger.info("STEP 1: Saving user context via context manager")
    logger.info("=" * 60)
    
    setup_message = """I want to create content about sustainable living. 
My target audience is young professionals aged 25-35 who are interested in eco-friendly lifestyle. 
I primarily create content for YouTube and Instagram. 
My goal is to reach 10k subscribers on YouTube by the end of the year."""
    
    setup_response = await context_manager.process_message(
        user_message=f"Save this user information: {setup_message}",
        user_context={"user_id": test_user_id}
    )
    logger.info(f"Context saved: {setup_response}\n")
    
    # Step 2: Now test the planner retrieving this context
    logger.info("=" * 60)
    logger.info("STEP 2: Planner requests context and creates plan")
    logger.info("=" * 60)
    
    planning_request = """Help me create a content calendar for next month. 
I need ideas that align with my audience and goals."""
    
    # The planner should automatically request context about:
    # - User's content goals
    # - Target audience
    # - Platforms they use
    planner_response = await planner.process_message(
        user_message=planning_request,
        user_context={"user_id": test_user_id}
    )
    
    logger.info(f"Planner response:\n{planner_response}\n")
    
    # Step 3: Test multiple context retrievals
    logger.info("=" * 60)
    logger.info("STEP 3: Planner makes specific content request")
    logger.info("=" * 60)
    
    specific_request = """Create 5 video ideas specifically for my YouTube channel 
that would help me reach my subscriber goal."""
    
    planner_response_2 = await planner.process_message(
        user_message=specific_request,
        user_context={"user_id": test_user_id}
    )
    
    logger.info(f"Planner response:\n{planner_response_2}\n")
    
    logger.info("=" * 60)
    logger.info("TEST COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_context_retrieval())
