#!/usr/bin/env python3
"""
Direct TaskManager Agent Test Script
Test the TaskManager agent by passing prompts directly.

Usage:
    python test_task_manager.py "create a task for video editing"
    python test_task_manager.py "search for tasks about YouTube"
    python test_task_manager.py "update task 123 to completed"

Environment Requirements:
    - DATABASE_URL: PostgreSQL connection string
    - OPENAI_API_KEY: OpenAI API key
    - INTERNAL_API_SECRET: Any secret string
"""
import sys
import asyncio
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.task_manager import UserTaskManagerAgent
from models.openai_client import OpenAIClient
from config.settings import settings
from utils.logger import logger
from storage.database import db_manager


async def test_task_manager(prompt: str, user_id: str = "test-user-123", conversation_id: str = "test-conv-123"):
    """
    Test the TaskManager agent with a given prompt
    
    Args:
        prompt: User prompt to test
        user_id: Test user ID (default: test-user-123)
        conversation_id: Test conversation ID (default: test-conv-123)
    """
    print(f"\n{'='*80}")
    print(f"Testing TaskManager Agent")
    print(f"{'='*80}")
    print(f"Prompt: {prompt}")
    print(f"User ID: {user_id}")
    print(f"Conversation ID: {conversation_id}")
    print(f"{'='*80}\n")
    
    try:
        # Database connection is auto-initialized in DatabaseManager.__init__
        print("🔌 Database connection ready...")
        print("✅ Database connected\n")
        
        # Initialize Claude client
        print("🤖 Initializing Claude client...")
        from models import create_model_client
        model_client = create_model_client(
            "claude-sonnet-4-5-20250929",
            metadata={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "test_script": "true"
            }
        )
        print("✅ Claude client initialized\n")
        
        # Initialize TaskManager agent
        print("🎯 Initializing TaskManager agent...")
        task_manager = UserTaskManagerAgent(model_client)
        print("✅ TaskManager agent initialized\n")
        
        # Prepare user context
        user_context = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "session_id": "test-session-123"
        }
        
        # Process the message
        print(f"💬 Processing prompt: '{prompt}'\n")
        print("⏳ Waiting for agent response...\n")
        
        response = await task_manager.process_message(
            user_message=prompt,
            user_context=user_context
        )
        
        # Display results
        print(f"\n{'='*80}")
        print("🎉 AGENT RESPONSE")
        print(f"{'='*80}")
        print(response)
        print(f"{'='*80}\n")
        
        # Display metadata
        metadata = task_manager.get_metadata()
        print(f"📊 AGENT METADATA:")
        print(f"  - Total messages: {metadata['total_messages']}")
        print(f"  - Tool calls: {metadata['tool_calls_count']}")
        print(f"  - Tasks created: {metadata['tasks_created']}")
        print(f"  - Tasks updated: {metadata['tasks_updated']}")
        print(f"  - Tasks searched: {metadata['tasks_searched']}")
        print(f"  - Model: {metadata['model_name']}")
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    finally:
        # Close database connection
        await db_manager.close()
        print("🔌 Database connection closed")
    
    return 0


def print_usage():
    """Print usage instructions"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TaskManager Agent Test Script                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python test_task_manager.py "<prompt>" [user_id] [conversation_id]

Arguments:
    prompt            : Required. The prompt to test
    user_id          : Optional. User ID (default: test-user-123)
    conversation_id  : Optional. Conversation ID (default: test-conv-123)

Examples:
    # Create tasks
    python test_task_manager.py "create a task for editing a YouTube video about Python"
    python test_task_manager.py "I need to plan content for next week"
    
    # Search tasks
    python test_task_manager.py "search for all video editing tasks"
    python test_task_manager.py "find tasks with high priority"
    python test_task_manager.py "show me all tasks about YouTube"
    
    # Update tasks (requires task ID from previous searches)
    python test_task_manager.py "mark task cm123abc as completed"
    python test_task_manager.py "update task cm456def to in progress"
    python test_task_manager.py "change priority of task cm789ghi to urgent"
    
    # Complex requests
    python test_task_manager.py "create 3 tasks for launching a podcast series"
    python test_task_manager.py "find incomplete tasks and show their status"

Environment Variables Required:
    DATABASE_URL      : PostgreSQL connection (e.g., postgresql://user:pass@localhost:5432/dbname)
    OPENAI_API_KEY    : Your OpenAI API key
    INTERNAL_API_SECRET: Any secret string (e.g., 'test-secret')

Environment Setup:
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/content_planner"
    export OPENAI_API_KEY="sk-..."
    export INTERNAL_API_SECRET="test-secret-123"

Or use Docker:
    docker exec -it python-agents python test_task_manager.py "your prompt here"
    """)


def main():
    """Main entry point"""
    # Check for help flag
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print_usage()
        return 0
    
    # Get arguments
    prompt = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else "test-user-123"
    conversation_id = sys.argv[3] if len(sys.argv) > 3 else "test-conv-123"
    
    # Check environment variables
    required_env_vars = ["DATABASE_URL", "OPENAI_API_KEY", "INTERNAL_API_SECRET"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"\n❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}\n")
        print("Please set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=<value>")
        print("\nRun 'python test_task_manager.py --help' for more information.\n")
        return 1
    
    # Run the test
    return asyncio.run(test_task_manager(prompt, user_id, conversation_id))


if __name__ == "__main__":
    sys.exit(main())
