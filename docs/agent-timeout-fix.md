# Agent Timeout and Orphaned Call Fix

## Problem Description

### Issue
When the planner agent delegated long-running operations to the task manager agent (e.g., closing duplicate tasks), the following problems occurred:

1. **Timeout After 120 Seconds**: Task manager operations taking >120s would timeout
2. **Planner Agent Completed with Null Output**: After timeout, planner would send another tool call, but the follow-up response would return empty/null content
3. **Orphaned Task Manager Processes**: Task manager would remain stuck in IN_PROGRESS status with no tracking
4. **Poor Error Messages**: Timeout errors didn't provide actionable guidance

## Root Cause

1. **120-second timeout too short**: Complex operations like batch task closures need more time
2. **Empty follow-up responses not handled**: When LLM returned null/empty content after timeout, it wasn't caught
3. **No cleanup mechanism**: Orphaned agent calls remained in database indefinitely
4. **Transaction not properly managed**: All updates attempted in single transaction - first error aborted everything

## Solutions Implemented

### 1. Increased Timeout (120s → 300s)
**File**: `python-agents/agents/planner.py` (Line 737)

```python
# Before:
timeout_seconds = 120

# After:
timeout_seconds = 300  # Increased for complex operations
```

### 2. Handle Null/Empty Follow-Up Responses
**File**: `python-agents/agents/planner.py` (Lines 373-388)

Added detection and fallback for empty responses after timeouts:

```python
# Handle null/empty responses (can happen after timeouts)
if not follow_up_text or follow_up_text.strip() == "":
    logger.warning(f"[PLANNER] Empty follow-up response detected")
    has_timeout = any("TOOL TIMEOUT" in str(r) for r in tool_results)
    if has_timeout:
        follow_up_text = (
            "The task management operation is taking longer than expected and may still be processing in the background. "
            "You can check the task list to see if changes have been applied, or try a more specific request. "
            "For large operations, consider breaking them into smaller batches."
        )
    else:
        follow_up_text = "I've completed processing your request. Please let me know if you need anything else."
```

### 3. Improved Timeout Error Messages
**File**: `python-agents/agents/planner.py` (Lines 752-762)

Enhanced error messages with actionable suggestions:

```python
task_result = (
    f"TOOL TIMEOUT: The task management operation did not complete within {timeout_seconds} seconds ({elapsed:.0f}s elapsed). "
    f"The task manager may still be processing your request in the background. "
    f"\n\nSuggested actions:\n"
    f"- Wait a few minutes and check if tasks were updated\n"
    f"- Break your request into smaller, more specific operations\n"
    f"- For bulk operations, process tasks in batches of 5-10 at a time"
)
```

### 4. Orphaned Agent Call Cleanup System

#### New Cleanup Utility
**File**: `python-agents/utils/cleanup_orphaned_agents.py`

Features:
- Finds agent calls stuck in IN_PROGRESS for >30 minutes (configurable)
- Updates them to FAILED status with detailed error messages
- Adds metadata about cleanup reason and timestamp
- Provides statistics about orphaned calls

#### Cleanup Script
**File**: `python-agents/cleanup_orphaned_agents.py`

Command-line tool to manually run cleanup:

```bash
# Run cleanup for calls older than 30 minutes
docker exec -it content-planner-python python /app/cleanup_orphaned_agents.py

# Only show statistics
docker exec -it content-planner-python python /app/cleanup_orphaned_agents.py --stats-only

# Custom age threshold (e.g., 60 minutes)
docker exec -it content-planner-python python /app/cleanup_orphaned_agents.py --max-age 60
```

#### New API Endpoints
**File**: `python-agents/api/routes.py` (Lines 369-416)

```python
# Cleanup orphaned calls
POST /admin/cleanup-orphaned-agents?max_age_minutes=30

# Get statistics (read-only)
POST /admin/orphaned-agents/stats?max_age_minutes=30
```

## Testing

### Cleanup Results
Ran cleanup on 9 orphaned agent calls:
- 5 task_manager agents (ages: 1018.9min, 1016.2min, 1012.9min, 928.7min, 923.1min)
- 3 planner agents (ages: 133.3min, 127.4min, 43.3min)
- 1 task_manager agent (age: 33.4min)

All successfully cleaned up and marked as FAILED.

## Recommendations

### For Users
1. **Break down large operations**: Instead of "close all duplicate tasks", try "close tasks X, Y, Z"
2. **Process in batches**: For bulk operations, work with 5-10 tasks at a time
3. **Check after timeouts**: If operation times out, wait a few minutes and verify if changes were applied

### For Developers
1. **Monitor orphaned calls**: Run cleanup script periodically or set up a cron job
2. **Review timeout thresholds**: If 300s still isn't enough, consider further increases or streaming responses
3. **Add progress indicators**: For long operations, consider WebSocket updates or progress tracking
4. **Implement rate limiting**: Prevent users from triggering too many concurrent long operations

## Future Improvements

1. **Automatic Cleanup Cron**: Add scheduled task to run cleanup every hour
2. **Background Job Queue**: Move long operations to Celery/RQ for proper background processing
3. **Progress Tracking**: Stream progress updates via WebSocket for operations taking >30s
4. **Operation Splitting**: Automatically chunk large operations into smaller batches
5. **Timeout Prediction**: Estimate operation time based on request size and historical data

## Files Modified

1. `python-agents/agents/planner.py` - Timeout increase, null handling, better errors
2. `python-agents/utils/cleanup_orphaned_agents.py` - New cleanup utility
3. `python-agents/cleanup_orphaned_agents.py` - New CLI script
4. `python-agents/api/routes.py` - New admin endpoints

## Configuration

All timeout values are currently hardcoded. Consider moving to environment variables:

```bash
# Add to .env or docker-compose.yml
TASK_MANAGER_TIMEOUT_SECONDS=300
ORPHANED_CALL_AGE_MINUTES=30
```

## Monitoring

Watch for these log patterns:
- `[PLANNER] Task manager timed out after` - Indicates timeout occurred
- `[PLANNER] Empty follow-up response detected` - Null response after tools
- `WARNING: Task manager agent may still be running` - Potential orphaned process
- `Found X orphaned agent calls` - Cleanup script found orphaned calls
