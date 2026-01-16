"""
Test script for Context Manager Agent
Demonstrates how to use the agent to manage user context files
"""
import asyncio
import os
from models.openai_client import OpenAIClient
from models.anthropic_client import AnthropicClient
from agents.context_manager import ContextManagerAgent
from utils.logger import logger


async def test_context_manager_basic():
    """Test basic context management without tools"""
    print("\n=== Test 1: Basic Context Manager (No Tools) ===\n")
    
    # Initialize with OpenAI client
    openai_client = OpenAIClient(
        api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        model="gpt-3.5-turbo"
    )
    
    agent = ContextManagerAgent(openai_client)
    
    # Simulate information from onboarding agent
    user_info = """
    User completed onboarding:
    - Name: Sarah Johnson
    - Content Type: YouTube videos (tech tutorials)
    - Channel: TechWithSarah (50K subscribers)
    - Goals: Reach 100K subscribers by end of year, monetize through courses
    - Challenges: Inconsistent posting schedule, running out of content ideas
    - Preferences: Prefers batch recording, likes detailed tutorials
    """
    
    user_context = {
        "user_id": "user_sarah_001",
        "email": "sarah@example.com"
    }
    
    try:
        response = await agent.process_message(user_info, user_context)
        print(f"Agent Response: {response}\n")
    except Exception as e:
        print(f"Error: {e}\n")


async def test_context_manager_with_direct_calls():
    """Test context manager with direct file operations"""
    print("\n=== Test 2: Direct Context File Operations ===\n")
    
    from utils.user_context_manager import (
        write_user_context,
        read_user_context,
        list_user_context_files,
        ensure_user_context_dir
    )
    
    user_id = "user_test_001"
    ensure_user_context_dir(user_id)
    
    # Create INDEX.md
    index_content = """# User Context Index

**User ID:** user_test_001  
**Last Updated:** 2026-01-16  

## Quick Overview
- **Name:** John Doe
- **Content Type:** Blog Posts
- **Status:** Active user since onboarding

## Context Files

1. [Profile](profile.md) - Basic user information
2. [Goals](goals.md) - User goals and objectives
3. [Preferences](preferences.md) - Content preferences and workflow
4. [History](history.md) - Conversation and activity history

---
*This index is automatically maintained by the Context Manager Agent*
"""
    
    success = write_user_context(user_id, "INDEX.md", index_content)
    print(f"INDEX.md created: {success}")
    
    # Create profile.md
    profile_content = """# User Profile

## Basic Information
- **Name:** John Doe
- **Email:** john@example.com
- **Joined:** 2026-01-15

## Content Details
- **Platform:** Blog (Medium, Personal Site)
- **Niche:** Technology & Productivity
- **Experience:** 2 years
- **Frequency:** 2-3 posts per week

## Channel Metrics
- **Followers:** 5,000
- **Average Views:** 500 per post
- **Engagement Rate:** 3.5%
"""
    
    success = write_user_context(user_id, "profile.md", profile_content)
    print(f"profile.md created: {success}")
    
    # Create goals.md
    goals_content = """# User Goals

## Primary Goals
1. **Grow audience to 10K followers** (Target: Q3 2026)
2. **Launch online course** (Target: Q4 2026)
3. **Establish newsletter** (Target: Q2 2026)

## Success Metrics
- 20% increase in monthly traffic
- 500+ email subscribers
- 5+ guest posting opportunities

## Long-term Vision
Build a personal brand around productivity and become a recognized voice in the space.
"""
    
    success = write_user_context(user_id, "goals.md", goals_content)
    print(f"goals.md created: {success}")
    
    # List all files
    files = list_user_context_files(user_id)
    print(f"\nAll context files for {user_id}: {files}")
    
    # Read back INDEX.md
    content = read_user_context(user_id, "INDEX.md")
    if content:
        print(f"\nINDEX.md preview (first 200 chars):\n{content[:200]}...")


async def test_context_manager_workflow():
    """Test typical workflow with context manager agent"""
    print("\n=== Test 3: Typical Workflow Simulation ===\n")
    
    # This test simulates how the orchestrator would pass info to context manager
    
    user_id = "user_workflow_001"
    
    # Step 1: User completes onboarding
    onboarding_summary = """
    Onboarding completed for user_workflow_001:
    - Content creator focusing on TikTok videos about fitness
    - Name: Mike Chen
    - Goals: Build personal training business through social media
    - Posts 5x per week, struggles with content planning
    - Target audience: Young adults (18-30) interested in home workouts
    """
    
    print(f"Step 1: Processing onboarding data...")
    print(f"Summary: {onboarding_summary[:100]}...\n")
    
    # Step 2: User has planning conversation
    planning_summary = """
    Planning session with user_workflow_001:
    - Created 4-week content calendar
    - Focus areas: bodyweight exercises, nutrition tips, motivation
    - Decided on content pillars: Workout tutorials (3x/week), 
      Quick tips (1x/week), Transformation stories (1x/week)
    - Wants to batch-record on weekends
    """
    
    print(f"Step 2: Processing planning data...")
    print(f"Summary: {planning_summary[:100]}...\n")
    
    print("✓ Context manager would organize this into:")
    print("  - INDEX.md (overview + links)")
    print("  - profile.md (Mike Chen, TikTok, fitness)")
    print("  - goals.md (build personal training business)")
    print("  - content_strategy.md (content pillars, posting schedule)")
    print("  - audience.md (young adults 18-30, home workouts)")
    print("  - preferences.md (batch recording on weekends)")
    print("  - history.md (onboarding + planning session timestamps)\n")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Context Manager Agent Test Suite")
    print("=" * 60)
    
    # Run tests
    await test_context_manager_basic()
    await test_context_manager_with_direct_calls()
    await test_context_manager_workflow()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nContext files are stored in: python-agents/agent_context/{userId}/")
    print("Check the agent_context directory to see created files.\n")


if __name__ == "__main__":
    asyncio.run(main())
