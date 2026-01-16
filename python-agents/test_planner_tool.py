"""
Test script for planner agent with task_inserter tool
"""
import asyncio
from agents.planner import PlanningAgent
from models.anthropic_client import AnthropicClient
from utils.logger import logger


async def test_planner_with_tool():
    """Test planner agent creating and inserting tasks"""
    
    print("\n" + "="*60)
    print("Testing Planner Agent with Task Inserter Tool")
    print("="*60 + "\n")
    
    # Initialize client and agent
    client = AnthropicClient(model="claude-sonnet-4-20250514")
    planner = PlanningAgent(client)
    
    # User context
    user_context = {
        "channelName": "Tech Reviews Pro",
        "channelType": "YouTube - Tech Reviews",
        "uploadFrequency": "Weekly",
        "contentGoals": "Provide in-depth tech product reviews"
    }
    
    # Test request
    request = """
    I want to create a video reviewing the latest flagship smartphones.
    Help me plan this project with specific tasks and save them to my database.
    """
    
    print("User Request:")
    print(request)
    print("\n" + "-"*60 + "\n")
    
    print("Agent Response (streaming):\n")
    
    # Stream response with tool execution
    async for token in planner.stream_response(request, user_context):
        print(token, end="", flush=True)
    
    print("\n\n" + "="*60)
    print("Test completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_planner_with_tool())
