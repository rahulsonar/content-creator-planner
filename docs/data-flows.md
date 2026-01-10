# Data Flow Documentation
## Content Creator Planner - AI Agent System

**Version:** 1.0  
**Date:** January 7, 2026

---

## 1. Overview

This document details the data flows for all major user interactions with the AI agent system, including request/response patterns, state transitions, and error handling.

---

## 2. User Onboarding Flow

### 2.1 Complete Onboarding Sequence

```
┌─────────┐                  ┌──────────┐                 ┌────────────┐               ┌──────────┐
│ Browser │                  │ Next.js  │                 │   Python   │               │   LLM    │
│         │                  │  Server  │                 │   Agent    │               │   API    │
└────┬────┘                  └────┬─────┘                 └──────┬─────┘               └────┬─────┘
     │                            │                              │                          │
     │  1. Visit Dashboard        │                              │                          │
     ├────────────────────────────>                              │                          │
     │                            │                              │                          │
     │  2. Check onboarding       │                              │                          │
     │     status (DB query)      │                              │                          │
     │<────────────────────────────                              │                          │
     │  onboardingCompleted=false │                              │                          │
     │                            │                              │                          │
     │  3. POST /api/agent/       │                              │                          │
     │     onboarding/start       │                              │                          │
     │     {userId: "uuid"}       │                              │                          │
     ├────────────────────────────>                              │                          │
     │                            │  4. Verify auth              │                          │
     │                            │     Extract userId           │                          │
     │                            │                              │                          │
     │                            │  5. Forward request          │                          │
     │                            │     POST /onboarding/start   │                          │
     │                            │     Headers:                 │                          │
     │                            │     X-Internal-Secret: ***   │                          │
     │                            │     X-User-Id: uuid          │                          │
     │                            ├──────────────────────────────>                          │
     │                            │                              │                          │
     │                            │                              │  6. Check for existing   │
     │                            │                              │     conversation (DB)    │
     │                            │                              │<─────                    │
     │                            │                              │  None found              │
     │                            │                              │                          │
     │                            │                              │  7. Create Conversation  │
     │                            │                              │     INSERT INTO          │
     │                            │                              │     conversations        │
     │                            │                              │     (userId, type:       │
     │                            │                              │     ONBOARDING)          │
     │                            │                              │<─────                    │
     │                            │                              │                          │
     │                            │                              │  8. Generate first       │
     │                            │                              │     question             │
     │                            │                              │     POST /chat/          │
     │                            │                              │     completions          │
     │                            │                              ├──────────────────────────>
     │                            │                              │                          │
     │                            │                              │<──────────────────────────
     │                            │                              │  "Hey! Let's set up..."  │
     │                            │                              │                          │
     │                            │                              │  9. Save message to DB   │
     │                            │                              │<─────                    │
     │                            │                              │                          │
     │                            │  10. Return response         │                          │
     │                            │<──────────────────────────────                          │
     │                            │  {                           │                          │
     │                            │    conversationId: "uuid",   │                          │
     │                            │    message: "Hey...",        │                          │
     │                            │    step: "channel_info",     │                          │
     │                            │    completed: false          │                          │
     │                            │  }                           │                          │
     │  11. Display message       │                              │                          │
     │<────────────────────────────                              │                          │
     │                            │                              │                          │
     │  12. User types response:  │                              │                          │
     │      "I have a tech        │                              │                          │
     │       YouTube channel"     │                              │                          │
     ├────────────────────────────>                              │                          │
     │  POST /api/agent/          │                              │                          │
     │  onboarding/message        │                              │                          │
     │  {                         │                              │                          │
     │    conversationId: "uuid", │                              │                          │
     │    message: "I have..."    │                              │                          │
     │  }                         │                              │                          │
     │                            │                              │                          │
     │                            │  13. Forward to Python       │                          │
     │                            ├──────────────────────────────>                          │
     │                            │                              │                          │
     │                            │                              │  14. Load conversation   │
     │                            │                              │      from DB             │
     │                            │                              │<─────                    │
     │                            │                              │                          │
     │                            │                              │  15. Append user message │
     │                            │                              │      to messages[]       │
     │                            │                              │                          │
     │                            │                              │  16. Call LLM with       │
     │                            │                              │      conversation        │
     │                            │                              │      history             │
     │                            │                              ├──────────────────────────>
     │                            │                              │                          │
     │                            │                              │<──────────────────────────
     │                            │                              │  "Great! What's your     │
     │                            │                              │   channel's topic?"      │
     │                            │                              │                          │
     │                            │                              │  17. Update conversation │
     │                            │                              │      in DB               │
     │                            │                              │<─────                    │
     │                            │                              │                          │
     │                            │<──────────────────────────────                          │
     │<────────────────────────────                              │                          │
     │                            │                              │                          │
     │  [Continue for 8-12        │                              │                          │
     │   message exchanges...]    │                              │                          │
     │                            │                              │                          │
     │                            │                              │  18. Final message:      │
     │                            │                              │      Determine           │
     │                            │                              │      completion          │
     │                            │                              ├──────────────────────────>
     │                            │                              │                          │
     │                            │                              │<──────────────────────────
     │                            │                              │  completed: true         │
     │                            │                              │                          │
     │                            │                              │  19. Generate context.md │
     │                            │                              │      file                │
     │                            │                              │      {project_root}/     │
     │                            │                              │      agent_context/      │
     │                            │                              │      {userId}/           │
     │                            │                              │      context.md          │
     │                            │                              │                          │
     │                            │                              │  20. Update UserContext  │
     │                            │                              │      in DB               │
     │                            │                              │<─────                    │
     │                            │                              │                          │
     │                            │                              │  21. Mark conversation   │
     │                            │                              │      complete            │
     │                            │                              │<─────                    │
     │                            │                              │                          │
     │                            │  22. Return completion       │                          │
     │                            │<──────────────────────────────                          │
     │                            │  {                           │                          │
     │                            │    completed: true,          │                          │
     │                            │    summary: "...",           │                          │
     │                            │    contextPath: "..."        │                          │
     │                            │  }                           │                          │
     │                            │                              │                          │
     │                            │  23. Update User model       │                          │
     │                            │      onboardingCompleted=true│                          │
     │                            │      onboardingCompletedAt   │                          │
     │                            │<─────                        │                          │
     │                            │                              │                          │
     │  24. Redirect to dashboard │                              │                          │
     │<────────────────────────────                              │                          │
     │                            │                              │                          │
```

