# Implementation Plan
## Content Creator Planner - AI Agent System

**Version:** 1.0  
**Date:** January 7, 2026  
**Timeline:** 4 weeks (Jan 7 - Feb 4, 2026)

---

## Overview

This document provides a week-by-week implementation plan for integrating AI agents into the Content Creator Planner. The plan is designed to deliver incremental value while maintaining a functional system throughout development.

---

## Week 1: Infrastructure Setup
**Dates:** January 7-13, 2026  
**Goal:** Establish foundational infrastructure for Python agent service

### Day 1-2: Database Schema Updates

**Tasks:**
- [ ] Update Prisma schema with new models
  - Add `Conversation` model
  - Add `UserContext` model
  - Add new fields to `User` model (onboarding tracking, usage stats)
  - Add new fields to `Task` model (AI generation tracking)
  - Add task dependency relations

**Files to modify:**
- `prisma/schema.prisma`

**Commands:**
```bash
# Inside Docker container
docker exec -it content-planner-app npx prisma format
docker exec -it content-planner-app npx prisma migrate dev --name add_ai_agent_models
docker exec -it content-planner-app npx prisma generate
```

**Acceptance Criteria:**
- ✅ Migration runs successfully
- ✅ All models created in database
- ✅ Prisma Client regenerated
- ✅ Existing data preserved (users, tasks)

---

### Day 3: Python FastAPI Project Setup

**Tasks:**
- [ ] Create `python-agents/` directory structure
- [ ] Set up Python virtual environment
- [ ] Create `requirements.txt` with dependencies
- [ ] Implement basic FastAPI application
- [ ] Create Dockerfile for Python service
- [ ] Update `docker-compose.yml` to include Python service

**Directory Structure:**
```
python-agents/
├── main.py
├── requirements.txt
├── Dockerfile
├── .env.example
├── config/
│   ├── __init__.py
│   └── settings.py
├── agents/
│   ├── __init__.py
│   └── base.py
├── models/
│   ├── __init__.py
│   └── openai_client.py
├── api/
│   ├── __init__.py
│   └── routes.py
├── storage/
│   ├── __init__.py
│   └── conversation.py
├── schemas/
│   ├── __init__.py
│   ├── requests.py
│   └── responses.py
└── utils/
    ├── __init__.py
    └── logger.py
```

**requirements.txt:**
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0
openai==1.12.0
anthropic==0.18.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.25
websockets==12.0
tenacity==8.2.3
```

**Acceptance Criteria:**
- ✅ Python service starts successfully
- ✅ FastAPI docs accessible at `http://localhost:8000/docs`
- ✅ Health check endpoint responds
- ✅ Environment variables loaded correctly

---

### Day 4: Service-to-Service Communication

**Tasks:**
- [ ] Create Next.js proxy route: `app/api/agent/[...path]/route.ts`
- [ ] Implement internal authentication middleware in Python
- [ ] Test basic request forwarding
- [ ] Set up shared environment variables

**Next.js Proxy Route:**
```typescript
// app/api/agent/[...path]/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth/helpers';

const PYTHON_AGENT_URL = process.env.PYTHON_AGENT_URL || 'http://python-agent:8000';
const INTERNAL_API_SECRET = process.env.INTERNAL_API_SECRET;

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const token = request.cookies.get('token')?.value;
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  const payload = verifyToken(token);
  if (!payload) {
    return NextResponse.json({ error: 'Invalid token' }, { status: 401 });
  }
  
  const body = await request.json();
  const path = params.path.join('/');
  
  const response = await fetch(`${PYTHON_AGENT_URL}/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Secret': INTERNAL_API_SECRET!,
      'X-User-Id': payload.userId,
      'X-User-Email': payload.email,
    },
    body: JSON.stringify(body),
  });
  
  return response;
}
```

**Python Middleware:**
```python
# api/middleware.py
from fastapi import Header, HTTPException
from config.settings import settings

async def verify_internal_request(
    x_internal_secret: str = Header(None),
    x_user_id: str = Header(None),
    x_user_email: str = Header(None)
):
    if x_internal_secret != settings.INTERNAL_API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing user ID")
    return {
        'user_id': x_user_id,
        'user_email': x_user_email
    }
