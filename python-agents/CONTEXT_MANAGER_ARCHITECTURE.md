# Context Manager Agent - Architecture Diagram

## System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Orchestrator  │
                    │  (routes msg)  │
                    └────────┬───────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │Onboarding│      │ Planning │      │ General  │
    │  Agent   │      │  Agent   │      │   Chat   │
    └────┬─────┘      └────┬─────┘      └────┬─────┘
         │                 │                  │
         │    Extracts     │    Extracts      │   Extracts
         │    user info    │    strategy      │   insights
         │                 │                  │
         └─────────────────┼──────────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │ Context Manager    │
                  │     Agent          │
                  │                    │
                  │ - Receives info    │
                  │ - Organizes data   │
                  │ - Updates files    │
                  └─────────┬──────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │ user_context_manager  │
                │  (File Operations)    │
                └─────────┬─────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │   agent_context/{userId}/           │
        ├─────────────────────────────────────┤
        │ INDEX.md          (overview)        │
        │ profile.md        (user details)    │
        │ goals.md          (objectives)      │
        │ preferences.md    (workflow)        │
        │ challenges.md     (pain points)     │
        │ content_strategy.md (strategy)      │
        │ audience.md       (target demo)     │
        │ schedule.md       (posting plan)    │
        │ history.md        (conversation)    │
        │ notes.md          (misc)            │
        └─────────────────────────────────────┘
```

## Data Flow Example

### Scenario: User Completes Onboarding

```
1. USER INPUT
   ↓
   "I create YouTube tech tutorials for beginners"
   
2. ONBOARDING AGENT
   ↓
   Collects: name, content type, channel, goals, challenges
   
3. ORCHESTRATOR
   ↓
   Detects: onboarding completed → send to Context Manager
   
4. CONTEXT MANAGER AGENT
   ↓
   Analyzes information and decides file structure:
   - Basic info    → profile.md
   - Goals stated  → goals.md
   - Challenges    → challenges.md
   - Overview      → INDEX.md
   
5. USER_CONTEXT_MANAGER (utility)
   ↓
   Executes file operations:
   - write_user_context("user_123", "INDEX.md", content)
   - write_user_context("user_123", "profile.md", content)
   - write_user_context("user_123", "goals.md", content)
   
6. FILE SYSTEM
   ↓
   agent_context/
   └── user_123/
       ├── INDEX.md
       ├── profile.md
       └── goals.md
```

## Tool-Based Operation Flow

### For Models with Tool Support (GPT-4, Claude 3.5)

```
┌─────────────────────────────────────────────────────────┐
│ Context Manager Agent                                   │
│                                                         │
│  1. Receives message from other agent                  │
│     ↓                                                   │
│  2. Calls LLM with tool definitions                    │
│     ↓                                                   │
│  3. LLM decides: "Need to create profile.md"           │
│     ↓                                                   │
│  4. Returns tool call:                                 │
│     {                                                   │
│       "name": "manage_user_context_files",             │
│       "arguments": {                                   │
│         "action": "update_section",                    │
│         "user_id": "user_123",                         │
│         "filename": "profile.md",                      │
│         "content": "# User Profile\n..."              │
│       }                                                │
│     }                                                   │
│     ↓                                                   │
│  5. Agent executes tool → calls utility function       │
│     ↓                                                   │
│  6. File created/updated                               │
│     ↓                                                   │
│  7. Confirmation returned to orchestrator              │
└─────────────────────────────────────────────────────────┘
```

## File Structure Pattern

### INDEX.md (Always created first)
```
# User Context Index

Quick Overview
  ↓
Links to All Sections
  ↓
Last Updated Timestamp
```

### Section Files (Created as needed)
```
profile.md        ←  From onboarding
goals.md          ←  From onboarding & planning
content_strategy.md ← From planning agent
schedule.md       ←  From planning agent
history.md        ←  Appended from all interactions
```

## Integration Points

### 1. Orchestrator Integration
```python
# In orchestrator.py
from agents.context_manager import ContextManagerAgent

class ModelOrchestrator:
    def __init__(self):
        # ... other agents
        self.context_manager = ContextManagerAgent(client)
    
    async def process_with_context_update(self, user_msg, user_id):
        # 1. Route to appropriate agent
        response = await self.onboarding_agent.process_message(...)
        
        # 2. Update context
        await self.context_manager.process_message(
            f"Onboarding data: {response}",
            {"user_id": user_id}
        )
        
        return response
```

### 2. API Routes Integration
```python
# In api/routes.py
@router.post("/context/save")
async def save_user_context(request):
    context_agent = get_context_manager()
    result = await context_agent.process_message(
        request.information,
        {"user_id": request.user_id}
    )
    return {"status": "saved"}
```

### 3. Context Retrieval
```python
# When starting new conversation
from utils.user_context_manager import read_user_context

# Load user context for agent
profile = read_user_context(user_id, "profile.md")
goals = read_user_context(user_id, "goals.md")

context = f"User Profile:\n{profile}\n\nGoals:\n{goals}"
```

## Markdown File Format

### Example: profile.md
```markdown
# User Profile

## Basic Information
- **Name:** Sarah Johnson
- **Email:** sarah@example.com
- **Joined:** 2026-01-15

## Content Details
- **Platform:** YouTube
- **Niche:** Tech Tutorials
- **Experience:** 3 years
- **Subscribers:** 50,000

---
*Last updated: 2026-01-16 14:30*
```

### Example: history.md
```markdown
# Conversation History

## 2026-01-15 10:00 - Onboarding
User completed initial onboarding...

## 2026-01-15 14:30 - Planning Session
Created 4-week content calendar...

## 2026-01-16 09:00 - Strategy Discussion
Discussed audience growth tactics...
```

## Benefits of This Architecture

1. **Separation of Concerns**
   - Context Manager focuses only on file organization
   - Other agents focus on their domain (onboarding, planning)
   
2. **Reusability**
   - Any agent can trigger context updates
   - Context files can be read by any agent
   
3. **Persistence**
   - User context survives server restarts
   - Easy to backup/restore
   
4. **Human-Readable**
   - Developers can inspect context files directly
   - Easy debugging and manual corrections
   
5. **Scalability**
   - Each user isolated in own directory
   - No database bottlenecks for simple context
   
6. **Flexibility**
   - Add new section files without code changes
   - Supports any markdown structure

## Future Enhancements

### Phase 2 Features
- [ ] Context compression for large files
- [ ] Auto-archiving old history
- [ ] Search across context files
- [ ] Context summarization
- [ ] Version control integration

### Phase 3 Features
- [ ] Multi-format support (JSON, YAML)
- [ ] Context analytics dashboard
- [ ] Smart context retrieval (semantic search)
- [ ] Context sharing between users
- [ ] Backup to cloud storage
