"""
Tool Handlers
Direct (non-LLM) implementations of the database tools, shared by
TaskExecutor and PlannerAgentRunner.
"""
from typing import Dict, Any

from utils.logger import logger


def coerce_id(value: Any) -> Any:
    """
    Cast an ID to int when possible.

    Variable references like ${task_1.result.project_id} are always
    resolved to strings, and LLMs often emit numeric IDs as strings too,
    but ID columns in the database are integers, so numeric-looking
    strings need to be converted back before hitting asyncpg.
    """
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


async def manage_tasks(context: Dict, user_id: str) -> Any:
    """Execute manage_tasks tool."""
    from utils.task_inserter import insert_tasks_to_db
    from utils.task_updater import update_task_by_id
    from utils.task_query import get_task_by_id, list_tasks, delete_task_by_id

    action = context.get('action')
    logger.info(f"[ToolHandlers] manage_tasks action: {action}")

    if action == 'create':
        tasks = context.get('tasks', [])
        if not tasks:
            raise ValueError("tasks must be a non-empty list")
        for task in tasks:
            if 'projectId' in task:
                task['projectId'] = coerce_id(task['projectId'])
        return await insert_tasks_to_db(tasks, user_id=user_id)

    elif action == 'update':
        task_id = coerce_id(context.get('task_id'))
        updates = context.get('updates', {})
        if not task_id:
            raise ValueError("task_id is required")
        if not updates:
            raise ValueError("updates must be a non-empty object")
        if 'projectId' in updates:
            updates['projectId'] = coerce_id(updates['projectId'])
        updated = await update_task_by_id(task_id, updates, user_id=user_id)
        return {"success": updated, "task_id": task_id, "updated": updated}

    elif action == 'get':
        task_id = coerce_id(context.get('task_id'))
        if not task_id:
            raise ValueError("task_id is required")
        return await get_task_by_id(task_id=task_id, user_id=user_id)

    elif action == 'list':
        return await list_tasks(
            user_id=user_id,
            status=context.get('status'),
            priority=context.get('priority'),
            project_id=coerce_id(context.get('project_id')),
            limit=context.get('limit', 50),
        )

    elif action == 'delete':
        task_id = coerce_id(context.get('task_id'))
        if not task_id:
            raise ValueError("task_id is required")
        return await delete_task_by_id(task_id=task_id, user_id=user_id)

    else:
        raise ValueError(f"Unknown manage_tasks action: {action}")


async def manage_projects(context: Dict, user_id: str) -> Any:
    """Execute manage_projects tool."""
    from utils.project_manager import (
        insert_projects_to_db,
        get_project_by_id,
        list_projects,
        delete_project_by_id,
    )

    action = context.get('action')
    logger.info(f"[ToolHandlers] manage_projects action: {action}")

    if action == 'create':
        projects = context.get('projects', [])
        if not projects:
            raise ValueError("projects must be a non-empty list")
        return await insert_projects_to_db(projects, user_id=user_id)

    elif action == 'get':
        project_id = coerce_id(context.get('project_id'))
        if not project_id:
            raise ValueError("project_id is required")
        return await get_project_by_id(project_id=project_id, user_id=user_id)

    elif action == 'list':
        return await list_projects(user_id=user_id, status_filter=context.get('status', ''))

    elif action == 'delete':
        project_id = coerce_id(context.get('project_id'))
        if not project_id:
            raise ValueError("project_id is required")
        new_project_id = coerce_id(context.get('new_project_id'))
        return await delete_project_by_id(
            project_id=project_id,
            user_id=user_id,
            new_project_id=new_project_id,
        )

    else:
        raise ValueError(f"Unknown manage_projects action: {action}")
