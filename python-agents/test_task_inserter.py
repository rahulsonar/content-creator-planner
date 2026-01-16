"""
Simple test script for task_inserter utility
Run: docker exec -it <python-agents-container> python test_task_inserter.py
"""
import asyncio
from utils.task_inserter import insert_tasks_to_db


async def test_insert():
    """Test inserting sample tasks from planner agent format"""
    
    # Sample JSON from planner agent
    planner_output = {
        "action": "create_tasks",
        "tasks": [
            {
                "title": "Research trending YouTube topics",
                "description": "Analyze top 20 tech education videos from past month. Document topics, views, engagement patterns.",
                "priority": "HIGH",
                "estimatedHours": 3,
                "researchNotes": "Use VidIQ or TubeBuddy for trend analysis. Focus on videos with 10k+ views in your subscriber range.",
                "aiReasoning": "Trend research boosts discoverability by targeting topics with proven audience interest.",
                "dependencies": []
            },
            {
                "title": "Create video script outline",
                "description": "Draft main talking points, hook, and call-to-action based on research findings.",
                "priority": "MEDIUM",
                "estimatedHours": 2,
                "researchNotes": "Follow 3-act structure: Problem (0-30s), Solution (30s-5m), Action (5-6m).",
                "aiReasoning": "Structured scripts improve retention and reduce editing time.",
                "dependencies": ["Research trending YouTube topics"]
            },
            {
                "title": "Film main content",
                "description": "Record A-roll footage following script. Aim for 10-15 minute raw footage.",
                "priority": "URGENT",
                "estimatedHours": 1.5,
                "researchNotes": "Natural lighting best before 10am. Have backup audio recorder.",
                "aiReasoning": "Early filming provides buffer for reshoots if needed.",
                "dependencies": ["Create video script outline"]
            }
        ]
    }
    
    print("Testing task insertion...")
    print(f"Tasks to insert: {len(planner_output['tasks'])}")
    
    try:
        task_ids = await insert_tasks_to_db(planner_output)
        print(f"\n✅ Successfully created {len(task_ids)} tasks:")
        for task_id in task_ids:
            print(f"  - {task_id}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_insert())
