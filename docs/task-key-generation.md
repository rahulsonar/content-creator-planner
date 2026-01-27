# Task Key Auto-Generation: CCP-XXX Format

## Overview
Implemented automatic task key generation with the format **CCP-XXX** (Content Creator Planner) for all task creation across the application.

- **Format**: `CCP-001`, `CCP-002`, ..., `CCP-999`, `CCP-1000`, etc.
- **Padding**: Minimum 3 digits with leading zeros

## Implementation Summary

### 1. Task Key Generator Helper
**File**: `nextjs/lib/task-key-generator.ts`

- Queries database for the highest existing CCP task key
- Extracts number, increments it, and returns formatted key
- Fallback mechanism using timestamp if query fails

**Usage**:
```typescript
import { generateTaskKey } from '@/lib/task-key-generator';

const taskKey = await generateTaskKey(); // Returns: "CCP-001", "CCP-002", etc.
```

### 2. API Route Integration
**File**: `nextjs/app/api/tasks/route.ts`

- Added import: `import { generateTaskKey } from '@/lib/task-key-generator';`
- Generates task key before creating task
- Auto-assigns key to all new tasks created via UI

**Code Change**:
```typescript
// Generate task key
const taskKey = await generateTaskKey();

const task = await prisma.task.create({
  data: {
    taskKey,  // Auto-assigned
    title,
    description,
    // ... other fields
  },
});
```

### 3. Python Task Inserter
**File**: `python-agents/utils/task_inserter.py`

- Queries latest task key at the start of batch insertion
- Generates sequential keys for all tasks in the batch
- Uses Python regex to extract number from CCP-XXX format

**Code Change**:
```python
# Get next task key number
latest_task = await conn.fetchrow("""
    SELECT "taskKey" FROM "Task"
    WHERE "taskKey" LIKE 'CCP-%'
    ORDER BY "taskKey" DESC
    LIMIT 1
""")

next_number = 1
if latest_task and latest_task['taskKey']:
    import re
    match = re.search(r'CCP-(\d+)', latest_task['taskKey'])
    if match:
        next_number = int(match.group(1)) + 1

for idx, task in enumerate(tasks):
    task_key = f"CCP-{str(next_number + idx).zfill(3)}"
    # ... insert task with task_key
```

### 4. Seed Data
**File**: `nextjs/prisma/seed.ts`

- Updated to assign sequential CCP keys to all seeded tasks
- Main tasks: `CCP-001` through `CCP-020` (20 tasks)
- Parent task: `CCP-021`
- Subtasks: `CCP-022` through `CCP-026` (5 subtasks)

**Code Change**:
```typescript
// Main tasks
for (let i = 0; i < tasks.length; i++) {
  const taskKey = `CCP-${String(i + 1).padStart(3, '0')}`;
  await prisma.task.create({
    data: { ...task, taskKey }
  });
}

// Parent task + subtasks
const taskKeyNumber = tasks.length + 1;
const mainTask = await prisma.task.create({
  data: {
    taskKey: `CCP-${String(taskKeyNumber).padStart(3, '0')}`,
    // ... other fields
  }
});
```

## Testing

### Test via UI (Kanban Board)
1. Navigate to `/kanban`
2. Click "Create Task" button
3. Fill in task details and submit
4. Verify new task has key `CCP-XXX` where XXX is the next sequential number

### Test via API
```bash
curl -X POST http://localhost:3000/api/tasks \
  -H "Content-Type: application/json" \
  -H "Cookie: auth-token=YOUR_TOKEN" \
  -d '{
    "title": "Test Task",
    "projectId": "PROJECT_ID",
    "priority": "HIGH"
  }'
```

Expected response includes:
```json
{
  "id": "...",
  "taskKey": "CCP-027",
  "title": "Test Task",
  ...
}
```

### Test via Python Agents
```python
from utils.task_inserter import insert_tasks_to_db

tasks = [{
    "title": "AI Generated Task",
    "description": "Test task from Python",
    "priority": "MEDIUM"
}]

result = await insert_tasks_to_db(tasks, user_id="USER_ID")
# Creates task with taskKey: "CCP-028"
```

### Reset and Re-Seed Database
```bash
# Inside Docker container
docker exec -it content-planner-app npx prisma migrate reset
docker exec -it content-planner-app npm run db:seed
```

## Task Key Behavior

### Sequential Ordering
Task keys are assigned sequentially based on database query:
- First task created: `CCP-001`
- Second task: `CCP-002`
- 100th task: `CCP-100`
- 1000th task: `CCP-1000`

### Concurrency Handling
The current implementation queries the latest key before generating. In high-concurrency scenarios, consider:
- Adding database transaction locks
- Using PostgreSQL sequences
- Implementing retry logic with exponential backoff

### Key Format Validation
Regex pattern used for extraction: `/CCP-(\d+)/`
- Matches: `CCP-001`, `CCP-999`, `CCP-1000`
- Case-sensitive (must be uppercase `CCP`)

## Files Modified

1. ✅ `nextjs/lib/task-key-generator.ts` - NEW
2. ✅ `nextjs/app/api/tasks/route.ts` - Modified
3. ✅ `python-agents/utils/task_inserter.py` - Modified
4. ✅ `nextjs/prisma/seed.ts` - Modified

## Integration Points

All task creation flows now generate task keys automatically:

1. **UI Forms** → API Route → `generateTaskKey()` → Database
2. **Python AI Agents** → `task_inserter.py` → Database
3. **Database Seeding** → `seed.ts` → Database

No manual key assignment needed anywhere in the application.
