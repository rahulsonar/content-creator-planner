"""
Project Inserter Utility
Simple function to insert projects into PostgreSQL database
"""
import asyncpg
from typing import List, Dict, Any
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
                start_date = project.get("startDate")
                end_date = project.get("endDate")
                due_date = project.get("dueDate")
                is_default = bool(project.get("isDefault", False))

                if is_default:
                    await conn.execute(
                        'UPDATE "Project" SET "isDefault" = FALSE WHERE "userId" = $1',
                        user_id
                    )
                
                # Insert project
                query = """
                    INSERT INTO "Project" (
                        id, name, description, status,
                        "userId", color, icon, tags,
                        "startDate", "endDate", "dueDate", "isDefault",
                        "createdAt", "updatedAt"
                    ) VALUES (
                        gen_random_uuid()::text, $1, $2, $3::"ProjectStatus",
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
    project_id: str,
    user_id: str = None,
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    Get a single project by ID
    
    Args:
        project_id: Project ID to retrieve
        user_id: User ID to verify ownership (optional, recommended for security)
        db_url: PostgreSQL connection string
        
    Returns:
        Dict with project data or error
    """
    if not project_id:
        return {"success": False, "error": "project_id is required"}
    
    try:
        conn = await asyncpg.connect(db_url)
        
        try:
            # Build WHERE clause with optional user_id filter
            where_clauses = ["p.id = $1"]
            params = [project_id]
            
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
