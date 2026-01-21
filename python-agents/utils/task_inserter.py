"""
Task Inserter Utility
Simple function to insert planner agent tasks into PostgreSQL database
"""
import asyncpg
from typing import List, Dict, Any
from utils.logger import logger


async def insert_tasks_to_db(
    tasks: List[Dict[str, Any]],
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> Dict[str, Any]:
    """
    Insert tasks into database
    
    Args:
        tasks: List of task dictionaries to insert
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
    
    created_ids = []
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        
        try:
            for task in tasks:
                # Map planner JSON to database schema
                title = task.get("title", "Untitled Task")
                description = task.get("description", "")
                priority = task.get("priority", "MEDIUM").upper()
                estimated_hours = task.get("estimatedHours", 0)
                
                # Combine research notes and AI reasoning into aiContext
                ai_context = {
                    "researchNotes": task.get("researchNotes", ""),
                    "aiReasoning": task.get("aiReasoning", ""),
                    "dependencies": task.get("dependencies", [])
                }
                
                # Insert task
                query = """
                    INSERT INTO "Task" (
                        id, title, description, status, priority,
                        "estimatedHours", "aiGenerated", "aiContext",
                        "createdAt", "updatedAt"
                    ) VALUES (
                        gen_random_uuid()::text, $1, $2, 'TODO', $3::\"Priority\",
                        $4, true, $5,
                        NOW(), NOW()
                    )
                    RETURNING id
                """
                
                task_id = await conn.fetchval(
                    query,
                    title,
                    description,
                    priority,
                    estimated_hours,
                    str(ai_context)  # Store as string for now
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