```

**Acceptance Criteria:**
- ✅ Proxy forwards requests correctly
- ✅ Authentication works end-to-end
- ✅ Python receives user context headers
- ✅ Errors propagate properly

---

### Day 5: Docker Integration & Testing

**Tasks:**
- [ ] Test full Docker Compose stack
- [ ] Verify database connectivity from Python
- [ ] Test hot reload for both services
- [ ] Create development environment documentation

**Updated docker-compose.yml:**
```yaml
services:
  app:
    # ... existing Next.js config ...
    environment:
      - PYTHON_AGENT_URL=http://python-agent:8000
      - INTERNAL_API_SECRET=${INTERNAL_API_SECRET}
    depends_on:
      - db
      - python-agent
  
  python-agent:
    build: ./python-agents
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - INTERNAL_API_SECRET=${INTERNAL_API_SECRET}
      - ENVIRONMENT=development
    volumes:
      - ./agent_context:/app/agent_context
      - ./python-agents:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - db
  
  db:
    # ... existing PostgreSQL config ...
```

**Acceptance Criteria:**
- ✅ All services start with `docker compose up`
- ✅ Python can query PostgreSQL
- ✅ File changes trigger hot reload
- ✅ Environment variables propagate correctly

---

## Week 2: Onboarding Agent MVP
**Dates:** January 14-20, 2026  
**Goal:** Complete conversational onboarding flow

### Day 6-7: Onboarding Agent Logic

**Tasks:**
- [ ] Implement onboarding agent class
- [ ] Create conversation flow state machine
- [ ] Write system prompts for onboarding
- [ ] Implement OpenAI integration
- [ ] Add conversation persistence

**Onboarding Agent Implementation:**
```python
# agents/onboarding.py
from typing import Dict, Optional
from openai import AsyncOpenAI
from storage.conversation import ConversationStorage

class OnboardingAgent:
    def __init__(self, openai_client: AsyncOpenAI, storage: ConversationStorage):
        self.client = openai_client
        self.storage = storage
        self.steps = [
            'welcome',
            'channel_info',
            'channel_details',
            'demographics',
            'content_strategy',
            'goals',
            'completion'
        ]
    
    async def start_conversation(self, user_id: str) -> Dict:
        """Initialize onboarding conversation"""
        conversation_id = await self.storage.create_conversation(
            user_id=user_id,
            type='ONBOARDING'
        )
        
        first_message = await self._generate_welcome_message()
        
        await self.storage.add_message(
            conversation_id=conversation_id,
            role='assistant',
            content=first_message,
            metadata={'step': 'welcome'}
        )
        
        return {
            'conversationId': conversation_id,
            'message': first_message,
            'step': 'channel_info',
            'completed': False
        }
    
    async def process_message(
        self,
        conversation_id: str,
        user_message: str
    ) -> Dict:
        """Process user response and generate next question"""
        
        # Load conversation history
        conversation = await self.storage.get_conversation(conversation_id)
        
        # Append user message
        await self.storage.add_message(
            conversation_id=conversation_id,
            role='user',
            content=user_message
        )
        
        # Extract information from response
        extracted_data = await self._extract_information(
            conversation['messages'],
            user_message
        )
        
        # Determine next step
        current_step = conversation['metadata'].get('currentStep', 'channel_info')
        next_step = self._get_next_step(current_step, extracted_data)
        
        if next_step == 'completion':
            # Generate context file
            await self._generate_context_file(conversation_id, extracted_data)
            return {
                'conversationId': conversation_id,
                'message': 'Perfect! You\'re all set to start planning.',
                'step': 'completed',
                'completed': True
            }
        
        # Generate next question
        next_message = await self._generate_next_question(
            conversation['messages'],
            next_step
        )
        
        await self.storage.add_message(
            conversation_id=conversation_id,
            role='assistant',
            content=next_message,
            metadata={'step': next_step}
        )
        
        return {
            'conversationId': conversation_id,
            'message': next_message,
            'step': next_step,
            'completed': False
        }
    
    async def _generate_welcome_message(self) -> str:
        """Generate personalized welcome message"""
        response = await self.client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {
                    'role': 'system',
                    'content': ONBOARDING_SYSTEM_PROMPT
                },
                {
                    'role': 'user',
                    'content': 'Generate a friendly welcome message for onboarding'
                }
            ]
        )
        return response.choices[0].message.content
