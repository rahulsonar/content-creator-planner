"""
Task Inserter Utility
Simple function to insert planner agent tasks into PostgreSQL database
"""
import asyncpg
from typing import List, Dict, Any
from utils.logger import logger


async def insert_tasks_to_db(
    tasks_json: Dict[str, Any],
    db_url: str = "postgresql://postgres:postgres@content-planner-db:5432/content_planner"
) -> List[str]:
    """
    Insert tasks from planner agent JSON into database
    
    Args:
        tasks_json: Dict with "action": "create_tasks" and "tasks": [...]
        db_url: PostgreSQL connection string
        
    Returns:
        List of created task IDs
        
    Example:
        tasks = {
            "action": "create_tasks",
            "tasks": [
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
        }
        task_ids = await insert_tasks_to_db(tasks)
    """
    if tasks_json.get("action") != "create_tasks":
        logger.warning(f"Invalid action: {tasks_json.get('action')}")
        return []
    
    tasks = tasks_json.get("tasks", [])
    if not tasks:
        logger.warning("No tasks to insert")
        return []
    
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
                
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error inserting tasks: {e}")
        raise
    
    logger.info(f"Successfully created {len(created_ids)} tasks")
    return created_ids
