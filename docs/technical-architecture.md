# Technical Architecture Document
## Content Creator Planner - AI Agent System

**Version:** 1.0  
**Date:** January 7, 2026  
**Author:** Engineering Team

---

## 1. System Overview

### Architecture Pattern
**Hybrid Microservices Architecture** with two primary services:
1. **Next.js Application** (existing) - Frontend + Backend API
2. **Python Agent Service** (new) - AI/ML workload handler

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    Next.js App Router                        │
│              (React, TypeScript, Tailwind)                   │
│                                                              │
│  • Task Management UI                                        │
│  • Chat Interface (WebSocket client)                         │
│  • Kanban Board                                              │
│  • Calendar View                                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ↓ HTTP/REST + WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Backend                           │
│               (Node.js 18, TypeScript)                       │
│                                                              │
│  • JWT Authentication                                        │
│  • Task CRUD Operations                                      │
│  • User Management                                           │
│  • Proxy to Python Agent Service                            │
│  • WebSocket Server (Socket.io)                             │
└─────────┬───────────────────────────────┬───────────────────┘
          │                               │
          ↓                               ↓
    ┌─────────────┐          ┌────────────────────────────────┐
    │ PostgreSQL  │          │     Python Agent Service       │
    │  Database   │          │        (FastAPI + uvicorn)     │
    │             │          │                                │
    │  • Users    │←─────────│  • Onboarding Agent            │
    │  • Tasks    │          │  • Planning Agent              │
    │  • Convos   │          │  • Model Orchestrator          │
    │  • Context  │          │  • WebSocket Handler           │
    └─────────────┘          └────────────┬───────────────────┘
                                          │
                                          ↓ HTTPS API Calls
                             ┌────────────────────────────────┐
                             │    External AI Services        │
                             │                                │
                             │  • OpenAI API (GPT-4/3.5)      │
                             │  • Anthropic API (Claude 3.5)  │
                             └────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Next.js Application (Existing + Extensions)

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | Next.js | 16 | Full-stack React framework |
| **Runtime** | Node.js | 18 | JavaScript runtime |
| **Language** | TypeScript | 5.x | Type-safe development |
| **ORM** | Prisma | Latest | Database abstraction |
| **Database** | PostgreSQL | 15 | Primary data store |
| **Auth** | JWT (jsonwebtoken) | Latest | Token-based authentication |
| **Styling** | Tailwind CSS | 4.x | Utility-first CSS |
| **WebSocket** | Socket.io | 4.x | Real-time bidirectional communication |
| **HTTP Client** | Fetch API | Native | Service-to-service calls |

### 2.2 Python Agent Service (New)

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | FastAPI | 0.109+ | Async web framework |
| **Runtime** | Python | 3.11+ | Language runtime |
| **ASGI Server** | Uvicorn | Latest | Production server |
| **LLM SDK** | OpenAI Python SDK | 1.12+ | OpenAI API client |
| **LLM SDK** | Anthropic SDK | 0.18+ | Claude API client |
| **WebSocket** | FastAPI WebSocket | Built-in | Real-time streaming |
| **Validation** | Pydantic | 2.x | Data validation |
| **ORM** | SQLAlchemy (optional) | 2.x | Direct DB access if needed |
| **HTTP Client** | httpx | Latest | Async HTTP requests |

### 2.3 Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Container** | Docker | Service isolation |
| **Orchestration** | Docker Compose | Local development |
| **Reverse Proxy** | (Future) Nginx/Traefik | Production routing |
| **File Storage** | Local filesystem | User context markdown files |

---

## 3. Design Decisions & Rationale

### 3.1 Why Separate Python Service?

**Decision:** Create standalone Python service instead of Next.js API routes

**Rationale:**
1. **Language Fit:** Python has superior AI/ML ecosystem (LangChain, Transformers, rich LLM SDKs)
2. **Independent Scaling:** Agent service can scale separately based on LLM workload
3. **Development Velocity:** AI engineers can work in Python without Next.js knowledge
4. **Library Support:** OpenAI, Anthropic, and future libraries are Python-first
5. **Async Performance:** FastAPI's async support ideal for I/O-bound LLM calls

**Trade-offs Accepted:**
- ❌ Additional deployment complexity (2 services instead of 1)
- ❌ Network latency between services (~5-10ms)
- ❌ Need service-to-service authentication

