"""
Test OpenAI function calling with planner agent
"""
import asyncio
from agents.planner import PlanningAgent
from models.openai_client import OpenAIClient
from utils.logger import logger


async def test_openai_planner():
    """Test planner agent with OpenAI function calling"""
    
    print("\n" + "="*60)
    print("Testing Planner Agent with OpenAI Function Calling")
    print("="*60 + "\n")
    
    # Initialize OpenAI client and agent
    client = OpenAIClient(model="gpt-4")
    planner = PlanningAgent(client)
    
    # Simulate conversation
    print("User: I want to start a YouTube channel about cooking")
    response1 = await planner.process_message(
        "I want to start a YouTube channel about cooking"
    )
    print(f"\nAgent: {response1}\n")
    
    print("-"*60)
    print("\nUser: First time, quick recipes for busy people. 5-10 hours/week.")
    response2 = await planner.process_message(
        "First time, quick recipes for busy people. 5-10 hours/week."
    )
    print(f"\nAgent: {response2}\n")
    
    print("-"*60)
    print("\nUser: yes please")
    response3 = await planner.process_message("yes please")
    print(f"\nAgent: {response3}\n")
    
    print("-"*60)
    print("\nUser: yes go ahead")
    response4 = await planner.process_message("yes go ahead")
    print(f"\nAgent: {response4}\n")
    
    print("\n" + "="*60)
    print("Test completed! Check if tasks were created.")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_openai_planner())
