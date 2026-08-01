"""
Task Query Utility
Read and delete operations for tasks in PostgreSQL, complementing
task_inserter.py (create) and task_updater.py (update).
"""
import asyncpg
from typing import Any, Dict, List, Optional
from config.settings import settings
from utils.logger import logger

TASK_COLUMNS = """
    id, "taskKey", title, description, status, priority,
    "startDate", "endDate", "dueDate", "completedAt",
    "userId", "projectId", "parentId",
    "aiGenerated", "aiSuggestions", "aiContext",
    tags, "assignedTo", "estimatedHours", "actualHours",
    "createdAt", "updatedAt"
"""

_DATETIME_FIELDS = (
    "startDate", "endDate", "dueDate", "completedAt", "createdAt", "updatedAt"
)


def _serialize_task(row: asyncpg.Record) -> Dict[str, Any]:
    task = dict(row)
    for field in _DATETIME_FIELDS:
        if task.get(field) is not None:
            task[field] = task[field].isoformat()
    return task


async def get_task_by_id(
    task_id: int,
    user_id: Optional[int] = None,
    db_url: str = settings.DATABASE_URL,
) -> Dict[str, Any]:
    """
    Get a single task by ID, optionally scoped to a user.

    Args:
        task_id: Task ID to retrieve
        user_id: User ID to verify ownership (optional, recommended for security)
        db_url: PostgreSQL connection string

    Returns:
        Dict with success status and task data (or error)
    """
    conn = None
    try:
        conn = await asyncpg.connect(db_url)

        where_clauses = ["id = $1"]
        params: List[Any] = [task_id]
        if user_id is not None:
            where_clauses.append('"userId" = $2')
            params.append(user_id)

        query = f"""
            SELECT {TASK_COLUMNS}
            FROM "Task"
            WHERE {" AND ".join(where_clauses)}
        """
        row = await conn.fetchrow(query, *params)

        if not row:
            return {"success": False, "error": f"Task {task_id} not found"}

        return {"success": True, "task": _serialize_task(row)}

    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            await conn.close()


async def list_tasks(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    project_id: Optional[int] = None,
    limit: int = 50,
    db_url: str = settings.DATABASE_URL,
) -> Dict[str, Any]:
    """
    List tasks, optionally filtered by status, priority, and/or project.

    Args:
        user_id: User ID to filter tasks (optional, if None returns all)
        status: Filter by TaskStatus (TODO, IN_PROGRESS, REVIEW, BLOCKED, COMPLETED, CANCELLED)
        priority: Filter by Priority (LOW, MEDIUM, HIGH, URGENT)
        project_id: Filter by project ID
        limit: Maximum number of tasks to return (default 50, max 200)
        db_url: PostgreSQL connection string

    Returns:
        Dict with success status and task list
    """
    conn = None
    try:
        conn = await asyncpg.connect(db_url)

        where_clauses = []
        params: List[Any] = []
        param_index = 1

        if user_id is not None:
            where_clauses.append(f'"userId" = ${param_index}')
            params.append(user_id)
            param_index += 1

        if status:
            where_clauses.append(f'status = ${param_index}::"TaskStatus"')
            params.append(status.upper())
            param_index += 1

        if priority:
            where_clauses.append(f'priority = ${param_index}::"Priority"')
            params.append(priority.upper())
            param_index += 1

        if project_id is not None:
            where_clauses.append(f'"projectId" = ${param_index}')
            params.append(project_id)
            param_index += 1

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        safe_limit = max(1, min(limit, 200))

        query = f"""
            SELECT {TASK_COLUMNS}
            FROM "Task"
            WHERE {where_sql}
            ORDER BY "createdAt" DESC
            LIMIT ${param_index}
        """
        params.append(safe_limit)

        rows = await conn.fetch(query, *params)
        tasks = [_serialize_task(row) for row in rows]

        return {"success": True, "tasks": tasks, "count": len(tasks)}

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}", exc_info=True)
        return {"success": False, "error": str(e), "tasks": []}
    finally:
        if conn:
            await conn.close()


async def delete_task_by_id(
    task_id: int,
    user_id: Optional[int] = None,
    db_url: str = settings.DATABASE_URL,
) -> Dict[str, Any]:
    """
    Delete a task by ID, optionally scoped to a user.

    Args:
        task_id: ID of the task to delete
        user_id: User ID to verify ownership (optional, recommended for security)
        db_url: PostgreSQL connection string

    Returns:
        Dict with success status
    """
    conn = None
    try:
        conn = await asyncpg.connect(db_url)

        where_clauses = ["id = $1"]
        params: List[Any] = [task_id]
        if user_id is not None:
            where_clauses.append('"userId" = $2')
            params.append(user_id)

        query = f'DELETE FROM "Task" WHERE {" AND ".join(where_clauses)}'
        result = await conn.execute(query, *params)
        deleted = result == "DELETE 1"

        if deleted:
            logger.info(f"Deleted task: {task_id}")
        else:
            logger.warning(f"Task not found or not owned by user: {task_id}")

        return {"success": deleted, "task_id": task_id, "deleted": deleted}

    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            await conn.close()