---

### 3.2 Database Architecture

**Decision:** Single PostgreSQL database shared by both services

**Rationale:**
1. **Data Consistency:** Avoid sync issues between separate databases
2. **Simplicity:** One migration system (Prisma)
3. **Cost:** Single database instance in production
4. **Transaction Support:** Can use DB transactions across entities

**Schema Design Principles:**
- **User-centric:** All data tied to User model
- **Audit trail:** `createdAt`, `updatedAt` on critical tables
- **Soft deletes:** Use `deletedAt` for user data (future)
- **JSON flexibility:** Use Json type for unstructured data (conversation messages, metadata)

---

### 3.3 Real-Time Communication Strategy

**Decision:** WebSocket with streaming responses

**Rationale:**
1. **User Expectation:** Modern AI interfaces (ChatGPT, Claude) stream responses
2. **Perceived Performance:** Users see first token in ~1-2 seconds vs waiting 10+ seconds
3. **Engagement:** Streaming creates sense of AI "thinking" which builds trust
4. **Mobile Support:** WebSocket works well on mobile with reconnection logic

**Implementation Approach:**
```
User Browser ←→ Next.js (Socket.io) ←→ Python FastAPI (WebSocket)
```

**Flow:**
1. User connects WebSocket to Next.js server
2. Next.js authenticates user via JWT
3. Next.js opens WebSocket to Python service
4. Python streams LLM tokens back through Next.js to user
5. Next.js saves complete message to database after stream ends

---

### 3.4 Context Storage Strategy

**Decision:** Hybrid storage (Database + Markdown files)

**Structured Data (Database):**
```prisma
model UserContext {
  userId          String @unique
  channelName     String?
  uploadFrequency String?
  isTeam          Boolean
  // ... 10-15 specific fields
}
```

**Unstructured Summary (Files):**
```
user_context/
  {userId}/
    context.md         # Main context file for AI consumption
    onboarding.json    # Raw conversation backup
    planning_history/  # Previous planning sessions
```

**Rationale:**
1. **Database for queries:** Fast filtering (e.g., "all users who upload weekly")
2. **Markdown for AI:** LLMs work best with natural language context
3. **Human readability:** Users can read/edit their context.md
4. **Backup:** JSON files preserve exact conversation history

---

### 3.5 AI Model Selection Strategy

**Decision:** Multi-model orchestrator with cost-based routing

**Model Characteristics:**

| Model | Cost per 1M Tokens | Use Cases |
|-------|-------------------|-----------|
| GPT-3.5 Turbo | $0.50 input / $1.50 output | Simple questions, clarifications |
| GPT-4 Turbo | $10 input / $30 output | Complex planning, nuanced understanding |
| Claude 3.5 Sonnet | $3 input / $15 output | Research, long context, creative tasks |

**Routing Logic:**
```python
def select_model(task_type: str, context_length: int) -> str:
    if task_type == "onboarding_initial":
        return "gpt-3.5-turbo"  # Simple questions
    elif task_type == "onboarding_final":
        return "gpt-4"  # Nuanced understanding
    elif task_type == "planning" and context_length > 8000:
        return "claude-3.5-sonnet"  # Long context
    elif task_type == "planning":
        return "gpt-4"  # Complex reasoning
    else:
        return "gpt-3.5-turbo"  # Default to cheap
```

**Cost Optimization:**
- Cache common prompts (system prompts, examples)
- Truncate conversation history to last N messages
- Use streaming to detect and stop low-quality responses early

---

## 4. Data Models

### 4.1 Prisma Schema Extensions