```

**System Prompt:**
```python
# config/prompts.py
ONBOARDING_SYSTEM_PROMPT = """You are a friendly onboarding assistant for content creators.
Your goal is to learn about the user's channel, goals, and content strategy through natural conversation.

Guidelines:
- Ask ONE question at a time
- Be conversational and encouraging
- Acknowledge user's responses before asking next question
- Extract structured information (channel name, upload frequency, etc.)
- Keep responses concise (2-3 sentences)

Information to gather:
1. Channel existence (existing or planning to start)
2. Channel name and topic
3. Current status (subscriber count, video count)
4. Demographics (age group, location)
5. Team size
6. Upload frequency
7. Goals and challenges
"""
```

**Acceptance Criteria:**
- ✅ Conversation flows naturally through all steps
- ✅ Agent asks one question at a time
- ✅ Responses saved to database
- ✅ Extracted data structured correctly

---

### Day 8-9: Context File Generation

**Tasks:**
- [ ] Implement context file generation logic
- [ ] Create markdown templates
- [ ] Save structured data to UserContext model
- [ ] Test with various onboarding scenarios

**Context File Generator:**
```python
# storage/user_context.py
import os
from pathlib import Path
from typing import Dict

class UserContextManager:
    def __init__(self, base_path: str = '/app/agent_context'):
        self.base_path = Path(base_path)
    
    async def create_context_file(
        self,
        user_id: str,
        extracted_data: Dict
    ) -> str:
        """Generate markdown context file"""
        
        user_dir = self.base_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        context_path = user_dir / 'context.md'
        
        content = self._build_markdown(extracted_data)
        
        with open(context_path, 'w') as f:
            f.write(content)
        
        return str(context_path)
    
    def _build_markdown(self, data: Dict) -> str:
        """Build markdown from extracted data"""
        return f"""# User Context: {data.get('name', 'Unknown')}

## Channel Information
- **Name:** {data.get('channel_name', 'Not specified')}
- **Type:** {data.get('channel_type', 'Not specified')}
- **Topic:** {data.get('channel_topic', 'Not specified')}
- **Current Status:** {data.get('channel_size', 'New channel')}

## Demographics
- **Age Group:** {data.get('age_group', 'Not specified')}
- **Location:** {data.get('location', 'Not specified')}

## Content Strategy
- **Team:** {'Team of ' + str(data.get('team_size')) if data.get('is_team') else 'Solo creator'}
- **Upload Frequency:** {data.get('upload_frequency', 'Not specified')}
- **Goals:** {data.get('content_goals', 'Not specified')}

## Challenges
{data.get('challenges', 'None mentioned')}

## Additional Notes
{data.get('additional_notes', 'None')}

---
*Generated: {data.get('generated_at')}*
"""
```

**Acceptance Criteria:**
- ✅ Context files created in correct directory
- ✅ Markdown properly formatted
- ✅ All extracted data included
- ✅ Files readable by AI agents

---

### Day 10: Frontend Integration

**Tasks:**
- [ ] Create onboarding UI component
- [ ] Integrate with chat interface
- [ ] Add onboarding completion redirect
- [ ] Test full user flow

**Onboarding Component:**
```typescript
// app/(app)/onboarding/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function OnboardingPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  
  useEffect(() => {
    startOnboarding();
  }, []);
  
  const startOnboarding = async () => {
    const response = await fetch('/api/agent/onboarding/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversationId: null })
    });
    
    const data = await response.json();
    setConversationId(data.conversationId);
    setMessages([{ role: 'assistant', content: data.message }]);
  };
  
  const sendMessage = async () => {
    if (!input.trim() || !conversationId) return;
    
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    setInput('');
    setLoading(true);
    
    const response = await fetch('/api/agent/onboarding/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversationId,
        message: input
      })
    });
    
    const data = await response.json();
    setMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
    setLoading(false);
    
    if (data.completed) {
      // Redirect to dashboard after 2 seconds
      setTimeout(() => router.push('/'), 2000);
    }
  };
  
  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Welcome! Let's set up your profile</h1>
      
      <div className="space-y-4 mb-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-4 rounded-lg ${
              msg.role === 'user' 
                ? 'bg-blue-100 ml-auto max-w-[80%]'
                : 'bg-gray-100 mr-auto max-w-[80%]'
            }`}
          >
            {msg.content}
          </div>
        ))}
      </div>
      
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type your response..."
          disabled={loading}
          className="flex-1 p-2 border rounded"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- ✅ UI displays conversation naturally
- ✅ Messages send and receive correctly
- ✅ Redirect works on completion
- ✅ Mobile-responsive design

---

## Week 3: Planning Agent & Task Generation
**Dates:** January 21-27, 2026  
**Goal:** AI-powered content planning with task generation

### Day 11-12: Planning Agent Logic

**Tasks:**
- [ ] Implement planning agent class
- [ ] Integrate Claude 3.5 for complex reasoning
- [ ] Create planning system prompts
- [ ] Test with various user contexts

**Planning Agent:**
```python
# agents/planner.py
from typing import Dict, List
from anthropic import AsyncAnthropic
from storage.conversation import ConversationStorage
from storage.user_context import UserContextManager

