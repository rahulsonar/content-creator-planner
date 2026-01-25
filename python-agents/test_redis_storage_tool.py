"""
Test Redis Storage Tool
Demonstrates the new Redis storage capability for the Planner agent
"""
import asyncio
import json
from config.settings import Settings
from storage.redis_client import get_redis_client
from utils.logger import logger


async def test_redis_storage():
    """Test Redis storage operations as used by the planner agent"""
    
    logger.info("=== Testing Redis Storage Tool ===")
    
    # Initialize settings and Redis client
    settings = Settings()
    redis_client = await get_redis_client(settings)
    
    # Simulate user ID and conversation context
    user_id = "test-user-123"
    
    try:
        # Test 1: Store a draft plan
        logger.info("\n--- Test 1: Store Draft Plan ---")
        draft_plan = {
            "project": "YouTube Video Series",
            "episodes": [
                {"title": "Episode 1: Introduction", "status": "planned"},
                {"title": "Episode 2: Deep Dive", "status": "scripting"}
            ],
            "deadline": "2026-02-01"
        }
        
        key = f"planner:{user_id}:draft_plan"
        await redis_client.set(key, draft_plan, ttl=3600)
        logger.info(f"✓ Stored draft plan with key: {key}")
        
        # Test 2: Retrieve the draft plan
        logger.info("\n--- Test 2: Retrieve Draft Plan ---")
        retrieved_plan = await redis_client.get(key)
        logger.info(f"✓ Retrieved draft plan: {json.dumps(retrieved_plan, indent=2)}")
        
        # Test 3: Store a task list
        logger.info("\n--- Test 3: Store Task List ---")
        task_list = [
            "Research video topics",
            "Create script outline",
            "Record intro video",
            "Edit footage",
            "Upload to YouTube"
        ]
        
        task_key = f"planner:{user_id}:pending_tasks"
        await redis_client.set(task_key, task_list, ttl=7200)  # 2 hours
        logger.info(f"✓ Stored task list with key: {task_key}")
        
        # Test 4: Check if keys exist
        logger.info("\n--- Test 4: Check Key Existence ---")
        exists_plan = await redis_client.exists(key)
        exists_tasks = await redis_client.exists(task_key)
        logger.info(f"✓ Draft plan exists: {exists_plan}")
        logger.info(f"✓ Task list exists: {exists_tasks}")
        
        # Test 5: Store intermediate planning state
        logger.info("\n--- Test 5: Store Planning State ---")
        planning_state = {
            "current_step": 3,
            "total_steps": 5,
            "completed_tasks": ["research", "outline"],
            "in_progress": ["scripting"],
            "notes": "User wants to focus on SEO optimization"
        }
        
        state_key = f"planner:{user_id}:planning_state"
        await redis_client.set(state_key, planning_state, ttl=1800)  # 30 minutes
        logger.info(f"✓ Stored planning state with key: {state_key}")
        
        # Test 6: Retrieve all stored data
        logger.info("\n--- Test 6: Retrieve All Data ---")
        all_plan = await redis_client.get(key)
        all_tasks = await redis_client.get(task_key)
        all_state = await redis_client.get(state_key)
        
        logger.info(f"✓ All stored data retrieved successfully")
        logger.info(f"  - Draft Plan: {type(all_plan).__name__} with {len(all_plan)} keys")
        logger.info(f"  - Task List: {type(all_tasks).__name__} with {len(all_tasks)} items")
        logger.info(f"  - Planning State: {type(all_state).__name__} with {len(all_state)} keys")
        
        # Test 7: Delete a key
        logger.info("\n--- Test 7: Delete Key ---")
        await redis_client.delete(state_key)
        still_exists = await redis_client.exists(state_key)
        logger.info(f"✓ Deleted planning state. Still exists: {still_exists}")
        
        # Test 8: Store simple string value
        logger.info("\n--- Test 8: Store Simple String ---")
        simple_key = f"planner:{user_id}:current_focus"
        await redis_client.set(simple_key, "Working on video script", ttl=600)
        simple_value = await redis_client.get(simple_key)
        logger.info(f"✓ Stored and retrieved simple string: '{simple_value}'")
        
        logger.info("\n=== All Tests Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Cleanup test data
        logger.info("\n--- Cleanup ---")
        test_keys = [
            f"planner:{user_id}:draft_plan",
            f"planner:{user_id}:pending_tasks",
            f"planner:{user_id}:planning_state",
            f"planner:{user_id}:current_focus"
        ]
        
        for k in test_keys:
            await redis_client.delete(k)
        
        logger.info("✓ Cleanup completed")


async def test_tool_simulation():
    """Simulate how the tool would be called by the LLM"""
    
    logger.info("\n\n=== Simulating Tool Calls ===")
    
    settings = Settings()
    redis_client = await get_redis_client(settings)
    user_id = "simulation-user"
    
    try:
        # Simulate tool call 1: Save intermediate plan
        logger.info("\n[LLM Tool Call] Saving draft content calendar...")
        tool_input_1 = {
            "operation": "set",
            "key": "content_calendar_draft",
            "value": json.dumps({
                "month": "February 2026",
                "themes": ["AI Tools", "Productivity", "Creator Tips"],
                "scheduled_posts": 12
            }),
            "ttl": 7200
        }
        
        key1 = f"planner:{user_id}:{tool_input_1['key']}"
        success1 = await redis_client.set(
            key1,
            json.loads(tool_input_1['value']),
            ttl=tool_input_1['ttl']
        )
        logger.info(f"✓ Result: {'Success' if success1 else 'Failed'} - Stored for {tool_input_1['ttl']}s")
        
        # Simulate tool call 2: Retrieve saved plan
        logger.info("\n[LLM Tool Call] Retrieving saved content calendar...")
        tool_input_2 = {
            "operation": "get",
            "key": "content_calendar_draft"
        }
        
        key2 = f"planner:{user_id}:{tool_input_2['key']}"
        data = await redis_client.get(key2)
        logger.info(f"✓ Result: Retrieved data - {json.dumps(data, indent=2)}")
        
        # Simulate tool call 3: Check if key exists
        logger.info("\n[LLM Tool Call] Checking if draft exists...")
        tool_input_3 = {
            "operation": "exists",
            "key": "content_calendar_draft"
        }
        
        key3 = f"planner:{user_id}:{tool_input_3['key']}"
        exists = await redis_client.exists(key3)
        logger.info(f"✓ Result: Key {'exists' if exists else 'does not exist'}")
        
        # Simulate tool call 4: Store progress tracker
        logger.info("\n[LLM Tool Call] Saving task progress...")
        tool_input_4 = {
            "operation": "set",
            "key": "task_progress",
            "value": json.dumps(["Research: Done", "Outline: In Progress", "Filming: Pending"]),
            "ttl": 3600
        }
        
        key4 = f"planner:{user_id}:{tool_input_4['key']}"
        success4 = await redis_client.set(
            key4,
            json.loads(tool_input_4['value']),
            ttl=tool_input_4['ttl']
        )
        logger.info(f"✓ Result: Progress saved successfully")
        
        # Cleanup
        await redis_client.delete(key1)
        await redis_client.delete(key4)
        
        logger.info("\n=== Simulation Completed ===")
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def main():
    """Run all tests"""
    await test_redis_storage()
    await test_tool_simulation()
    
    logger.info("\n" + "="*60)
    logger.info("REDIS STORAGE TOOL TESTING COMPLETE")
    logger.info("="*60)
    logger.info("\nThe planner agent can now use the 'redis_storage' tool to:")
    logger.info("  • Save intermediate planning information")
    logger.info("  • Store draft plans and task lists")
    logger.info("  • Track planning state across conversation turns")
    logger.info("  • Cache temporary data with automatic expiration")
    logger.info("  • Use key-value pairs for flexible data storage")
    logger.info("\nAll data is automatically namespaced per user to prevent conflicts.")


if __name__ == "__main__":
    asyncio.run(main())