```prisma
// Existing User model - ADD these fields
model User {
  id                    String   @id @default(uuid())
  email                 String   @unique
  password              String
  name                  String
  createdAt             DateTime @default(now())
  
  // NEW: Onboarding tracking
  onboardingCompleted   Boolean  @default(false)
  onboardingStep        String?  // Current step if incomplete
  onboardingCompletedAt DateTime?
  
  // NEW: Usage tracking
  dailyMessageCount     Int      @default(0)
  dailyMessageDate      DateTime?
  lifetimeTokensUsed    Int      @default(0)
  
  // Relations
  tasks                 Task[]
  conversations         Conversation[]
  userContext           UserContext?
}

// Existing Task model - ADD these fields
model Task {
  id                    String   @id @default(uuid())
  title                 String
  description           String?  @db.Text
  status                TaskStatus @default(TODO)
  priority              TaskPriority @default(MEDIUM)
  dueDate               DateTime?
  estimatedHours        Float?
  actualHours           Float?
  completedAt           DateTime?
  createdAt             DateTime @default(now())
  updatedAt             DateTime @updatedAt
  
  // Hierarchical structure (existing)
  parentId              String?
  parent                Task?    @relation("TaskHierarchy", fields: [parentId], references: [id])
  subtasks              Task[]   @relation("TaskHierarchy")
  
  // NEW: AI-generated task tracking
  generatedByAI         Boolean  @default(false)
  planId                String?  // Group tasks from same planning session
  researchNotes         String?  @db.Text
  aiSuggestions         String?  @db.Text
  aiReasoning           String?  @db.Text // Why AI suggested this task
  
  // NEW: Dependencies (many-to-many)
  dependsOn             Task[]   @relation("TaskDependencies")
  requiredFor           Task[]   @relation("TaskDependencies")
  
  // Relations
  userId                String
  user                  User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  labels                Label[]  @relation("TaskLabels")
  
  @@index([userId, status])
  @@index([planId])
}

// NEW: Conversation history
model Conversation {
  id                    String   @id @default(uuid())
  userId                String
  user                  User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  type                  ConversationType // "onboarding", "planning", "chat"
  status                ConversationStatus // "active", "completed", "abandoned"
  
  // Message storage
  messages              Json     // Array of {role, content, timestamp, model}
  metadata              Json?    // Agent state, current step, etc.
  
  // Tracking
  createdAt             DateTime @default(now())
  updatedAt             DateTime @updatedAt
  completedAt           DateTime?
  lastMessageAt         DateTime?
  
  // Cost tracking
  totalTokensUsed       Int      @default(0)
  estimatedCost         Float    @default(0)
  
  @@index([userId, type, status])
  @@index([updatedAt])
}

enum ConversationType {
  ONBOARDING
  PLANNING
  GENERAL_CHAT
}

enum ConversationStatus {
  ACTIVE
  COMPLETED
  ABANDONED
  PAUSED
}

// NEW: User context storage
model UserContext {
  id                    String   @id @default(uuid())
  userId                String   @unique
  user                  User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  // Channel information
  channelName           String?
  channelType           String?  // "existing", "new"
  channelTopic          String?  @db.Text
  channelSize           String?  // "0-1k", "1k-10k", "10k-100k", "100k+"
  
  // Demographics
  ageGroup              String?
  location              String?
  
  // Content strategy
  isTeam                Boolean  @default(false)
  teamSize              Int?
  uploadFrequency       String?  // "daily", "weekly", "biweekly", "monthly"
  contentGoals          String?  @db.Text
  challenges            String?  @db.Text
  
  // Preferences
  thoughtProcess        String?  @db.Text
  preferredWorkStyle    String?
  
  // File reference
  contextFilePath       String?  // Path to markdown file
  
  // Metadata
  rawContext            Json?    // Flexible storage
  updatedAt             DateTime @updatedAt
  
  @@index([userId])
}
```

---

### 4.2 Message Format Schema

**Conversation.messages JSON structure:**
```typescript
interface Message {
  id: string;              // Unique message ID
  role: 'user' | 'assistant' | 'system';
  content: string;         // Message text
  timestamp: string;       // ISO 8601
  model?: string;          // Which AI model generated (if assistant)
  tokensUsed?: number;     // Token count for this message
  metadata?: {
    step?: string;         // Onboarding step
    confidence?: number;   // AI confidence score
    [key: string]: any;
  };
}
```

**Example:**
```json
{
  "messages": [
    {
      "id": "msg_001",
      "role": "assistant",
      "content": "Hey! Let's set up your content creator profile...",
      "timestamp": "2026-01-07T10:00:00Z",
      "model": "gpt-3.5-turbo",
      "tokensUsed": 45,
      "metadata": {
        "step": "welcome",
        "confidence": 1.0
      }
    },
    {
      "id": "msg_002",
      "role": "user",
      "content": "I have a tech YouTube channel with 5000 subscribers",
      "timestamp": "2026-01-07T10:00:15Z"
    }
  ]
}
```

