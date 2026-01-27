# Executor Agent - Child Agent for Parallel Task Processing

## Overview

The **Executor Agent** is a child agent that can be spawned by the Planner to handle individual subtasks independently. This enables the Planner to break complex tasks into smaller chunks and process them in parallel using multiple executor instances.

## Key Features

1. **Independent Execution**: Each executor works independently with its own context
2. **Redis-Based Coordination**: Task context and results are stored in Redis
3. **Parallel Processing**: Multiple executors can run simultaneously
4. **Status Tracking**: Real-time status updates stored in Redis
5. **Result Aggregation**: Completed subtask outputs are collected and summarized

## Architecture

```
┌─────────────────┐
│  Planner Agent  │
└────────┬────────┘
         │
         │ break_into_subtasks()
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
    │Executor1│   │Executor2│   │Executor3│   │ExecutorN│
    └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
         │             │             │             │
         └─────────────┴──────┬──────┴─────────────┘
                              ▼
                         ┌─────────┐
                         │  Redis  │ (Context & Results)
                         └─────────┘
```

## How It Works

### 1. Planner Breaks Task into Subtasks

The Planner uses the `break_into_subtasks` tool to:
- Define the parent task description
- Create a list of independent subtasks with IDs, descriptions, goals, and context
- Store each subtask's context in Redis
- Spawn executor agents for each subtask

### 2. Executors Process Subtasks

Each executor:
- Fetches its assigned subtask context from Redis
- Updates status to "in_progress"
- Processes the subtask using the LLM
- Stores the output in Redis
- Updates status to "completed" or "failed"

### 3. Results Aggregation

The Planner:
- Waits for all executors to complete (if `wait_for_completion: true`)
- Collects outputs from Redis
- Generates a summary report
- Stores aggregated results for future retrieval

## Usage Example

### Using the Tool Directly in Planner

```python
# The planner can invoke this via tool call
{
    "name": "break_into_subtasks",
    "arguments": {
        "parent_task_description": "Create a comprehensive video production guide",
        "subtasks": [
            {
                "id": "research_equipment",
                "description": "Research professional video equipment",
                "goal": "List cameras, microphones, and lighting under $3000",
                "context": {
                    "budget": "$3000",
                    "quality": "professional"
                }
            },
            {
                "id": "script_template",
                "description": "Create a reusable script template",
                "goal": "Design a template with intro, main points, CTA",
                "context": {
                    "video_length": "10-15 minutes",
                    "style": "educational"
                }
            },
            {
                "id": "editing_checklist",
                "description": "Build a post-production checklist",
                "goal": "Step-by-step checklist from import to export",
                "context": {
                    "software": "DaVinci Resolve",
                    "output_format": "1080p MP4"
                }
            }
        ],
        "wait_for_completion": true
    }
}
```

### Programmatic Usage

```python
from agents.executor import ExecutorAgent
from models.factory import ModelFactory
from storage.redis_client import RedisClient
import asyncio
import json

async def example():
    # Setup
    redis_client = RedisClient(settings)
    await redis_client.connect()
    
    # Define subtask context
    user_id = "user123"
    parent_task_id = "video_guide_001"
    subtask_id = "research_equipment"
    
    subtask_context = {
        "id": subtask_id,
        "description": "Research professional video equipment",
        "goal": "List cameras, microphones, and lighting under $3000",
        "context": {
            "budget": "$3000",
            "quality": "professional"
        },
        "parent_task_id": parent_task_id
    }
    
    # Store in Redis
    key = f"subtask:{parent_task_id}:{subtask_id}:{user_id}"
    await redis_client.set(key, json.dumps(subtask_context), ex=3600)
    
    # Create executor
    model = ModelFactory.create_model("gpt-4o-mini")
    executor = ExecutorAgent(
        model_client=model,
        redis_client=redis_client,
        executor_id="executor_001"
    )
    
    # Execute subtask
    result = await executor.execute_subtask(
        subtask_id=subtask_id,
        parent_task_id=parent_task_id,
        user_id=user_id
    )
    
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
```

## Redis Key Structure

### Subtask Context
```
Key: subtask:{parent_task_id}:{subtask_id}:{user_id}
TTL: 3600 seconds (1 hour)
Value: JSON object with task details
```

### Subtask Status
```
Key: subtask_status:{parent_task_id}:{subtask_id}:{user_id}
TTL: 3600 seconds (1 hour)
Value: {
    "subtask_id": "...",
    "parent_task_id": "...",
    "status": "pending|in_progress|completed|failed",
    "executor_id": "...",
    "updated_at": "ISO timestamp",
    "result": "output or error message"
}
```

### Subtask Output
```
Key: subtask_output:{parent_task_id}:{subtask_id}:{user_id}
TTL: 3600 seconds (1 hour)
Value: {
    "subtask_id": "...",
    "parent_task_id": "...",
    "executor_id": "...",
    "output": "detailed output",
    "completed_at": "ISO timestamp"
}
```

### Aggregated Results
```
Key: subtask_results:{parent_task_id}:{user_id}
TTL: 7200 seconds (2 hours)
Value: {
    "parent_task_id": "...",
    "parent_description": "...",
    "total_subtasks": 3,
    "completed": 3,
    "failed": 0,
    "results": [...],
    "completed_at": "ISO timestamp"
}
```

## Testing

Run the test suite to see the executor agents in action:

```bash
# Inside Docker container
docker exec -it content-planner-app python test_executor_agents.py

# Or if running locally
python python-agents/test_executor_agents.py
```

The test suite includes:
1. **Single Executor Test**: Tests one executor processing a subtask
2. **Planner Integration Test**: Tests the planner breaking tasks into subtasks
3. **Parallel Execution Test**: Tests multiple executors running simultaneously

## Benefits

### For Complex Tasks
- Break down large tasks into manageable pieces
- Process independent subtasks in parallel
- Reduce overall completion time

### For the Planner
- Delegate specialized work to child agents
- Focus on orchestration and result synthesis
- Better resource utilization

### For Users
- Faster task completion through parallelization
- More detailed outputs for each subtask
- Better progress tracking

## Best Practices

1. **Independent Subtasks**: Ensure subtasks don't depend on each other's outputs
2. **Clear Goals**: Define specific, measurable goals for each subtask
3. **Context Sharing**: Provide all necessary context in the subtask definition
4. **Reasonable TTL**: Adjust Redis TTL based on expected completion time
5. **Error Handling**: Check result status and handle failures gracefully

## Configuration

### Model Selection
Executors can use different models than the planner:
- Planner: GPT-4 (for complex reasoning and orchestration)
- Executors: GPT-4o-mini (for cost-effective subtask execution)

### Timeout Settings
Control wait behavior:
- `wait_for_completion: true` - Blocks until all subtasks finish
- `wait_for_completion: false` - Returns immediately, subtasks run in background

### Parallelism
No hard limit on concurrent executors, but consider:
- API rate limits
- Redis connection pool size
- Server resources

## Troubleshooting

### Subtasks Not Starting
- Check Redis connection
- Verify subtask context is stored correctly
- Check executor initialization

### Executors Timing Out
- Increase task complexity appropriately
- Check LLM API availability
- Review subtask goal clarity

### Results Not Found
- Verify TTL hasn't expired
- Check Redis key naming
- Ensure executor completed successfully

## Future Enhancements

- [ ] Priority-based execution
- [ ] Dependent subtask chains
- [ ] Dynamic executor pool scaling
- [ ] Result streaming for long-running tasks
- [ ] Executor specialization (e.g., research-only, writing-only)
- [ ] Retry logic for failed subtasks
- [ ] Progress callbacks during execution
