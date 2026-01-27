"""
Task Inserter Utility
Simple function to insert planner agent tasks into PostgreSQL database
"""
import asyncpg
from typing import List, Dict, Any
from utils.logger import logger


async def insert_tasks_to_db(
    tasks: List[Dict[str, Any]],
    user_id: str = None,
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    Insert tasks into database
    
    Args:
        tasks: List of task dictionaries to insert
        user_id: User ID to associate tasks with (required)
        db_url: PostgreSQL connection string
        
    Returns:
        Dict with success status and created task IDs
        
    Example:
        tasks = [
            {
                "title": "Research trending topics",
                "description": "Analyze top 20 videos...",
                "priority": "HIGH",
                "estimatedHours": 3,
                "researchNotes": "Use VidIQ/TubeBuddy...",
                "aiReasoning": "Trends boost discoverability...",
                "dependencies": []
            }
        ]
        result = await insert_tasks_to_db(tasks)
        # Returns: {"success": True, "created_ids": ["id1", "id2", ...]}
    """
    if not tasks:
        logger.warning("No tasks to insert")
        return {"success": False, "error": "No tasks provided", "created_ids": []}
    
    if not user_id:
        logger.error("No user_id provided for task creation")
        return {"success": False, "error": "user_id is required", "created_ids": []}
    
    created_ids = []
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        
        try:
            # Get next task key number
            latest_task = await conn.fetchrow("""
                SELECT "taskKey" FROM "Task"
                WHERE "taskKey" LIKE 'CCP-%'
                ORDER BY "taskKey" DESC
                LIMIT 1
            """)
            
            next_number = 1
            if latest_task and latest_task['taskKey']:
                # Extract number from CCP-XXX format
                import re
                match = re.search(r'CCP-(\d+)', latest_task['taskKey'])
                if match:
                    next_number = int(match.group(1)) + 1
            
            for idx, task in enumerate(tasks):
                # Generate task key (CCP-001, CCP-002, etc.)
                task_key = f"CCP-{str(next_number + idx).zfill(3)}"
                
                # Map planner JSON to database schema
                title = task.get("title", "Untitled Task")
                description = task.get("description", "")
                priority = task.get("priority", "MEDIUM").upper()
                estimated_hours = task.get("estimatedHours", 0)
                project_id = task.get("projectId") or task.get("project_id")
                tags = task.get("tags") if task.get("tags") is not None else task.get("labels")
                
                # Combine research notes and AI reasoning into aiContext
                ai_context = {
                    "researchNotes": task.get("researchNotes", ""),
                    "aiReasoning": task.get("aiReasoning", ""),
                    "dependencies": task.get("dependencies", [])
                }
                
                # Insert task
                query = """
                    INSERT INTO "Task" (
                        id, "taskKey", title, description, status, priority,
                        "userId", "projectId", "estimatedHours", "aiGenerated", "aiContext", "tags",
                        "createdAt", "updatedAt"
                    ) VALUES (
                        gen_random_uuid()::text, $1, $2, $3, 'TODO', $4::\"Priority\",
                        $5, $6, $7, true, $8, $9,
                        NOW(), NOW()
                    )
                    RETURNING id
                """
                
                task_id = await conn.fetchval(
                    query,
                    task_key,
                    title,
                    description,
                    priority,
                    user_id,
                    project_id,
                    estimated_hours,
                    str(ai_context),  # Store as string for now
                    tags
                )
                
                created_ids.append(task_id)
                logger.info(f"Created task: {task_id} - {title}")
                
                # Insert notes if provided
                notes = task.get("notes", [])
                if notes and isinstance(notes, list):
                    for note in notes:
                        if isinstance(note, dict) and note.get("content"):
                            note_query = """
                                INSERT INTO "TaskNote" (
                                    id, "taskId", content, "createdBy",
                                    "createdAt", "updatedAt"
                                ) VALUES (
                                    gen_random_uuid()::text, $1, $2, $3,
                                    NOW(), NOW()
                                )
                            """
                            await conn.execute(
                                note_query,
                                task_id,
                                note.get("content"),
                                note.get("createdBy")
                            )
                            logger.info(f"Added note to task: {task_id}")
                
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error inserting tasks: {e}", exc_info=True)
        return {"success": False, "error": str(e), "created_ids": []}
    
    logger.info(f"Successfully created {len(created_ids)} tasks")
    return {"success": True, "created_ids": created_ids, "count": len(created_ids)}