class PlanningAgent:
    def __init__(
        self,
        anthropic_client: AsyncAnthropic,
        storage: ConversationStorage,
        context_manager: UserContextManager
    ):
        self.client = anthropic_client
        self.storage = storage
        self.context_manager = context_manager
    
    async def generate_plan(
        self,
        user_id: str,
        timeframe: str,
        video_count: int
    ) -> Dict:
        """Generate content plan based on user context"""
        
        # Load user context
        context_content = await self.context_manager.load_context_file(user_id)
        
        # Create planning conversation
        conversation_id = await self.storage.create_conversation(
            user_id=user_id,
            type='PLANNING'
        )
        
        # Generate plan using Claude
        prompt = self._build_planning_prompt(
            context_content,
            timeframe,
            video_count
        )
        
        response = await self.client.messages.create(
            model='claude-3-5-sonnet-20240620',
            max_tokens=4096,
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        )
        
        # Parse structured plan from response
        plan = self._parse_plan(response.content[0].text)
        
        # Save conversation
        await self.storage.add_message(
            conversation_id=conversation_id,
            role='assistant',
            content=response.content[0].text,
            metadata={'plan': plan}
        )
        
        return {
            'conversationId': conversation_id,
            'plan': plan,
            'summary': self._generate_summary(plan)
        }
    
    def _build_planning_prompt(
        self,
        context: str,
        timeframe: str,
        video_count: int
    ) -> str:
        """Build planning prompt with context"""
        return f"""Based on the following user context, create a strategic content plan.

{context}

Requirements:
- Timeframe: {timeframe}
- Number of videos: {video_count}
- Consider upload frequency from context
- Create realistic task breakdowns
- Identify dependencies between tasks

For each video idea, provide:
1. Title (engaging and SEO-friendly)
2. Description (detailed concept)
3. Priority (HIGH, MEDIUM, LOW)
4. Estimated hours for completion
5. Subtasks (research, script, record, edit, thumbnail, publish)
6. Dependencies (which videos should come first)
7. Reasoning (why this topic fits their channel)

Format response as JSON array of task objects.
"""
```

**Acceptance Criteria:**
- ✅ Plans generated match user context
- ✅ Task dependencies logical
- ✅ Estimated hours reasonable
- ✅ JSON parsing works reliably

---

### Day 13-14: Task Dependency & Due Date Calculation

**Tasks:**
- [ ] Implement topological sort for dependencies
- [ ] Calculate due dates based on dependencies
- [ ] Add task relationship management
- [ ] Test complex dependency chains

**Dependency Resolution:**
```python
# utils/task_scheduler.py
from datetime import datetime, timedelta
from typing import List, Dict
from collections import deque

class TaskScheduler:
    def calculate_schedule(
        self,
        tasks: List[Dict],
        start_date: datetime,
        upload_frequency: str
    ) -> List[Dict]:
        """Calculate due dates respecting dependencies"""
        
        # Build dependency graph
        task_map = {t['id']: t for t in tasks}
        completion_dates = {}
        
        # Topological sort
        sorted_tasks = self._topological_sort(tasks)
        
        for task in sorted_tasks:
            # Find earliest start date
            earliest_start = start_date
            
            if task.get('dependencies'):
                dep_dates = [
                    completion_dates[dep_id]
                    for dep_id in task['dependencies']
                ]
                earliest_start = max(dep_dates)
            
            # Calculate duration
            duration = timedelta(hours=task['estimatedHours'])
            task['dueDate'] = earliest_start + duration
            completion_dates[task['id']] = task['dueDate']
        
        return sorted_tasks
    
    def _topological_sort(self, tasks: List[Dict]) -> List[Dict]:
        """Sort tasks in dependency order"""
        graph = {t['id']: t.get('dependencies', []) for t in tasks}
        in_degree = {t['id']: 0 for t in tasks}
        
        # Calculate in-degrees
        for deps in graph.values():
            for dep in deps:
                in_degree[dep] += 1
        
        # Queue tasks with no dependencies
        queue = deque([t for t in tasks if in_degree[t['id']] == 0])
        result = []
        
        while queue:
            task = queue.popleft()
            result.append(task)
            
            for dep in graph[task['id']]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(next(t for t in tasks if t['id'] == dep))
        
        return result