### 2.2 State Transitions

```
User States:
┌─────────────────┐
│   New User      │
│ onboarding=false│
└────────┬────────┘
         │
         │ Start Onboarding
         ↓
┌─────────────────┐
│  In Onboarding  │
│ status=ACTIVE   │
│ step=channel_.. │
└────────┬────────┘
         │
         │ Complete All Steps
         ↓
┌─────────────────┐
│   Onboarded     │
│ onboarding=true │
│ completedAt set │
└─────────────────┘
```

---

## 3. WebSocket Streaming Flow

### 3.1 Real-Time Message Streaming

```
┌─────────┐              ┌──────────┐              ┌────────────┐              ┌──────────┐
│ Browser │              │ Next.js  │              │   Python   │              │   LLM    │
│         │              │ Socket.io│              │  WebSocket │              │   API    │
└────┬────┘              └────┬─────┘              └──────┬─────┘              └────┬─────┘
     │                        │                           │                         │
     │  1. Connect WebSocket  │                           │                         │
     │     ws://localhost:3000│                           │                         │
     ├────────────────────────>                           │                         │
     │                        │                           │                         │
     │  2. Authenticate       │                           │                         │
     │     {token: "jwt..."}  │                           │                         │
     ├────────────────────────>                           │                         │
     │                        │  Verify JWT               │                         │
     │                        │<─────                     │                         │
     │                        │                           │                         │
     │  3. Connection ACK     │                           │                         │
     │<────────────────────────                           │                         │
     │  {status: "connected"} │                           │                         │
     │                        │                           │                         │
     │                        │  4. Open connection to    │                         │
     │                        │     Python WebSocket      │                         │
     │                        ├───────────────────────────>                         │
     │                        │  ws://python:8000/ws      │                         │
     │                        │  {userId: "uuid"}         │                         │
     │                        │                           │  Authenticate           │
     │                        │                           │<─────                   │
     │                        │                           │                         │
     │  5. User sends message │                           │                         │
     │     {                  │                           │                         │
     │       conversationId,  │                           │                         │
     │       message: "..."   │                           │                         │
     │     }                  │                           │                         │
     ├────────────────────────>                           │                         │
     │                        │                           │                         │
     │                        │  6. Forward message       │                         │
     │                        ├───────────────────────────>                         │
     │                        │                           │                         │
     │                        │                           │  7. Load conversation   │
     │                        │                           │<─────                   │
     │                        │                           │                         │
     │                        │                           │  8. Stream request to   │
     │                        │                           │     LLM                 │
     │                        │                           ├─────────────────────────>
     │                        │                           │  POST /chat/completions │
     │                        │                           │  {stream: true}         │
     │                        │                           │                         │
     │                        │                           │  9. Receive token       │
     │                        │                           │<═════════════════════════
     │                        │                           │  data: {"choices":[...]}│
     │                        │                           │                         │
     │                        │  10. Forward token        │                         │
     │                        │<═══════════════════════════                         │
     │                        │  {type: "token",          │                         │
     │                        │   content: "Hey"}         │                         │
     │                        │                           │                         │
     │  11. Display token     │                           │                         │
     │<════════════════════════                           │                         │
     │  "Hey"                 │                           │                         │
     │                        │                           │                         │
     │                        │                           │  12. Next token         │
     │                        │                           │<═════════════════════════
     │                        │                           │  data: {"choices":[...]}│
     │                        │                           │                         │
     │                        │  13. Forward token        │                         │
     │                        │<═══════════════════════════                         │
     │  14. Append token      │                           │                         │
     │<════════════════════════                           │                         │
     │  "Hey!"                │                           │                         │
     │                        │                           │                         │
     │  [Stream continues     │                           │                         │
     │   for full response]   │                           │                         │
     │                        │                           │                         │
     │                        │                           │  15. Stream ends        │
     │                        │                           │<─────────────────────────
     │                        │                           │  data: [DONE]           │
     │                        │                           │                         │
     │                        │                           │  16. Save full message  │
     │                        │                           │      to DB              │
     │                        │                           │<─────                   │
     │                        │                           │                         │
     │                        │  17. Send completion      │                         │
     │                        │<═══════════════════════════                         │
     │                        │  {type: "done",           │                         │
     │                        │   messageId: "uuid"}      │                         │
     │                        │                           │                         │
     │  18. Enable input      │                           │                         │
     │<════════════════════════                           │                         │
     │                        │                           │                         │
```

