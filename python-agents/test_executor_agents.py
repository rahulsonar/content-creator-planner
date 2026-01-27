#!/usr/bin/env python3
"""
Test script for Executor Agent and break_into_subtasks functionality

This demonstrates:
1. How the planner can break a complex task into subtasks
2. How executor agents work independently to process subtasks
3. How results are stored and retrieved from Redis
"""
import asyncio
import json
from agents.executor import ExecutorAgent
from agents.planner import PlanningAgent
from models.factory import create_model_client
from storage.redis_client import RedisClient
from config.settings import Settings
from utils.logger import logger


async def test_executor_agent():
    """Test the executor agent with a sample subtask"""
    
    logger.info("=== Testing Executor Agent ===")
    
    # Initialize settings and Redis
    settings = Settings()
    redis_client = RedisClient(settings)
    await redis_client.connect()
    
    try:
        # Create model client for executor
        model = ModelFactory.create_model("gpt-4o-mini")
        
        # Create executor agent
        executor = ExecutorAgent(
            model_client=model,
            redis_client=redis_client,
            executor_id="test_executor_1"
        )
        
        # Define a test subtask
        user_id = "test_user_executor"
        parent_task_id = "parent_test_task"
        subtask_id = "subtask_research"
        
        # Store subtask context in Redis
        subtask_context = {
            "id": subtask_id,
            "description": "Research the top 3 video editing software tools",
            "goal": "Provide a comparison of features and pricing for Adobe Premiere, Final Cut Pro, and DaVinci Resolve",
            "context": {
                "task_type": "research",
                "focus_areas": ["features", "pricing", "ease_of_use"],
                "output_format": "bullet points"
            },
            "parent_task_id": parent_task_id,
            "parent_description": "Create a comprehensive video production workflow"
        }
        
        key = f"subtask:{parent_task_id}:{subtask_id}:{user_id}"
        await redis_client.set(key, json.dumps(subtask_context), ex=3600)
        logger.info(f"Stored test subtask context: {key}")
        
        # Execute the subtask
        result = await executor.execute_subtask(
            subtask_id=subtask_id,
            parent_task_id=parent_task_id,
            user_id=user_id
        )
        
        # Display results
        logger.info("=== Execution Result ===")
        logger.info(f"Success: {result.get('success')}")
        logger.info(f"Subtask ID: {result.get('subtask_id')}")
        logger.info(f"Executor ID: {result.get('executor_id')}")
        if result.get('success'):
            logger.info(f"Output:\n{result.get('output')}")
        else:
            logger.error(f"Error: {result.get('error')}")
        
        # Check status in Redis
        status_key = f"subtask_status:{parent_task_id}:{subtask_id}:{user_id}"
        status_json = await redis_client.get(status_key)
        if status_json:
            status = json.loads(status_json)
            logger.info(f"Status in Redis: {status.get('status')}")
        
        # Get executor metadata
        metadata = executor.get_metadata()
        logger.info(f"Executor Metadata: {json.dumps(metadata, indent=2)}")
        
    finally:
        await redis_client.disconnect()


