#!/usr/bin/env python3
"""
Direct ContextManager Agent Test Script
Test the ContextManager agent by passing prompts directly.

Usage:
    python test_context_manager.py "I'm a YouTuber focused on tech reviews"
    python test_context_manager.py "retrieve my profile information"
    python test_context_manager.py "list all my context files"

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

from agents.context_manager import ContextManagerAgent
from models.openai_client import OpenAIClient
from config.settings import settings
from utils.logger import logger
from storage.database import db_manager


async def test_context_manager(prompt: str, user_id: str = "test-user-123", conversation_id: str = "test-conv-123"):
    """
    Test the ContextManager agent with a given prompt
    
    Args:
        prompt: User prompt to test
        user_id: Test user ID (default: test-user-123)
        conversation_id: Test conversation ID (default: test-conv-123)
    """
    print(f"\n{'='*80}")
    print(f"Testing ContextManager Agent")
    print(f"{'='*80}")
    print(f"Prompt: {prompt}")
    print(f"User ID: {user_id}")
    print(f"Conversation ID: {conversation_id}")
    print(f"{'='*80}\n")
    
    try:
        # Database connection is auto-initialized in DatabaseManager.__init__
        print("🔌 Database connection ready...")
        print("✅ Database connected\n")
        
        # Initialize OpenAI client
        print("🤖 Initializing OpenAI client...")
        model_client = OpenAIClient(
            model="gpt-5",  # Using gpt-4o-mini for faster/cheaper testing
            metadata={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "test_script": "true"
            }
        )
        print("✅ OpenAI client initialized\n")
        
        # Initialize ContextManager agent
        print("📝 Initializing ContextManager agent...")
        context_manager = ContextManagerAgent(model_client)
        print("✅ ContextManager agent initialized\n")
        
        # Prepare user context
        user_context = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "session_id": "test-session-123"
        }

        logger.info(f"Starting test with prompt: '{prompt}' for user_id: {user_id}, conversation_id: {conversation_id}")
        
        # Process the message
        print(f"💬 Processing prompt: '{prompt}'\n")
        print("⏳ Waiting for agent response...\n")
        
        response = await context_manager.process_message(
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
        metadata = context_manager.get_metadata()
        print(f"📊 AGENT METADATA:")
        print(f"  - Total messages: {metadata['total_messages']}")
        print(f"  - Tool calls: {metadata['tool_calls_count']}")
        print(f"  - Files created: {metadata['files_created']}")
        print(f"  - Files updated: {metadata['files_updated']}")
        print(f"  - Files read: {metadata['files_read']}")
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
║                   ContextManager Agent Test Script                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python test_context_manager.py "<prompt>" [user_id] [conversation_id]

Arguments:
    prompt            : Required. The prompt to test
    user_id          : Optional. User ID (default: test-user-123)
    conversation_id  : Optional. Conversation ID (default: test-conv-123)

Examples:
    # Save user context
    python test_context_manager.py "I'm a content creator focused on cooking videos"
    python test_context_manager.py "My main platform is YouTube and I post weekly"
    python test_context_manager.py "I want to grow my audience to 100k subscribers"
    
    # Retrieve context
    python test_context_manager.py "retrieve my profile information"
    python test_context_manager.py "get my goals"
    python test_context_manager.py "show me the index file"
    
    # List context files
    python test_context_manager.py "list all my context files"
    python test_context_manager.py "what information do you have about me?"
    
    # Request additional context
    python test_context_manager.py "ask me about my content schedule"
    python test_context_manager.py "what's my target audience?"
    
    # Complex interactions
    python test_context_manager.py "I'm planning a series about healthy recipes. My target audience is millennials interested in quick meals"
    python test_context_manager.py "Update my goals: I want to hit 50k subscribers by Q2"

Environment Variables Required:
    DATABASE_URL      : PostgreSQL connection (e.g., postgresql://user:pass@localhost:5432/dbname)
    OPENAI_API_KEY    : Your OpenAI API key
    INTERNAL_API_SECRET: Any secret string (e.g., 'test-secret')

Environment Setup:
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/content_planner"
    export OPENAI_API_KEY="sk-..."
    export INTERNAL_API_SECRET="test-secret-123"

Or use Docker:
    docker exec -it content-planner-python python test_context_manager.py "your prompt here"
    
Notes:
    - Context files are stored in agent_context/{user_id}/ directory
    - The agent creates structured markdown files (INDEX.md, profile.md, goals.md, etc.)
    - Each user has their own context directory
    - Use 'list' action to see what files exist for a user
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

    logger.info(f"Test script started with prompt: {prompt}, user_id: {user_id}")
    

    conversation_id = sys.argv[3] if len(sys.argv) > 3 else "test-conv-123"
    
    # Check environment variables
    required_env_vars = ["DATABASE_URL", "OPENAI_API_KEY", "INTERNAL_API_SECRET"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"\n❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}\n")
        print("Please set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=<value>")
        print("\nRun 'python test_context_manager.py --help' for more information.\n")
        return 1
    
    # Run the test
    return asyncio.run(test_context_manager(prompt, user_id, conversation_id))


if __name__ == "__main__":
    sys.exit(main())
