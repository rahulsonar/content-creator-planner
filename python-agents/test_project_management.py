"""
Test script for project management tools in task manager agent
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.task_manager import UserTaskManagerAgent
from models.factory import create_model_client
from config.settings import settings
from utils.logger import logger


async def test_project_management():
    """Test project management functionality"""
    
    print("\n=== Testing Task Manager Project Tools ===\n")
    
    # Initialize model client
    model_client = create_model_client(
        model=settings.TASK_MANAGER_MODEL,
        metadata={
            "test_name": "project_management",
            "user_id": "admin-user"
        }
    )
    
    # Initialize task manager agent
    agent = UserTaskManagerAgent(model_client)
    
    # Set up user context - use actual seeded admin user
    # Default user from seed.ts: admin@example.com
    # We need to get the actual user ID from the database
    import asyncpg
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        admin_user = await conn.fetchrow('SELECT id, email FROM "User" WHERE email = $1', 'admin@example.com')
        if not admin_user:
            print("⚠️  Admin user not found. Creating test user...")
            # Create a test user
            test_user_id = await conn.fetchval(
                'INSERT INTO "User" (id, email, password, name, "createdAt", "updatedAt") '
                'VALUES (gen_random_uuid()::text, $1, $2, $3, NOW(), NOW()) RETURNING id',
                'test@example.com',
                '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ajS4/jPIR/i.',  # hashed 'password'
                'Test User'
            )
            user_id = test_user_id
            print(f"✓ Created test user: {test_user_id}")
        else:
            user_id = admin_user['id']
            print(f"✓ Using existing admin user: {admin_user['email']} (ID: {user_id})")
    finally:
        await conn.close()
    
    user_context = {
        "user_id": user_id,
        "conversation_id": "test-conv-projects",
        "session_id": "test-session-123"
    }
    
    # Test 1: Create a project
    print("Test 1: Creating a new project...")
    response1 = await agent.process_message(
        "Create a new project called 'YouTube Tech Review Channel' for my tech review videos. "
        "Use status ACTIVE, color #FF5733, and icon 📹. Add tags: youtube, tech, reviews",
        user_context=user_context
    )
    print(f"Response: {response1}\n")
    
    # Test 2: List all projects
    print("Test 2: Listing all projects...")
    response2 = await agent.process_message(
        "Show me all my projects",
        user_context=user_context
    )
    print(f"Response: {response2}\n")
    
    # Test 3: List projects by status
    print("Test 3: Listing ACTIVE projects...")
    response3 = await agent.process_message(
        "List all my active projects",
        user_context=user_context
    )
    print(f"Response: {response3}\n")
    
    # Test 4: Create multiple projects
    print("Test 4: Creating multiple projects...")
    response4 = await agent.process_message(
        "Create two projects: "
        "1) 'Podcast Series' for my podcast with icon 🎙️ and tags podcast, audio "
        "2) 'Blog Platform' for blogging with icon ✍️ and tags blog, writing",
        user_context=user_context
    )
    print(f"Response: {response4}\n")
    
    # Test 5: View specific project (will need project ID from previous responses)
    print("Test 5: Viewing project details...")
    response5 = await agent.process_message(
        "Show me details about the 'YouTube Tech Review Channel' project",
        user_context=user_context
    )
    print(f"Response: {response5}\n")
    
    print("=== Project Management Tests Complete ===\n")
    print(f"Agent Metadata: {agent.get_metadata_summary()}")


if __name__ == "__main__":
    asyncio.run(test_project_management())