### 3.2 WebSocket Message Types

```typescript
// Client → Server
interface UserMessage {
  type: 'message';
  conversationId: string;
  content: string;
}

interface PingMessage {
  type: 'ping';
}

// Server → Client
interface TokenMessage {
  type: 'token';
  content: string;        // Individual token
  timestamp: string;
}

interface DoneMessage {
  type: 'done';
  messageId: string;      // Full message saved to DB
  tokensUsed: number;
}

interface ErrorMessage {
  type: 'error';
  error: string;
  code: 'RATE_LIMIT' | 'LLM_ERROR' | 'INTERNAL_ERROR';
}

interface PongMessage {
  type: 'pong';
}
```

---

## 4. Content Planning Flow

### 4.1 AI-Generated Task Plan Creation

```
┌─────────┐              ┌──────────┐              ┌────────────┐              ┌──────────┐
│ Browser │              │ Next.js  │              │   Python   │              │   LLM    │
└────┬────┘              └────┬─────┘              └──────┬─────┘              └────┬─────┘
     │                        │                           │                         │
     │  1. User clicks        │                           │                         │
     │     "Generate Plan"    │                           │                         │
     ├────────────────────────>                           │                         │
     │  POST /api/agent/      │                           │                         │
     │  planning/start        │                           │                         │
     │  {                     │                           │                         │
     │    timeframe: "6 mo",  │                           │                         │
     │    videoCount: 15      │                           │                         │
     │  }                     │                           │                         │
     │                        │                           │                         │
     │                        │  2. Forward request       │                         │
     │                        ├───────────────────────────>                         │
     │                        │  Headers:                 │                         │
     │                        │  X-User-Id: uuid          │                         │
     │                        │                           │                         │
     │                        │                           │  3. Load user context   │
     │                        │                           │     - From DB           │
     │                        │                           │     - From context.md   │
     │                        │                           │<─────                   │
     │                        │                           │                         │
     │                        │                           │  4. Build planning      │
     │                        │                           │     prompt              │
     │                        │                           │     """                 │
     │                        │                           │     User: Tech YouTuber │
     │                        │                           │     Topic: Python       │
     │                        │                           │     Goal: 15 videos     │
     │                        │                           │     Frequency: Weekly   │
     │                        │                           │     Create plan...      │
     │                        │                           │     """                 │
     │                        │                           │                         │
     │                        │                           │  5. Call LLM            │
     │                        │                           │     (Claude 3.5)        │
     │                        │                           ├─────────────────────────>
     │                        │                           │  POST /messages         │
     │                        │                           │  {                      │
     │                        │                           │    model: "claude...",  │
     │                        │                           │    messages: [...]      │
     │                        │                           │  }                      │
     │                        │                           │                         │
     │                        │                           │<─────────────────────────
     │                        │                           │  [Structured JSON plan] │
     │                        │                           │                         │
     │                        │                           │  6. Parse response      │
     │                        │                           │     Validate schema     │
     │                        │                           │                         │
     │                        │                           │  7. Create Conversation │
     │                        │                           │     for planning session│
     │                        │                           │<─────                   │
     │                        │                           │                         │
     │                        │  8. Return plan          │                         │
     │                        │<───────────────────────────                         │
     │                        │  {                        │                         │
     │                        │    conversationId: "uuid",│                         │
     │                        │    plan: [                │                         │
     │                        │      {                    │                         │
     │                        │        title: "Setup...", │                         │
     │                        │        description: "...",│                         │
     │                        │        dueDate: "...",    │                         │
     │                        │        priority: "HIGH",  │                         │
     │                        │        estimatedHours: 20,│                         │
     │                        │        dependencies: []   │                         │
     │                        │      },                   │                         │
     │                        │      // ... 14 more       │                         │
     │                        │    ],                     │                         │
     │                        │    summary: "Here's..."   │                         │
     │                        │  }                        │                         │
     │                        │                           │                         │
     │  9. Display preview    │                           │                         │
     │<────────────────────────                           │                         │
     │  [Show task cards]     │                           │                         │
     │                        │                           │                         │
     │  10. User approves     │                           │                         │
     │      plan              │                           │                         │
     ├────────────────────────>                           │                         │
     │  POST /api/tasks/bulk  │                           │                         │
     │  {                     │                           │                         │
     │    planId: "conv-uuid",│                           │                         │
     │    tasks: [...]        │                           │                         │
     │  }                     │                           │                         │
     │                        │                           │                         │
     │                        │  11. Batch insert tasks   │                         │
     │                        │      into DB              │                         │
     │                        │<─────                     │                         │
     │                        │  prisma.task.createMany() │                         │
     │                        │                           │                         │
     │                        │  12. Mark conversation    │                         │
     │                        │      complete             │                         │
     │                        │<─────                     │                         │
     │                        │                           │                         │
     │  13. Return success    │                           │                         │
     │<────────────────────────                           │                         │
     │  {created: 15}         │                           │                         │
     │                        │                           │                         │
     │  14. Redirect to       │                           │                         │
     │      Kanban board      │                           │                         │
     │<────────────────────────                           │                         │
     │                        │                           │                         │
```

