"""
Project Inserter Utility
Simple function to insert projects into PostgreSQL database
"""
import asyncpg
from typing import List, Dict, Any
from datetime import datetime, date
from utils.logger import logger


async def insert_projects_to_db(
    projects: List[Dict[str, Any]],
    user_id: str = None,
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    Insert projects into database
    
    Args:
        projects: List of project dictionaries to insert
        user_id: User ID to associate projects with (required)
        db_url: PostgreSQL connection string
        
    Returns:
        Dict with success status and created project IDs
        
    Example:
        projects = [
            {
                "name": "YouTube Channel Launch",
                "description": "Launch new tech review channel",
                "status": "ACTIVE",
                "color": "#FF5733",
                "icon": "📹",
                "tags": ["youtube", "tech", "reviews"]
            }
        ]
        result = await insert_projects_to_db(projects, user_id="user123")
        # Returns: {"success": True, "created_ids": ["id1", "id2", ...]}
    """
    if not projects:
        logger.warning("No projects to insert")
        return {"success": False, "error": "No projects provided", "created_ids": []}
    
    if not user_id:
        logger.error("No user_id provided for project creation")
        return {"success": False, "error": "user_id is required", "created_ids": []}
    
    created_ids = []
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        
        try:
            for project in projects:
                # Map project JSON to database schema
                name = project.get("name", "Untitled Project")
                description = project.get("description", "")
                status = project.get("status", "ACTIVE").upper()
                color = project.get("color")
                icon = project.get("icon")
                tags = project.get("tags", [])
                
                # Convert string dates to date objects
                start_date = project.get("startDate")
                if start_date and isinstance(start_date, str):
                    try:
                        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        logger.warning(f"Invalid startDate format: {start_date}, setting to None")
                        start_date = None
                
                end_date = project.get("endDate")
                if end_date and isinstance(end_date, str):
                    try:
                        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        logger.warning(f"Invalid endDate format: {end_date}, setting to None")
                        end_date = None
                
                due_date = project.get("dueDate")
                if due_date and isinstance(due_date, str):
                    try:
                        due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        logger.warning(f"Invalid dueDate format: {due_date}, setting to None")
                        due_date = None
                
                is_default = bool(project.get("isDefault", False))

                if is_default:
                    await conn.execute(
                        'UPDATE "Project" SET "isDefault" = FALSE WHERE "userId" = $1',
                        user_id
                    )
                
                # Insert project (id auto-increments, don't specify it)
                query = """
                    INSERT INTO "Project" (
                        name, description, status,
                        "userId", color, icon, tags,
                        "startDate", "endDate", "dueDate", "isDefault",
                        "createdAt", "updatedAt"
                    ) VALUES (
                        $1, $2, $3::"ProjectStatus",
                        $4, $5, $6, $7,
                        $8, $9, $10, $11,
                        NOW(), NOW()
                    )
                    RETURNING id
                """
                
                project_id = await conn.fetchval(
                    query,
                    name,
                    description,
                    status,
                    user_id,
                    color,
                    icon,
                    tags,
                    start_date,
                    end_date,
                    due_date,
                    is_default
                )
                
                created_ids.append(project_id)
                logger.info(f"Created project: {project_id} - {name}")
            
            return {
                "success": True,
                "created_ids": created_ids,
                "message": f"Created {len(created_ids)} project(s)"
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to insert projects: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "created_ids": created_ids  # Return any that were created before error
        }


async def get_project_by_id(
    project_id: int | str,
    user_id: str = None,
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    Get a single project by ID
    
    Args:
        project_id: Project ID to retrieve (int or string that can be converted to int)
        user_id: User ID to verify ownership (optional, recommended for security)
        db_url: PostgreSQL connection string
        
    Returns:
        Dict with project data or error
    """
    if not project_id:
        return {"success": False, "error": "project_id is required"}
    
    # Convert project_id to int if it's a string
    try:
        project_id_int = int(project_id)
    except (ValueError, TypeError):
        return {"success": False, "error": "Invalid project_id format"}
    
    try:
        conn = await asyncpg.connect(db_url)
        
        try:
            # Build WHERE clause with optional user_id filter
            where_clauses = ["p.id = $1"]
            params = [project_id_int]
            
            if user_id:
                where_clauses.append('p."userId" = $2')
                params.append(user_id)
            
            where_sql = " AND ".join(where_clauses)
            
            query = f"""
                SELECT 
                    p.id, p.name, p.description, p.status,
                    p."userId", p.color, p.icon, p.tags, p."isDefault",
                    p."startDate", p."endDate", p."dueDate",
                    p."createdAt", p."updatedAt",
                    COUNT(t.id) FILTER (WHERE t.id IS NOT NULL) as task_count,
                    COUNT(t.id) FILTER (WHERE t.status = 'COMPLETED') as completed_tasks
                FROM "Project" p
                LEFT JOIN "Task" t ON p.id = t."projectId"
                WHERE {where_sql}
                GROUP BY p.id
            """
            
            row = await conn.fetchrow(query, *params)
            
            if not row:
                return {"success": False, "error": f"Project {project_id} not found"}
            
            return {
                "success": True,
                "project": dict(row)
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def delete_project_by_id(
    project_id: int | str,
    user_id: str = None,
    new_project_id: int | str = None,
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    Delete a project, reassigning its tasks first.

    Tasks belonging to the deleted project are transferred to new_project_id if
    given, otherwise to the user's default project (isDefault=True) if one exists,
    otherwise left orphaned (projectId set to NULL).

    Args:
        project_id: Project ID to delete
        user_id: User ID to verify ownership (optional, recommended for security)
        new_project_id: Project ID to transfer tasks to (optional)
        db_url: PostgreSQL connection string

    Returns:
        Dict with success status, deletion result, and task transfer counts
    """
    try:
        project_id_int = int(project_id)
    except (ValueError, TypeError):
        return {"success": False, "error": "Invalid project_id format"}

    try:
        conn = await asyncpg.connect(db_url)

        try:
            async with conn.transaction():
                where_clauses = ["id = $1"]
                params = [project_id_int]
                if user_id:
                    where_clauses.append('"userId" = $2')
                    params.append(user_id)

                project_row = await conn.fetchrow(
                    f'SELECT id, "userId" FROM "Project" WHERE {" AND ".join(where_clauses)}',
                    *params
                )
                if not project_row:
                    return {"success": False, "error": f"Project {project_id} not found"}

                owner_id = project_row["userId"]
                target_project_id = None

                if new_project_id is not None:
                    try:
                        new_project_id_int = int(new_project_id)
                    except (ValueError, TypeError):
                        return {"success": False, "error": "Invalid new_project_id format"}

                    if new_project_id_int == project_id_int:
                        return {"success": False, "error": "new_project_id cannot be the same as project_id"}

                    target_row = await conn.fetchrow(
                        'SELECT id FROM "Project" WHERE id = $1 AND "userId" = $2',
                        new_project_id_int, owner_id
                    )
                    if not target_row:
                        return {"success": False, "error": f"new_project_id {new_project_id} not found for this user"}

                    target_project_id = new_project_id_int
                else:
                    default_row = await conn.fetchrow(
                        'SELECT id FROM "Project" WHERE "userId" = $1 AND "isDefault" = TRUE AND id != $2',
                        owner_id, project_id_int
                    )
                    if default_row:
                        target_project_id = default_row["id"]

                affected_count = await conn.fetchval(
                    'SELECT COUNT(*) FROM "Task" WHERE "projectId" = $1', project_id_int
                )

                await conn.execute(
                    'UPDATE "Task" SET "projectId" = $1, "updatedAt" = NOW() WHERE "projectId" = $2',
                    target_project_id, project_id_int
                )

                await conn.execute('DELETE FROM "Project" WHERE id = $1', project_id_int)

            logger.info(
                f"Deleted project {project_id_int}, "
                f"{'transferred' if target_project_id else 'orphaned'} {affected_count} task(s)"
                + (f" to project {target_project_id}" if target_project_id else "")
            )

            return {
                "success": True,
                "project_id": project_id_int,
                "deleted": True,
                "target_project_id": target_project_id,
                "tasks_transferred": affected_count if target_project_id else 0,
                "tasks_orphaned": affected_count if not target_project_id else 0,
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def list_projects(
    user_id: str = None,
    status_filter: str = "",
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    List all projects, optionally filtered by status
    
    Args:
        user_id: User ID to filter projects (optional, if None returns all)
        status_filter: Filter by project status (ACTIVE, ON_HOLD, COMPLETED, ARCHIVED, CANCELLED)
        db_url: PostgreSQL connection string
        
    Returns:
        Dict with project list or error
    """
    try:
        conn = await asyncpg.connect(db_url)
        
        try:
            # Build query with optional filters
            where_clauses = []
            params = []
            param_index = 1
            
            if user_id:
                where_clauses.append(f'p."userId" = ${param_index}')
                params.append(user_id)
                param_index += 1
            
            if status_filter and status_filter.strip():
                where_clauses.append(f'p.status = ${param_index}')
                params.append(status_filter.upper())
                param_index += 1
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
                SELECT 
                    p.id, p.name, p.description, p.status,
                    p."userId", p.color, p.icon, p.tags, p."isDefault",
                    p."startDate", p."endDate", p."dueDate",
                    p."createdAt", p."updatedAt",
                    COUNT(t.id) FILTER (WHERE t.id IS NOT NULL) as task_count,
                    COUNT(t.id) FILTER (WHERE t.status = 'COMPLETED') as completed_tasks
                FROM "Project" p
                LEFT JOIN "Task" t ON p.id = t."projectId"
                WHERE {where_sql}
                GROUP BY p.id
                ORDER BY p."createdAt" DESC
                LIMIT 100
            """
            
            rows = await conn.fetch(query, *params)
            
            projects = [dict(row) for row in rows]
            
            return {
                "success": True,
                "projects": projects,
                "count": len(projects)
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        return {"success": False, "error": str(e), "projects": []}