---

## 5. API Architecture

### 5.1 Next.js API Routes

**Structure:**
```
app/api/
├── auth/
│   ├── login/route.ts          # Existing
│   ├── logout/route.ts         # Existing
│   └── signup/route.ts         # Existing
├── tasks/
│   ├── route.ts                # Existing CRUD
│   ├── [id]/route.ts           # Single task operations
│   └── bulk/route.ts           # NEW: Batch create from AI plans
├── agent/
│   └── [...path]/route.ts      # NEW: Proxy to Python service
├── conversations/
│   ├── route.ts                # NEW: List user's conversations
│   └── [id]/route.ts           # NEW: Get conversation by ID
└── user/
    ├── context/route.ts        # NEW: Get/update user context
    └── usage/route.ts          # NEW: Get token usage stats
```

**Proxy Route Implementation:**
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
  // Verify JWT
  const token = request.cookies.get('token')?.value;
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  const payload = verifyToken(token);
  if (!payload) {
    return NextResponse.json({ error: 'Invalid token' }, { status: 401 });
  }
  
  // Parse body
  const body = await request.json();
  const path = params.path.join('/');
  
  // Forward to Python service
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
  
  if (!response.ok) {
    return NextResponse.json(
      { error: 'Agent service error' },
      { status: response.status }
    );
  }
  
  return response;
}
```

---

### 5.2 Python FastAPI Structure

**Directory Structure:**
```
python-agents/
├── main.py                     # FastAPI app entry point
├── requirements.txt            # Dependencies
├── Dockerfile                  # Container definition
├── .env.example                # Environment template
├── config/
│   ├── settings.py             # Configuration management
│   └── prompts.py              # System prompts library
├── agents/
│   ├── __init__.py
│   ├── base.py                 # Base Agent class
│   ├── onboarding.py           # Onboarding agent logic
│   ├── planner.py              # Planning agent logic
│   └── orchestrator.py         # Model selection logic
├── models/
│   ├── __init__.py
│   ├── openai_client.py        # OpenAI SDK wrapper
│   └── anthropic_client.py     # Anthropic SDK wrapper
├── api/
│   ├── __init__.py
│   ├── routes.py               # FastAPI route definitions
│   ├── websocket.py            # WebSocket endpoint
│   └── middleware.py           # Auth middleware
├── storage/
│   ├── __init__.py
│   ├── conversation.py         # Conversation DB operations
│   ├── user_context.py         # Context file management
│   └── rate_limiter.py         # Rate limiting logic
├── schemas/
│   ├── __init__.py
│   ├── requests.py             # Pydantic request models
│   └── responses.py            # Pydantic response models
└── utils/
    ├── __init__.py
    ├── token_counter.py        # Token counting utilities
    └── logger.py               # Logging configuration
```

**Main Application (main.py):**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.websocket import websocket_endpoint
from config.settings import settings

app = FastAPI(
    title="Content Creator Agent Service",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
)

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api")

# WebSocket
app.add_websocket_route("/ws", websocket_endpoint)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "python-agent"}
```

---

## 6. Security Architecture

### 6.1 Authentication Flow

```
1. User logs in → Next.js /api/auth/login
   ↓
2. Next.js verifies password → generates JWT
   ↓
3. JWT stored in:
   - HTTP-only cookie (server-side requests)
   - localStorage (client-side WebSocket)
   ↓
4. User makes request to /api/agent/*
   ↓
5. Next.js middleware verifies JWT
   ↓
6. Next.js extracts userId from JWT
   ↓
7. Next.js forwards to Python with headers:
   - X-Internal-Secret: <shared secret>
   - X-User-Id: <uuid>
   ↓
8. Python verifies X-Internal-Secret
   ↓
9. Python uses X-User-Id for DB queries (trusts Next.js)
```

### 6.2 Service-to-Service Authentication

**Mechanism:** Shared secret in environment variable

```bash
# .env (both services)
INTERNAL_API_SECRET=<64-char random string>
```

**Python Middleware:**
```python
from fastapi import Header, HTTPException

async def verify_internal_request(
    x_internal_secret: str = Header(None),
    x_user_id: str = Header(None)
):
    if x_internal_secret != settings.INTERNAL_API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing user ID")
    return x_user_id
```