### 4.2 Task Dependency Resolution

When tasks have dependencies, the system must calculate proper due dates:

```
Task Dependencies Example:
A: Script Writing (5 days)
B: Video Recording (3 days) [depends on A]
C: Video Editing (4 days) [depends on B]
D: Thumbnail Creation (1 day) [depends on A]
E: Publishing (1 day) [depends on C, D]

Timeline:
Day 1-5:   A (Script Writing)
Day 6-8:   B (Video Recording) | D (Thumbnail Creation in parallel)
Day 9-12:  C (Video Editing)
Day 13:    E (Publishing)

Database Representation:
Task A: { id: "a", dueDate: "Day 5", dependsOn: [] }
Task B: { id: "b", dueDate: "Day 8", dependsOn: ["a"] }
Task C: { id: "c", dueDate: "Day 12", dependsOn: ["b"] }
Task D: { id: "d", dueDate: "Day 6", dependsOn: ["a"] }
Task E: { id: "e", dueDate: "Day 13", dependsOn: ["c", "d"] }
```

**Algorithm (Python Agent):**
```python
def calculate_due_dates(tasks: List[Task], start_date: datetime) -> List[Task]:
    """
    Calculate due dates respecting dependencies.
    Note: Tasks follow single-level hierarchy - subtasks cannot have their own subtasks.
    """
    task_map = {t.id: t for t in tasks}
    completion_dates = {}
    
    # Process tasks in dependency order (topological sort)
    sorted_tasks = topological_sort(tasks)
    
    for task in sorted_tasks:
        # Calculate earliest start based on dependencies
        if not task.depends_on:
            earliest_start = start_date
        else:
            # All dependencies are guaranteed to be in completion_dates due to topological sort
            dep_completion_dates = [
                completion_dates[dep_id] 
                for dep_id in task.depends_on
            ]
            earliest_start = max(dep_completion_dates)
        
        duration = timedelta(hours=task.estimated_hours)
        task.due_date = earliest_start + duration
        completion_dates[task.id] = task.due_date
    
    return tasks
```