async def test_planner_break_into_subtasks():
    """Test the planner's ability to break tasks into subtasks and delegate to executors"""
    
    logger.info("\n=== Testing Planner Break Into Subtasks ===")
    
    # Initialize settings and Redis
    settings = Settings()
    redis_client = RedisClient(settings)
    await redis_client.connect()
    
    try:
        # Create model client for planner
        model = create_model_client("gpt-4o")
        
        # Create planner agent
        planner = PlanningAgent(
            model_client=model,
            enable_openai_tools=True,
            redis_client=redis_client
        )
        
        # Simulate a tool call to break_into_subtasks
        user_id = "test_user_planner"
        planner._current_user_id = user_id
        planner._current_conversation_id = "test_conv"
        
        tool_input = {
            "parent_task_description": "Create a complete YouTube video production workflow",
            "subtasks": [
                {
                    "id": "script_research",
                    "description": "Research trending topics and keywords for YouTube content",
                    "goal": "Identify 5 trending topics with high search volume and low competition",
                    "context": {
                        "task_type": "research",
                        "niche": "content creation tutorials",
                        "target_audience": "beginner creators"
                    }
                },
                {
                    "id": "equipment_list",
                    "description": "Create a list of essential video production equipment",
                    "goal": "Provide a budget-friendly equipment list with alternatives",
                    "context": {
                        "task_type": "planning",
                        "budget_range": "$500-$2000",
                        "quality_level": "beginner to intermediate"
                    }
                },
                {
                    "id": "editing_workflow",
                    "description": "Design a step-by-step video editing workflow",
                    "goal": "Create a workflow from raw footage to final export",
                    "context": {
                        "task_type": "process_design",
                        "software": "DaVinci Resolve",
                        "video_length": "10-15 minutes"
                    }
                }
            ],
            "wait_for_completion": True
        }
        
        # Execute the break_into_subtasks tool
        result = await planner._execute_break_into_subtasks(
            tool_input=tool_input,
            user_id=user_id,
            conversation_id="test_conv"
        )
        
        logger.info("=== Break Into Subtasks Result ===")
        logger.info(result)
        
        # Check what's stored in Redis
        parent_task_id = None
        # Extract parent_task_id from result or find it in Redis
        # For demonstration, we'll search for keys
        logger.info("\n=== Checking Redis for Subtask Data ===")
        
        # Get planner metadata
        metadata = planner.get_metadata()
        logger.info(f"\nPlanner Metadata: {json.dumps({k: v for k, v in metadata.items() if k != 'model_name'}, indent=2)}")
        
    finally:
        await redis_client.disconnect()


async def test_parallel_execution():
    """Test multiple executor agents running in parallel"""
    
    logger.info("\n=== Testing Parallel Executor Agents ===")
    
    settings = Settings()
    redis_client = RedisClient(settings)
    await redis_client.connect()
    
    try:
        user_id = "test_user_parallel"
        parent_task_id = "parent_parallel_test"
        
        # Define multiple subtasks
        subtasks_data = [
            {
                "id": "research_tools",
                "description": "Research content creation tools",
                "goal": "List top 5 tools for each category: video editing, graphics, scheduling"
            },
            {
                "id": "analyze_competitors",
                "description": "Analyze top 3 competitors in content creation niche",
                "goal": "Identify their strengths, weaknesses, and content strategies"
            },
            {
                "id": "create_timeline",
                "description": "Create a 30-day content production timeline",
                "goal": "Break down daily tasks for consistent content output"
            }
        ]
        
        # Store subtask contexts in Redis
        for subtask_data in subtasks_data:
            context = {
                **subtask_data,
                "context": {"task_type": "general"},
                "parent_task_id": parent_task_id,
                "parent_description": "Build a complete content creation system"
            }
            key = f"subtask:{parent_task_id}:{subtask_data['id']}:{user_id}"
            await redis_client.set(key, json.dumps(context), ex=3600)
        
        logger.info(f"Stored {len(subtasks_data)} subtask contexts")
        
        # Create executors and launch parallel execution
        executor_tasks = []
        
        for subtask_data in subtasks_data:
            model = create_model_client("gpt-4o-mini")
            executor = ExecutorAgent(
                model_client=model,
                redis_client=redis_client,
                executor_id=f"executor_{subtask_data['id']}"
            )
            
            task = executor.execute_subtask(
                subtask_id=subtask_data['id'],
                parent_task_id=parent_task_id,
                user_id=user_id
            )
            executor_tasks.append(task)
        
        logger.info(f"Launched {len(executor_tasks)} executors in parallel")
        
        # Wait for all to complete
        results = await asyncio.gather(*executor_tasks, return_exceptions=True)
        
        # Display results
        logger.info("\n=== Parallel Execution Results ===")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed: {result}")
            elif isinstance(result, dict):
                logger.info(f"\nSubtask: {result.get('subtask_id')}")
                logger.info(f"Success: {result.get('success')}")
                if result.get('success'):
                    logger.info(f"Output preview: {result.get('output', '')[:200]}...")
        
    finally:
        await redis_client.disconnect()


async def main():
    """Run all tests"""
    
    print("=" * 80)
    print("EXECUTOR AGENT TEST SUITE")
    print("=" * 80)
    
    # Test 1: Single executor agent
    await test_executor_agent()
    
    # Test 2: Planner breaking into subtasks
    await test_planner_break_into_subtasks()
    
    # Test 3: Parallel execution
    await test_parallel_execution()
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