```

**Acceptance Criteria:**
- ✅ Dependencies resolved correctly
- ✅ No circular dependencies
- ✅ Due dates respect upload frequency
- ✅ Parallel tasks scheduled efficiently

---

### Day 15: Bulk Task Creation Endpoint

**Tasks:**
- [ ] Create `/api/tasks/bulk` endpoint
- [ ] Implement batch insert with Prisma
- [ ] Add task relationship creation
- [ ] Test with 20+ task plans

**Bulk Task Endpoint:**
```typescript
// app/api/tasks/bulk/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { verifyToken } from '@/lib/auth/helpers';

export async function POST(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  const payload = verifyToken(token);
  if (!payload) {
    return NextResponse.json({ error: 'Invalid token' }, { status: 401 });
  }
  
  const { planId, tasks } = await request.json();
  
  if (tasks.length > 50) {
    return NextResponse.json(
      { error: 'Maximum 50 tasks per request' },
      { status: 413 }
    );
  }
  
  try {
    // Create tasks with dependencies
    const createdTasks = await prisma.$transaction(async (tx) => {
      const taskRecords = [];
      
      for (const task of tasks) {
        const created = await tx.task.create({
          data: {
            title: task.title,
            description: task.description,
            status: 'TODO',
            priority: task.priority,
            dueDate: new Date(task.dueDate),
            estimatedHours: task.estimatedHours,
            generatedByAI: true,
            planId,
            userId: payload.userId,
            aiReasoning: task.reasoning
          }
        });
        taskRecords.push(created);
      }
      
      // Add dependencies after all tasks created
      // (requires mapping temporary IDs to real IDs)
      
      return taskRecords;
    });
    
    return NextResponse.json({
      created: createdTasks.length,
      taskIds: createdTasks.map(t => t.id),
      planId
    }, { status: 201 });
    
  } catch (error) {
    console.error('Bulk task creation failed:', error);
    return NextResponse.json(
      { error: 'Failed to create tasks' },
      { status: 500 }
    );
  }
}
```

**Acceptance Criteria:**
- ✅ Creates 15+ tasks in <2 seconds
- ✅ Dependencies linked correctly
- ✅ Transaction rolls back on error
- ✅ Returns created task IDs

---

## Week 4: Polish, Rate Limiting & Testing
**Dates:** January 28 - February 4, 2026  
**Goal:** Production-ready system with monitoring

### Day 16-17: WebSocket Streaming

**Tasks:**
- [ ] Implement WebSocket endpoint in Python
- [ ] Add streaming support for LLM responses
- [ ] Create Next.js WebSocket server
- [ ] Build streaming chat UI

**Python WebSocket Handler:**
```python
# api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_token(self, user_id: str, token: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json({
                'type': 'token',
                'content': token
            })

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    user_id = None
    try:
        await websocket.accept()
        
        # Authenticate
        auth_message = await websocket.receive_json()
        user_id = auth_message.get('userId')
        
        await manager.connect(websocket, user_id)
        
        while True:
            data = await websocket.receive_json()
            
            if data['type'] == 'message':
                # Stream response
                async for token in generate_streaming_response(
                    data['conversationId'],
                    data['content']
                ):
                    await manager.send_token(user_id, token)
                
                await websocket.send_json({
                    'type': 'done',
                    'messageId': '...'
                })
    
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id)
```

**Acceptance Criteria:**
- ✅ Tokens stream in real-time
- ✅ Connection handles disconnects
- ✅ Reconnection works automatically
- ✅ Mobile browsers supported

---

### Day 18: Rate Limiting & Cost Control

**Tasks:**
- [ ] Implement rate limiting in Python
- [ ] Add token counting
- [ ] Create usage tracking dashboard
- [ ] Set up alerts for high usage

**Rate Limiter:**
```python
# storage/rate_limiter.py
from datetime import datetime, timezone
from sqlalchemy import select, update
from models.user import User

class RateLimiter:
    def __init__(self, db_session):
        self.db = db_session
        self.limits = {
            'daily_messages': 50,
            'daily_tokens': 100000
        }
    
    async def check_limit(self, user_id: str) -> bool:
        """Check if user is within limits"""
        user = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalar_one()
        
        # Reset if new day
        if self._is_new_day(user.daily_message_date):
            await self._reset_daily_counters(user_id)
            return True
        
        # Check limits
        if user.daily_message_count >= self.limits['daily_messages']:
            return False
        
        return True
    
    async def increment_usage(
        self,
        user_id: str,
        tokens_used: int
    ):
        """Increment usage counters"""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                daily_message_count=User.daily_message_count + 1,
                lifetime_tokens_used=User.lifetime_tokens_used + tokens_used,
                daily_message_date=datetime.now(timezone.utc)
            )
        )
        await self.db.commit()