---

## 5. Rate Limiting Flow

### 5.1 Token Usage Tracking

```
┌─────────┐              ┌──────────┐              ┌────────────┐
│ Browser │              │ Next.js  │              │   Python   │
└────┬────┘              └────┬─────┘              └──────┬─────┘
     │                        │                           │
     │  1. Send message       │                           │
     ├────────────────────────>                           │
     │                        │                           │
     │                        │  2. Forward to Python     │
     │                        ├───────────────────────────>
     │                        │                           │
     │                        │                           │  3. Check rate limit
     │                        │                           │     SELECT daily_usage
     │                        │                           │     FROM users
     │                        │                           │     WHERE id=...
     │                        │                           │<─────
     │                        │                           │
     │                        │                           │  IF usage > 50:
     │                        │                           │     RETURN error
     │                        │                           │
     │                        │                           │  4. Increment counter
     │                        │                           │     UPDATE users
     │                        │                           │     SET daily_usage += 1
     │                        │                           │<─────
     │                        │                           │
     │                        │                           │  5. Call LLM
     │                        │                           ├───────> [LLM API]
     │                        │                           │
     │                        │                           │  6. Track tokens used
     │                        │                           │<─────
     │                        │                           │  completion.usage
     │                        │                           │
     │                        │                           │  7. Update totals
     │                        │                           │     UPDATE users
     │                        │                           │     SET lifetime_tokens
     │                        │                           │         += tokens_used
     │                        │                           │<─────
     │                        │                           │
     │                        │  8. Return response       │
     │                        │<───────────────────────────
     │  9. Display message    │
     │<────────────────────────
     │
```

### 5.2 Daily Reset Logic

```python
# Python Agent - rate_limiter.py
from datetime import datetime, timezone
from sqlalchemy import update

async def check_and_reset_daily_limit(user_id: str, db_session):
    """Reset daily counter if it's a new day"""
    
    user = await db_session.execute(
        select(User).where(User.id == user_id)
    )
    user = user.scalar_one()
    
    today = datetime.now(timezone.utc).date()
    last_message_date = user.daily_message_date.date() if user.daily_message_date else None
    
    if last_message_date != today:
        # New day - reset counter
        await db_session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                daily_message_count=0,
                daily_message_date=datetime.now(timezone.utc)
            )
        )
        await db_session.commit()
        return 0
    
    return user.daily_message_count
```

---

## 6. Error Handling Flows

### 6.1 LLM API Failure

```
┌────────────┐              ┌──────────┐
│   Python   │              │   LLM    │
│   Agent    │              │   API    │
└──────┬─────┘              └────┬─────┘
       │                         │
       │  1. Request             │
       ├─────────────────────────>
       │                         │
       │  2. 429 Rate Limit      │
       │<─────────────────────────
       │                         │
       │  3. Wait (exponential   │
       │     backoff: 1s)        │
       │                         │
       │  4. Retry request       │
       ├─────────────────────────>
       │                         │
       │  5. 429 Again           │
       │<─────────────────────────
       │                         │
       │  6. Wait (2s)           │
       │                         │
       │  7. Retry request       │
       ├─────────────────────────>
       │                         │
       │  8. 200 Success         │
       │<─────────────────────────
       │                         │
```

