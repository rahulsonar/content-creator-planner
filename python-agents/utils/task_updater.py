"""
Task Updater Utility
Update tasks in PostgreSQL database by ID, with support for batch updates
"""
import asyncpg
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.logger import logger


async def update_task_by_id(
    task_id: int,
    updates: Dict[str, Any],
    user_id: str = None,
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> bool:
    """
    Update a single task by ID
    
    Args:
        task_id: ID of the task to update
        updates: Dictionary of fields to update
        user_id: User ID to verify ownership (optional, recommended for security)
        db_url: PostgreSQL connection string
        
    Returns:
        True if task was updated, False otherwise
        
    Example:
        updates = {
            "title": "New title",
            "status": "IN_PROGRESS",
            "priority": "HIGH",
            "estimatedHours": 5,
            "actualHours": 2,
            "description": "Updated description"
        }
        success = await update_task_by_id(task_id, updates, user_id="user123")
    """
    conn = None
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)

        if "labels" in updates and "tags" not in updates:
            updates["tags"] = updates.get("labels")
            updates.pop("labels", None)
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = [task_id]
        param_index = 2
        
        # Map of allowed fields to database columns
        allowed_fields = {
            "title": "title",
            "description": "description",
            "status": "status",
            "priority": "priority",
            "estimatedHours": "\"estimatedHours\"",
            "actualHours": "\"actualHours\"",
            "projectId": "\"projectId\"",
            "startDate": "\"startDate\"",
            "endDate": "\"endDate\"",
            "dueDate": "\"dueDate\"",
            "completedAt": "\"completedAt\"",
            "aiContext": "\"aiContext\"",
            "aiSuggestions": "\"aiSuggestions\"",
            "assignedTo": "\"assignedTo\"",
            "tags": "tags"
        }
        
        for field, value in updates.items():
            if field not in allowed_fields:
                logger.warning(f"Skipping unknown field: {field}")
                continue
            
            db_column = allowed_fields[field]
            
            # Handle enum fields
            if field in ["status", "priority"]:
                value = value.upper() if isinstance(value, str) else value
            
            # Handle date/datetime fields - convert strings to datetime objects
            if field in ["startDate", "endDate", "dueDate", "completedAt"]:
                if isinstance(value, str):
                    try:
                        # Try parsing ISO format with various patterns
                        # Support: "2026-01-26", "2026-01-26T00:00:00Z", "2026-01-26T00:00:00"
                        if value.endswith('Z'):
                            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        else:
                            value = datetime.fromisoformat(value)
                        
                        # Convert to timezone-naive for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
                        if value.tzinfo is not None:
                            value = value.replace(tzinfo=None)
                    except ValueError as e:
                        logger.error(f"Invalid date format for {field}: {value} - {e}")
                        continue
            
            set_clauses.append(f"{db_column} = ${param_index}")
            values.append(value)
            param_index += 1
        
        if not set_clauses:
            logger.warning(f"No valid fields to update for task {task_id}")
            return False
        
        # Add updated timestamp
        set_clauses.append(f"\"updatedAt\" = NOW()")
        
        # Build WHERE clause with optional user_id filter
        where_clauses = ["id = $1"]
        if user_id:
            where_clauses.append(f'"userId" = ${param_index}')
            values.append(user_id)
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            UPDATE "Task"
            SET {', '.join(set_clauses)}
            WHERE {where_sql}
            RETURNING id
        """
        
        result = await conn.fetchval(query, *values)
        
        if result:
            logger.info(f"Updated task: {task_id}")
            return True
        else:
            logger.warning(f"Task not found: {task_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise
    finally:
        if conn:
            await conn.close()


async def update_tasks_batch(
    task_updates: List[Dict[str, Any]],
    user_id: str = None,
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    Update multiple tasks in batch
    
    Args:
        task_updates: List of update objects with "id" and fields to update
        user_id: User ID to verify ownership (optional, recommended for security)
        db_url: PostgreSQL connection string
        
    Returns:
        Dictionary with success count, failed count, and details
        
    Example:
        task_updates = [
            {
                "id": "task-1",
                "status": "COMPLETED",
                "actualHours": 3
            },
            {
                "id": "task-2",
                "status": "IN_PROGRESS",
                "priority": "HIGH"
            }
        ]
        result = await update_tasks_batch(task_updates, user_id="user123")
    """
    if not task_updates:
        logger.warning("No tasks to update in batch")
        return {
            "success": 0,
            "failed": 0,
            "details": []
        }
    
    success_count = 0
    failed_count = 0
    details = []
    
    for task_update in task_updates:
        task_id = task_update.get("id")
        if not task_id:
            logger.warning("Task update missing 'id' field")
            failed_count += 1
            details.append({
                "task_id": None,
                "success": False,
                "reason": "Missing task ID"
            })
            continue
        
        # Extract updates (all keys except 'id')
        updates = {k: v for k, v in task_update.items() if k != "id"}
        
        try:
            result = await update_task_by_id(task_id, updates, user_id, db_url)
            if result:
                success_count += 1
                details.append({
                    "task_id": task_id,
                    "success": True,
                    "reason": "Updated successfully"
                })
            else:
                failed_count += 1
                details.append({
                    "task_id": task_id,
                    "success": False,
                    "reason": "Task not found or no fields updated"
                })
        except Exception as e:
            failed_count += 1
            details.append({
                "task_id": task_id,
                "success": False,
                "reason": str(e)
            })
    
    logger.info(f"Batch update complete: {success_count} succeeded, {failed_count} failed")
    
    return {
        "success": success_count,
        "failed": failed_count,
        "total": len(task_updates),
        "details": details
    }
