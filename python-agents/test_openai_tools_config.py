"""
Example: Testing PlanningAgent with OpenAI tools enabled/disabled
"""
import asyncio
from agents.planner import PlanningAgent
from models.openai_client import OpenAIClient
from config.settings import settings


async def test_with_tools_enabled():
    """Test planner agent WITH tool calling enabled"""
    print("\n" + "="*60)
    print("Test 1: OpenAI Tools ENABLED")
    print("="*60 + "\n")
    
    client = OpenAIClient(model="gpt-4")
    agent = PlanningAgent(client, enable_openai_tools=True)
    
    response = await agent.process_message(
        "Create a simple 3-task plan for launching a podcast. Yes, save them to database."
    )
    print(f"Response: {response}\n")
    print("Note: Agent can call insert_tasks_to_db function\n")


async def test_with_tools_disabled():
    """Test planner agent WITHOUT tool calling"""
    print("\n" + "="*60)
    print("Test 2: OpenAI Tools DISABLED")
    print("="*60 + "\n")
    
    client = OpenAIClient(model="gpt-4")
    agent = PlanningAgent(client, enable_openai_tools=False)
    
    response = await agent.process_message(
        "Create a simple 3-task plan for launching a podcast."
    )
    print(f"Response: {response}\n")
    print("Note: Agent operates in text-only mode, cannot call functions\n")


async def test_using_global_settings():
    """Test using global settings configuration"""
    print("\n" + "="*60)
    print("Test 3: Using Global Settings")
    print(f"ENABLE_OPENAI_TOOLS = {settings.ENABLE_OPENAI_TOOLS}")
    print("="*60 + "\n")
    
    client = OpenAIClient(model="gpt-4")
    agent = PlanningAgent(client, enable_openai_tools=settings.ENABLE_OPENAI_TOOLS)
    
    response = await agent.process_message(
        "Create a simple 3-task plan for launching a podcast."
    )
    print(f"Response: {response}\n")


async def main():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# PlanningAgent - OpenAI Tools Configuration Examples")
    print("#"*60)
    
    # Test 1: Tools enabled
    await test_with_tools_enabled()
    
    # Test 2: Tools disabled
    await test_with_tools_disabled()
    
    # Test 3: Using global settings
    await test_using_global_settings()
    
    print("\n" + "#"*60)
    print("# All tests completed!")
    print("#"*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
