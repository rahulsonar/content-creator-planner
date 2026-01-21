"""
Example: Using Anthropic Claude Models
Demonstrates how to use the Anthropic client in agents
"""
from models import create_model_client, get_model_name
from config.settings import settings


async def example_claude_usage():
    """Example of using Claude Sonnet 4.5"""
    
    # Create Claude client using factory
    client = create_model_client("claude-sonnet-4.5", metadata={
        "user_id": "example-123",
        "session": "demo"
    })
    
    # Simple completion
    messages = [
        {"role": "system", "content": "You are a helpful assistant for content creators."},
        {"role": "user", "content": "What are the top 3 tips for creating engaging YouTube content?"}
    ]
    
    response = await client.generate_completion(messages)
    print("Response:", response)
    
    # Streaming completion
    print("\nStreaming response:")
    async for chunk in client.stream_completion(messages):
        print(chunk, end="", flush=True)
    print()


async def example_with_tools():
    """Example of using Claude with tool calling"""
    
    client = create_model_client("claude-sonnet-4.5")
    
    # Define tools (OpenAI format - will be converted automatically)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_video_stats",
                "description": "Get statistics for a YouTube video",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {
                            "type": "string",
                            "description": "YouTube video ID"
                        }
                    },
                    "required": ["video_id"]
                }
            }
        }
    ]
    
    messages = [
        {"role": "user", "content": "Get stats for video abc123"}
    ]
    
    response = await client.generate_completion(messages, tools=tools)
    
    # Check if tool was called
    if hasattr(response, 'stop_reason') and response.stop_reason == "tool_use":
        print("Tool called:", response.content)
    else:
        print("Response:", response)


async def example_agent_with_claude():
    """Example of initializing agents with Claude models"""
    from agents.planner import PlannerAgent
    from agents.task_manager import TaskManagerAgent
    
    # Create clients for different agents
    planner_client = create_model_client("claude-opus-4")  # More powerful for planning
    task_client = create_model_client("claude-sonnet-4.5")  # Efficient for task management
    
    # Initialize agents with Claude clients
    planner = PlannerAgent(planner_client)
    task_manager = TaskManagerAgent(task_client)
    
    # Use agents normally
    response = await planner.process_message(
        "Help me plan a video series about AI tools",
        user_context={"user_id": "user123"}
    )
    print("Planner response:", response)


# Configuration examples for .env file
"""
# Add to your .env file:

# Anthropic API Key (required for Claude models)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Agent Model Configuration (can use Claude models)
PLANNER_MODEL=claude-opus-4
TASK_MANAGER_MODEL=claude-sonnet-4.5
CONTEXT_MANAGER_MODEL=claude-sonnet-4.5

# Or keep using OpenAI
PLANNER_MODEL=gpt-4
TASK_MANAGER_MODEL=gpt-4
CONTEXT_MANAGER_MODEL=gpt-4
"""