### 6.3 API Key Management

**Storage:**
```bash
# Python service .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Rotation Strategy:**
1. Store secondary keys in environment
2. Implement graceful fallback on 401 errors
3. Log key usage for rotation planning

---

## 7. Deployment Architecture

### 7.1 Development (Docker Compose)

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/content_planner
      - PYTHON_AGENT_URL=http://python-agent:8000
      - INTERNAL_API_SECRET=${INTERNAL_API_SECRET}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - db
      - python-agent
  
  python-agent:
    build: ./python-agents
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/content_planner
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - INTERNAL_API_SECRET=${INTERNAL_API_SECRET}
      - ENVIRONMENT=development
    volumes:
      - ./user_context:/app/user_context
      - ./python-agents:/app  # Hot reload
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=content_planner
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
  node_modules:
```

### 7.2 Production Options

**Option 1: Single VPS (Simple)**
```
DigitalOcean Droplet ($20/month)
├── Nginx (reverse proxy)
├── Next.js (PM2 process manager)
├── Python (uvicorn via systemd)
└── PostgreSQL (Docker or native)
```

**Option 2: Cloud-Native (Scalable)**
```
Frontend: Vercel (Next.js deployment)
Backend: Railway/Render (Python FastAPI)
Database: Supabase/Neon (managed PostgreSQL)
Storage: S3 (user context files)
```

---

## 8. Monitoring & Observability

### 8.1 Logging Strategy

**Next.js:**
- Console logs for development
- Production: Winston/Pino → CloudWatch/Datadog

**Python:**
```python
import logging
from config.settings import settings

logger = logging.getLogger("agent_service")
logger.setLevel(logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG)

# Log format
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
```

### 8.2 Metrics to Track

| Metric | Type | Purpose |
|--------|------|---------|
| LLM API latency | Histogram | Detect slow responses |
| Token usage per user | Counter | Cost tracking |
| Conversation completion rate | Gauge | Product success |
| WebSocket connections | Gauge | Concurrent load |
| Error rate by endpoint | Counter | Service health |
| Database query time | Histogram | Performance tuning |

---

## 9. Testing Strategy

### 9.1 Unit Tests
- **Next.js:** Jest + React Testing Library
- **Python:** pytest + pytest-asyncio

### 9.2 Integration Tests
- Test Next.js ↔ Python communication
- Mock LLM APIs (use recorded responses)

### 9.3 E2E Tests
- Playwright for full onboarding flow
- Test WebSocket streaming

---

## 10. Migration Path

### Phase 1: Infrastructure (Week 1)
1. Update Prisma schema
2. Run migrations
3. Set up Python FastAPI skeleton
4. Configure Docker Compose

### Phase 2: MVP (Weeks 2-3)
1. Implement onboarding agent
2. Implement planning agent
3. Build chat UI integration

### Phase 3: Production-Ready (Week 4)
1. Add rate limiting
2. Implement logging/monitoring
3. Security audit
4. Performance testing

---

## Appendices

### A. Technology Alternatives Considered

| Decision | Alternative | Why Not Chosen |
|----------|-------------|----------------|
| Python service | Next.js API routes with AI SDK | Limited Python AI library support |
| FastAPI | Flask | Lack of native async, no auto OpenAPI docs |
| WebSocket | Server-Sent Events (SSE) | SSE is unidirectional, harder on mobile |
| PostgreSQL | MongoDB | Need relational structure, ACID guarantees |
| Docker Compose | Kubernetes | Overkill for initial deployment |

### B. Environment Variables Reference

```bash
# Next.js (.env)
DATABASE_URL=postgresql://...
JWT_SECRET=<secret>
INTERNAL_API_SECRET=<shared-with-python>
PYTHON_AGENT_URL=http://python-agent:8000
NODE_ENV=development|production

# Python (.env)
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
INTERNAL_API_SECRET=<shared-with-nextjs>
ENVIRONMENT=development|production
ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com
LOG_LEVEL=INFO
```

### C. API Response Time SLAs

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| /api/agent/onboarding/start | 500ms | 1s | 2s |
| /api/agent/planning/generate | 3s | 8s | 15s |
| WebSocket first token | 1s | 2s | 3s |
| Task CRUD | 100ms | 200ms | 500ms |