**Retry Logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def call_llm_with_retry(prompt: str, model: str):
    """Call LLM with automatic retry"""
    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response
    except openai.RateLimitError as e:
        logger.warning(f"Rate limit hit, retrying: {e}")
        raise  # Retry
    except openai.APIError as e:
        logger.error(f"API error: {e}")
        raise  # Retry
```

### 6.2 Database Connection Loss

```
┌──────────┐              ┌────────────┐              ┌──────────┐
│ Next.js  │              │   Python   │              │   DB     │
└────┬─────┘              └──────┬─────┘              └────┬─────┘
     │                           │                         │
     │  1. Request               │                         │
     ├───────────────────────────>                         │
     │                           │                         │
     │                           │  2. Query               │
     │                           ├─────────────────────────>
     │                           │                         X
     │                           │  3. Connection Error    
     │                           │<─────────────────────────
     │                           │                         
     │                           │  4. Detect disconnection
     │                           │     Try reconnect       
     │                           │                         
     │                           │  5. Create new pool     │
     │                           ├─────────────────────────>
     │                           │                         │
     │                           │  6. Retry query         │
     │                           ├─────────────────────────>
     │                           │                         │
     │                           │  7. Success             │
     │                           │<─────────────────────────
     │                           │                         │
     │  8. Return response       │                         │
     │<───────────────────────────                         │
     │                           │                         │
```

---

## 7. Context File Generation Flow

### 7.1 Markdown File Creation After Onboarding

```
Python Agent Process:

1. Conversation marked complete
   ↓
2. Extract structured data from messages:
   - Parse conversation for key facts
   - Identify channel info, demographics, goals
   ↓
3. Build markdown template:
   """
   # User Context: {user.name}
   
   ## Channel Information
   - **Name:** {channel_name}
   - **Type:** {channel_type}
   - **Topic:** {channel_topic}
   
   ## Demographics
   - **Age Group:** {age_group}
   - **Location:** {location}
   
   ## Content Strategy
   - **Upload Frequency:** {frequency}
   - **Goals:** {goals}
   
   ## Conversation Summary
   {ai_generated_summary}
   """
   ↓
4. Save to filesystem:
   {project_root}/agent_context/{user_id}/context.md
   ↓
5. Update UserContext in database:
   INSERT INTO user_context (
     user_id,
     channel_name,
     channel_type,
     ...
     context_file_path
   )
   ↓
6. Return path to Next.js
```

---

## 8. Multi-Model Orchestration Flow

### 8.1 Dynamic Model Selection

```
User Request
    ↓
┌───────────────────────────────┐
│   Orchestrator                │
│                               │
│  1. Analyze request:          │
│     - Type (onboarding/plan)  │
│     - Context length          │
│     - Complexity              │
│                               │
│  2. Check user's daily usage  │
│                               │
│  3. Select model:             │
│     IF usage > 40/50:         │
│       → GPT-3.5 (cheap)       │
│     ELIF type == "planning":  │
│       → Claude 3.5 (smart)    │
│     ELIF context > 8000 chars:│
│       → Claude 3.5 (long ctx) │
│     ELSE:                     │
│       → GPT-4 (balanced)      │
│                               │
│  4. Route to model client     │
└───────────┬───────────────────┘
            │
            ↓
    ┌───────────────┐
    │  Model Client │
    │  (OpenAI or   │
    │   Anthropic)  │
    └───────┬───────┘
            │
            ↓
        LLM API
```

---

## 9. Conversation Pause/Resume Flow

### 9.1 Pausing Mid-Conversation

```
User Flow:
1. User in middle of onboarding (step 3 of 10)
2. Clicks "I'll finish this later"
3. POST /api/agent/onboarding/pause
   ↓
Python Agent:
4. UPDATE conversations
   SET status = 'PAUSED'
   WHERE id = conversationId
   ↓
5. UPDATE users
   SET onboarding_step = 'demographics'
   WHERE id = userId
   ↓
6. Return {paused: true}

User Returns Later:
1. Login to dashboard
2. System checks: onboardingCompleted = false
3. Query: SELECT * FROM conversations
   WHERE userId = ... AND status = 'PAUSED'
   ↓
4. Display resume button:
   "Continue where you left off?"
   ↓
