"""
Task Management MCP Server

Exposes the app's task/project database as MCP tools so any MCP client
(Claude Desktop, Claude Code, other agents) can create, read, update, and
delete tasks and projects directly.

Run standalone (stdio transport):
    python -m mcp_server.task_management
"""
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from config.settings import settings
from utils.task_inserter import insert_tasks_to_db
from utils.task_updater import update_task_by_id
from utils.task_query import get_task_by_id, list_tasks as query_tasks, delete_task_by_id
from utils.project_manager import (
    insert_projects_to_db,
    get_project_by_id,
    list_projects as query_projects,
    delete_project_by_id,
)
from utils.logger import logger

DB_URL = settings.DATABASE_URL

mcp = FastMCP(
    name="task-management",
    instructions=(
        "Manage tasks and projects for the Content Creator Planner. "
        "Every tool takes a user_id to scope operations to that user's data."
    ),
)


# ============================================================================
# Tasks
# ============================================================================

@mcp.tool()
async def list_tasks(
    user_id: Annotated[int, Field(description="User ID to list tasks for")],
    status: Annotated[
        Optional[str],
        Field(description="Filter by status: TODO, IN_PROGRESS, REVIEW, BLOCKED, COMPLETED, CANCELLED"),
    ] = None,
    priority: Annotated[
        Optional[str], Field(description="Filter by priority: LOW, MEDIUM, HIGH, URGENT")
    ] = None,
    project_id: Annotated[Optional[int], Field(description="Filter by project ID")] = None,
    limit: Annotated[int, Field(description="Max tasks to return (default 50, max 200)")] = 50,
) -> Dict[str, Any]:
    """List a user's tasks, optionally filtered by status, priority, or project."""
    return await query_tasks(
        user_id=user_id,
        status=status,
        priority=priority,
        project_id=project_id,
        limit=limit,
        db_url=DB_URL,
    )


@mcp.tool()
async def get_task(
    user_id: Annotated[int, Field(description="User ID that owns the task")],
    task_id: Annotated[int, Field(description="Task ID to retrieve")],
) -> Dict[str, Any]:
    """Get a single task by ID."""
    return await get_task_by_id(task_id=task_id, user_id=user_id, db_url=DB_URL)


@mcp.tool()
async def create_tasks(
    user_id: Annotated[int, Field(description="User ID to create tasks for")],
    tasks: Annotated[
        List[Dict[str, Any]],
        Field(
            description=(
                "Tasks to create. Each object supports: title (required), description, "
                "priority (LOW/MEDIUM/HIGH/URGENT), estimatedHours, projectId, tags "
                "(array of strings), notes (array of {content}). New tasks start as TODO."
            )
        ),
    ],
) -> Dict[str, Any]:
    """Create one or more tasks."""
    if not tasks:
        return {"success": False, "error": "tasks must be a non-empty list"}
    result = await insert_tasks_to_db(tasks, user_id=user_id, db_url=DB_URL)
    logger.info(f"[MCP] create_tasks: {len(result.get('created_ids', []))} created for user {user_id}")
    return result


@mcp.tool()
async def update_task(
    user_id: Annotated[int, Field(description="User ID that owns the task")],
    task_id: Annotated[int, Field(description="Task ID to update")],
    updates: Annotated[
        Dict[str, Any],
        Field(
            description=(
                "Fields to update: title, description, status, priority, estimatedHours, "
                "actualHours, projectId, startDate, endDate, dueDate, completedAt, "
                "assignedTo, tags."
            )
        ),
    ],
) -> Dict[str, Any]:
    """Update fields on an existing task."""
    if not updates:
        return {"success": False, "error": "updates must be a non-empty object"}
    updated = await update_task_by_id(task_id=task_id, updates=updates, user_id=user_id, db_url=DB_URL)
    return {"success": updated, "task_id": task_id, "updated": updated}


@mcp.tool()
async def delete_task(
    user_id: Annotated[int, Field(description="User ID that owns the task")],
    task_id: Annotated[int, Field(description="Task ID to delete")],
) -> Dict[str, Any]:
    """Delete a task by ID."""
    return await delete_task_by_id(task_id=task_id, user_id=user_id, db_url=DB_URL)


# ============================================================================
# Projects
# ============================================================================

@mcp.tool()
async def list_projects(
    user_id: Annotated[int, Field(description="User ID to list projects for")],
    status: Annotated[
        Optional[str],
        Field(description="Filter by status: ACTIVE, ON_HOLD, COMPLETED, ARCHIVED, CANCELLED"),
    ] = None,
) -> Dict[str, Any]:
    """List a user's projects, each annotated with task_count and completed_tasks."""
    return await query_projects(user_id=user_id, status_filter=status or "", db_url=DB_URL)


@mcp.tool()
async def get_project(
    user_id: Annotated[int, Field(description="User ID that owns the project")],
    project_id: Annotated[int, Field(description="Project ID to retrieve")],
) -> Dict[str, Any]:
    """Get a single project by ID, including task_count and completed_tasks."""
    return await get_project_by_id(project_id=project_id, user_id=user_id, db_url=DB_URL)


@mcp.tool()
async def create_projects(
    user_id: Annotated[int, Field(description="User ID to create projects for")],
    projects: Annotated[
        List[Dict[str, Any]],
        Field(
            description=(
                "Projects to create. Each object supports: name (required), description, "
                "status (default ACTIVE), color, icon, tags (array), startDate, endDate, "
                "dueDate, isDefault."
            )
        ),
    ],
) -> Dict[str, Any]:
    """Create one or more projects."""
    if not projects:
        return {"success": False, "error": "projects must be a non-empty list"}
    result = await insert_projects_to_db(projects, user_id=user_id, db_url=DB_URL)
    logger.info(f"[MCP] create_projects: {len(result.get('created_ids', []))} created for user {user_id}")
    return result


@mcp.tool()
async def delete_project(
    user_id: Annotated[int, Field(description="User ID that owns the project")],
    project_id: Annotated[int, Field(description="Project ID to delete")],
    new_project_id: Annotated[
        Optional[int],
        Field(
            description=(
                "Project ID to transfer the deleted project's tasks to. If omitted, tasks are "
                "transferred to the user's default project if one exists, otherwise they are "
                "orphaned (projectId set to null)."
            )
        ),
    ] = None,
) -> Dict[str, Any]:
    """Delete a project, transferring its tasks to another project (explicit, default, or none)."""
    return await delete_project_by_id(
        project_id=project_id,
        user_id=user_id,
        new_project_id=new_project_id,
        db_url=DB_URL,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