```

**Acceptance Criteria:**
- ✅ Users blocked at 50 messages/day
- ✅ Counters reset at midnight
- ✅ Token usage tracked accurately
- ✅ Admin can adjust limits

---

### Day 19: Error Handling & Logging

**Tasks:**
- [ ] Add comprehensive error handling
- [ ] Implement structured logging
- [ ] Create error recovery mechanisms
- [ ] Test edge cases

**Error Handler:**
```python
# utils/error_handler.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def error_handler(request: Request, exc: Exception):
    """Global error handler"""
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                'error': {
                    'code': exc.detail,
                    'message': str(exc),
                    'timestamp': datetime.now().isoformat()
                }
            }
        )
    
    # Log unexpected errors
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            'user_id': request.headers.get('X-User-Id'),
            'path': request.url.path,
            'method': request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred'
            }
        }
    )
```

**Acceptance Criteria:**
- ✅ All errors logged with context
- ✅ User-friendly error messages
- ✅ Retries on transient failures
- ✅ Alerts on critical errors

---

### Day 20: End-to-End Testing

**Tasks:**
- [ ] Write integration tests
- [ ] Test complete user journeys
- [ ] Performance testing
- [ ] Security audit

**Test Scenarios:**
1. **Happy Path:**
   - New user signup → Onboarding → Plan generation → Task creation
   
2. **Error Cases:**
   - Network failures
   - LLM API errors
   - Rate limit exceeded
   - Invalid input data

3. **Performance:**
   - 100 concurrent WebSocket connections
   - Planning for 50 tasks
   - Database query optimization

4. **Security:**
   - JWT validation
   - Internal API authentication
   - SQL injection prevention
   - XSS protection

**Acceptance Criteria:**
- ✅ All user flows work end-to-end
- ✅ System handles 100 concurrent users
- ✅ No security vulnerabilities
- ✅ Error recovery functional

---

## Deployment Checklist

### Pre-Launch
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] SSL certificates installed
- [ ] Monitoring set up
- [ ] Backup strategy implemented
- [ ] Rate limits configured
- [ ] API keys secured

### Launch Day
- [ ] Deploy Python service
- [ ] Deploy Next.js application
- [ ] Verify health checks
- [ ] Test production endpoints
- [ ] Monitor error rates
- [ ] Check database connections

### Post-Launch
- [ ] Monitor token usage
- [ ] Track user onboarding completion
- [ ] Analyze conversation quality
- [ ] Gather user feedback
- [ ] Optimize prompts based on results

---

## Success Metrics

### Week 1 (Infrastructure)
- ✅ Docker stack starts successfully
- ✅ Services communicate properly
- ✅ Database migrations complete
- ✅ Authentication works end-to-end

### Week 2 (Onboarding)
- ✅ 80%+ onboarding completion rate
- ✅ Average conversation: 8-12 messages
- ✅ Context files generated correctly
- ✅ User satisfaction > 4/5

### Week 3 (Planning)
- ✅ Plans generated in <10 seconds
- ✅ 70%+ plan acceptance rate
- ✅ Dependencies calculated correctly
- ✅ Tasks appear in Kanban board

### Week 4 (Production Ready)
- ✅ <1% error rate
- ✅ Response time <2s (p95)
- ✅ Rate limiting functional
- ✅ Ready for 100 users

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| OpenAI API downtime | Implement fallback to Claude, queue system |
| High token costs | Strict rate limits, cheaper models for simple tasks |
| Poor AI responses | Collect feedback, iterate on prompts |
| Slow response times | Implement caching, optimize prompts |
| Database bottlenecks | Connection pooling, query optimization |
| User confusion | Clear UI, help documentation, examples |

---

## Post-MVP Roadmap

### Phase 2 (Weeks 5-8)
- Voice input/output
- Calendar integration
- Team collaboration features
- Analytics dashboard

### Phase 3 (Months 3-6)
- Mobile apps
- Advanced planning (competitive analysis)
- Script generation
- Thumbnail suggestions

---

**Document Status:** Living Document  
**Last Updated:** January 7, 2026  
**Next Review:** End of Week 1 (January 13, 2026)