5. POST /api/agent/onboarding/resume
   {conversationId: "uuid"}
   ↓
Python Agent:
6. Load conversation history
7. Generate contextual message:
   "Welcome back! We were discussing your demographics..."
8. UPDATE status = 'ACTIVE'
9. Continue conversation
```

---

## 10. Task Completion Cascade Flow

### 10.1 Completing Parent Task with Subtasks

```
User Action: Mark parent task as COMPLETED

Next.js API Flow:
1. PUT /api/tasks/{parentId}
   { status: "COMPLETED" }
   ↓
2. Load task with subtasks:
   prisma.task.findUnique({
     where: { id: parentId },
     include: { subtasks: true }
   })
   ↓
3. Check subtasks:
   incomplete_subtasks = subtasks.filter(s => s.status !== 'COMPLETED')
   ↓
4. IF incomplete_subtasks.length > 0:
   → Return error: "Complete all subtasks first"
   → Display list of incomplete subtasks
   ↓
5. ELSE:
   → UPDATE task
     SET status = 'COMPLETED',
         completedAt = NOW()
   → Return success
   ↓
6. Check if this task is a dependency:
   dependent_tasks = prisma.task.findMany({
     where: { dependsOn: { some: { id: parentId } } }
   })
   ↓
7. FOR EACH dependent_task:
   → Check if ALL dependencies are complete
   → IF yes: Send notification "Task X is now available"
```

### 10.2 Task Hierarchy Validation

**Rule: Single-level hierarchy only - subtasks cannot have children**

```
Creating a New Task:

Next.js API Flow:
1. POST /api/tasks
   { title, parentId?, ... }
   ↓
2. IF parentId is provided:
   → Load parent task:
     parent = prisma.task.findUnique({
       where: { id: parentId },
       select: { parentId: true }
     })
   ↓
3. Validate hierarchy:
   IF parent.parentId !== null:
   → Return 400 Bad Request: 
     "Cannot create subtask - parent is already a subtask. 
      Only one level of nesting is allowed."
   ↓
4. ELSE:
   → Proceed with task creation
   → prisma.task.create({
       data: { title, parentId, ... }
     })
```

**Example Validation:**
```typescript
// Valid: Top-level task with subtasks
Task A (parentId: null)
  ├─ Subtask B (parentId: A.id) ✓ Allowed
  └─ Subtask C (parentId: A.id) ✓ Allowed

// Invalid: Subtask trying to have children
Task A (parentId: null)
  └─ Subtask B (parentId: A.id)
      └─ Subtask C (parentId: B.id) ✗ BLOCKED
```

---

## Appendices

### A. Database Transaction Patterns

**Pattern 1: Atomic Conversation Update**
```typescript
await prisma.$transaction([
  prisma.conversation.update({
    where: { id: conversationId },
    data: {
      messages: newMessages,
      totalTokensUsed: { increment: tokensUsed }
    }
  }),
  prisma.user.update({
    where: { id: userId },
    data: {
      lifetimeTokensUsed: { increment: tokensUsed }
    }
  })
]);
```

**Pattern 2: Bulk Task Creation**
```typescript
await prisma.task.createMany({
  data: tasks.map(t => ({
    ...t,
    userId,
    planId: conversationId,
    generatedByAI: true
  }))
});
```

### B. WebSocket Heartbeat

```typescript
// Keep connection alive
setInterval(() => {
  socket.send(JSON.stringify({ type: 'ping' }));
}, 30000); // Every 30 seconds

socket.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.type === 'pong') {
    // Connection is alive
  }
});
```

### C. Error Codes Reference

| Code | Description | Recovery Action |
|------|-------------|-----------------|
| `RATE_LIMIT_EXCEEDED` | User exceeded daily message limit | Display remaining quota, suggest retry tomorrow |
| `LLM_API_ERROR` | OpenAI/Claude API failure | Retry with exponential backoff, switch to fallback model |
| `INVALID_CONVERSATION` | Conversation not found | Start new conversation |
| `WEBSOCKET_DISCONNECTED` | Connection lost | Auto-reconnect, resume from last message |
| `INTERNAL_SECRET_INVALID` | Service auth failed | Log security alert, return 401 |
| `TOKEN_COUNT_ERROR` | Failed to count tokens | Use estimate, log warning |
