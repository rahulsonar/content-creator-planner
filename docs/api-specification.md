# API Specification Document
## Content Creator Planner - AI Agent System

**Version:** 1.0  
**Date:** January 7, 2026  
**Base URL (Dev):** `http://localhost:3000/api`

---

## 1. Authentication

All API requests (except `/auth/*`) require JWT authentication.

### Header Format
```http
Authorization: Bearer <jwt_token>
```

Or cookie-based (automatically handled by browser):
```http
Cookie: token=<jwt_token>
```

### JWT Payload Structure
```json
{
  "userId": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "iat": 1704614400,
  "exp": 1705219200
}
```

---

## 2. Next.js API Routes

### 2.1 Authentication Endpoints

#### POST `/api/auth/login`
Authenticate user and receive JWT token.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "Admin123!"
}
```

**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "admin@example.com",
    "name": "Admin User",
    "onboardingCompleted": false
  }
}
```

**Errors:**
- `400 Bad Request` - Missing email or password
- `401 Unauthorized` - Invalid credentials

---

#### POST `/api/auth/signup`
Create new user account.

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "name": "New User"
}
```

**Response (201 Created):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "newuser@example.com",
    "name": "New User",
    "onboardingCompleted": false
  }
}
```

**Errors:**
- `400 Bad Request` - Validation errors
- `409 Conflict` - Email already exists

---

#### POST `/api/auth/logout`
Clear authentication token.

**Request:** (No body)

**Response (200 OK):**
```json
{
  "success": true
}
```

---

### 2.2 Task Management Endpoints

#### GET `/api/tasks`
List all tasks for authenticated user.

**Query Parameters:**
- `status` (optional): Filter by status (TODO, IN_PROGRESS, COMPLETED, etc.)
- `priority` (optional): Filter by priority (LOW, MEDIUM, HIGH, URGENT)
- `planId` (optional): Filter by planning session ID

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "id": "uuid",
      "title": "Setup VS Code for Python",
      "description": "Install Python extension, configure linting...",
      "status": "TODO",
      "priority": "HIGH",
      "dueDate": "2026-02-15T00:00:00Z",
      "estimatedHours": 20,
      "actualHours": null,
      "completedAt": null,
      "generatedByAI": true,
      "planId": "conv-uuid",
      "parentId": null,
      "subtasks": [],
      "labels": ["tutorial", "python"],
      "createdAt": "2026-01-07T10:00:00Z",
      "updatedAt": "2026-01-07T10:00:00Z"
    }
  ],
  "total": 15
}
```

---

#### POST `/api/tasks`
Create a new task.

**Request:**
```json
{
  "title": "Script writing for Python tutorial",
  "description": "Write detailed script covering setup, basics, and examples",
  "status": "TODO",
  "priority": "HIGH",
  "dueDate": "2026-02-10T00:00:00Z",
  "estimatedHours": 8,
  "parentId": null,
  "labels": ["scripting", "tutorial"]
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "title": "Script writing for Python tutorial",
  "description": "Write detailed script...",
  "status": "TODO",
  "priority": "HIGH",
  "dueDate": "2026-02-10T00:00:00Z",
  "estimatedHours": 8,
  "actualHours": null,
  "generatedByAI": false,
  "userId": "uuid",
  "createdAt": "2026-01-07T10:00:00Z",
  "updatedAt": "2026-01-07T10:00:00Z"
}
```

**Errors:**
- `400 Bad Request` - Validation errors
- `401 Unauthorized` - Not authenticated

---

#### PUT `/api/tasks/{id}`
Update an existing task.

**Request:**
```json
{
  "status": "IN_PROGRESS",
  "actualHours": 2
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "status": "IN_PROGRESS",
  "actualHours": 2,
  "updatedAt": "2026-01-07T12:30:00Z"
}
```

**Errors:**
- `404 Not Found` - Task doesn't exist
- `403 Forbidden` - Task belongs to another user

---

#### DELETE `/api/tasks/{id}`
Delete a task.

**Response (200 OK):**
```json
{
  "success": true,
  "deletedId": "uuid"
}
```

**Errors:**
- `404 Not Found` - Task doesn't exist
- `400 Bad Request` - Task has incomplete subtasks

---

#### POST `/api/tasks/bulk`
**NEW:** Create multiple tasks at once (used after AI plan approval).

**Request:**
```json
{
  "planId": "conv-uuid",
  "tasks": [
    {
      "title": "Research Python tutorials market",
      "description": "Analyze top 10 Python tutorial channels...",
      "priority": "HIGH",
      "dueDate": "2026-01-20T00:00:00Z",
      "estimatedHours": 5,
      "dependencies": []
    },
    {
      "title": "Script writing",
      "description": "Write Python basics script",
      "priority": "HIGH",
      "dueDate": "2026-01-25T00:00:00Z",
      "estimatedHours": 8,
      "dependencies": ["task-1-id"]
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "created": 15,
  "taskIds": ["uuid1", "uuid2", ...],
  "planId": "conv-uuid"
}
```

**Errors:**
- `400 Bad Request` - Invalid task data
- `413 Payload Too Large` - More than 50 tasks

---

### 2.3 Conversation Endpoints

#### GET `/api/conversations`
**NEW:** List user's conversations.

**Query Parameters:**
- `type` (optional): ONBOARDING, PLANNING, GENERAL_CHAT
- `status` (optional): ACTIVE, COMPLETED, PAUSED, ABANDONED

**Response (200 OK):**
```json
{
  "conversations": [
    {
      "id": "uuid",
      "type": "ONBOARDING",
      "status": "COMPLETED",
      "totalTokensUsed": 2500,
      "estimatedCost": 0.05,
      "createdAt": "2026-01-07T09:00:00Z",
      "completedAt": "2026-01-07T09:15:00Z",
      "messageCount": 12
    }
  ],
  "total": 3
}
```

---

#### GET `/api/conversations/{id}`
**NEW:** Get conversation details including messages.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "type": "ONBOARDING",
  "status": "COMPLETED",
  "messages": [
    {
      "id": "msg-1",
      "role": "assistant",
      "content": "Hey! Let's set up your content creator profile...",
      "timestamp": "2026-01-07T09:00:00Z",
      "model": "gpt-3.5-turbo",
      "tokensUsed": 45
    },
    {
      "id": "msg-2",
      "role": "user",
      "content": "I have a tech YouTube channel",
      "timestamp": "2026-01-07T09:00:30Z"
    }
  ],
  "metadata": {
    "currentStep": "completed"
  },
  "totalTokensUsed": 2500,
  "estimatedCost": 0.05
}
```

**Errors:**
- `404 Not Found` - Conversation doesn't exist
- `403 Forbidden` - Not user's conversation

---

#### POST `/api/conversations/{id}/pause`
**NEW:** Pause active conversation.

**Response (200 OK):**
```json
{
  "success": true,
  "status": "PAUSED"
}
```

---

### 2.4 User Context Endpoints

#### GET `/api/user/context`
**NEW:** Get user's context information.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "userId": "uuid",
  "channelName": "TechWithAlex",
  "channelType": "existing",
  "channelTopic": "Python programming tutorials",
  "channelSize": "1k-10k",
  "ageGroup": "25-34",
  "location": "United States",
  "isTeam": false,
  "uploadFrequency": "weekly",
  "contentGoals": "Teach Python to beginners, grow to 50k subs",
  "contextFilePath": "/user_context/{userId}/context.md",
  "updatedAt": "2026-01-07T09:15:00Z"
}
```

**Errors:**
- `404 Not Found` - User hasn't completed onboarding

---

#### PUT `/api/user/context`
**NEW:** Update user context.

**Request:**
```json
{
  "uploadFrequency": "biweekly",
  "contentGoals": "Focus on advanced Python topics"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "updatedAt": "2026-01-07T12:00:00Z"
}
```

---

#### GET `/api/user/usage`
**NEW:** Get token usage statistics.

**Response (200 OK):**
```json
{
  "today": {
    "messages": 12,
    "tokensUsed": 5000,
    "estimatedCost": 0.15
  },
  "limits": {
    "dailyMessages": 50,
    "dailyTokens": 100000
  },
  "remaining": {
    "messages": 38,
    "tokensPercentage": 95
  },
  "lifetime": {
    "totalMessages": 150,
    "totalTokens": 75000,
    "totalCost": 2.50
  }
}
```

---

### 2.5 Agent Proxy Endpoints

All `/api/agent/*` requests are proxied to Python service.

#### POST `/api/agent/onboarding/start`
Start or resume onboarding conversation.

**Request:**
```json
{
  "conversationId": null  // or "uuid" to resume
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "message": "Hey! Let's set up your content creator profile. First, tell me about your channel—do you already have one, or are you planning to start?",
  "step": "channel_info",
  "completed": false
}
```

---

#### POST `/api/agent/onboarding/message`
Send message in onboarding conversation.

**Request:**
```json
{
  "conversationId": "uuid",
  "message": "I have a tech YouTube channel about Python programming"
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "message": "Awesome! Python is a great niche. How many subscribers do you currently have?",
  "step": "channel_details",
  "completed": false,
  "metadata": {
    "confidence": 0.95
  }
}
```

**Or if completed:**
```json
{
  "conversationId": "uuid",
  "message": "Perfect! I've saved all your information. You're all set to start planning your content!",
  "step": "completed",
  "completed": true,
  "summary": "Tech YouTuber focusing on Python tutorials, 5k subscribers, uploads weekly...",
  "contextPath": "/user_context/{userId}/context.md"
}
```

---

#### POST `/api/agent/planning/start`
Start content planning conversation.

**Request:**
```json
{
  "timeframe": "6 months",
  "videoCount": 15
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "message": "I've analyzed your profile (Python tutorials, 5k subs, weekly uploads). Let me create a 6-month plan with 15 video ideas tailored to your audience...",
  "plan": null,  // Plan comes after conversation
  "completed": false
}
```

---

#### POST `/api/agent/planning/generate`
Generate task plan after conversation.

**Request:**
```json
{
  "conversationId": "uuid",
  "preferences": {
    "focusAreas": ["beginner tutorials", "practical projects"],
    "avoidTopics": ["advanced theory"]
  }
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "plan": [
    {
      "title": "Python Setup Tutorial",
      "description": "Complete guide to setting up Python development environment with VS Code",
      "priority": "HIGH",
      "dueDate": "2026-02-01T00:00:00Z",
      "estimatedHours": 20,
      "labels": ["tutorial", "beginner", "setup"],
      "subtasks": [
        {
          "title": "Research existing setup tutorials",
          "estimatedHours": 3
        },
        {
          "title": "Script writing",
          "estimatedHours": 5
        },
        {
          "title": "Screen recording",
          "estimatedHours": 4
        },
        {
          "title": "Video editing",
          "estimatedHours": 6
        },
        {
          "title": "Thumbnail design",
          "estimatedHours": 2
        }
      ],
      "dependencies": [],
      "aiReasoning": "Setup tutorials perform well for beginner audiences and have high search volume"
    }
    // ... 14 more tasks
  ],
  "summary": "Here's your 6-month content roadmap focused on beginner-friendly Python tutorials. The plan starts with foundational topics and progressively introduces practical projects...",
  "metadata": {
    "totalHours": 300,
    "distribution": {
      "tutorials": 8,
      "projects": 5,
      "tips": 2
    }
  }
}
```

---

## 3. Python Agent Service API

**Base URL:** `http://python-agent:8000` (internal)  
**External Access:** Via Next.js proxy only

### Authentication
All requests require internal secret header:
```http
X-Internal-Secret: <shared_secret>
X-User-Id: <uuid>
X-User-Email: <email>
```

---

### 3.1 Onboarding Endpoints

#### POST `/onboarding/start`
Initialize onboarding conversation.

**Request:**
```json
{
  "userId": "uuid",
  "conversationId": null  // Resume if provided
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "message": "Hey! Let's set up your content creator profile...",
  "step": "channel_info",
  "completed": false,
  "metadata": {
    "model": "gpt-3.5-turbo",
    "tokensUsed": 45
  }
}
```

---

#### POST `/onboarding/message`
Process user message in onboarding.

**Request:**
```json
{
  "conversationId": "uuid",
  "message": "I have a tech channel"
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "message": "Great! What's your channel's main topic?",
  "step": "topic_details",
  "completed": false,
  "extractedData": {
    "channelType": "existing",
    "channelTopic": "tech"
  }
}
```

---

#### POST `/onboarding/pause`
Pause active onboarding.

**Request:**
```json
{
  "conversationId": "uuid"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "status": "PAUSED",
  "resumeToken": "uuid"
}
```

---

### 3.2 Planning Endpoints

#### POST `/planning/start`
Start planning conversation with context.

**Request:**
```json
{
  "userId": "uuid",
  "timeframe": "6 months",
  "videoCount": 15
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "message": "Based on your profile (Python tutorials, weekly uploads), let's create a strategic plan...",
  "contextLoaded": true
}
```

---

#### POST `/planning/generate`
Generate structured task plan.

**Request:**
```json
{
  "conversationId": "uuid",
  "preferences": {
    "focusAreas": ["tutorials", "projects"],
    "difficulty": "beginner-to-intermediate"
  }
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "plan": [
    // Array of task objects (see Next.js planning/generate response)
  ],
  "summary": "Strategic summary...",
  "metadata": {
    "model": "claude-3.5-sonnet",
    "tokensUsed": 8500,
    "generationTime": 12.5
  }
}
```

---

### 3.3 Chat Endpoint (General)

#### POST `/chat/message`
General chat not tied to onboarding/planning.

**Request:**
```json
{
  "userId": "uuid",
  "message": "What's a good thumbnail color for tech content?",
  "conversationId": null  // Create new or continue existing
}
```

**Response (200 OK):**
```json
{
  "conversationId": "uuid",
  "message": "For tech content, blue and orange are popular choices because...",
  "type": "GENERAL_CHAT"
}
```

---

### 3.4 WebSocket Endpoint

#### WS `/ws`
Real-time streaming conversation.

**Connection:**
```javascript
const ws = new WebSocket('ws://python-agent:8000/ws');

// Authenticate
ws.send(JSON.stringify({
  type: 'auth',
  userId: 'uuid',
  token: 'internal-secret'
}));
```

**Send Message:**
```json
{
  "type": "message",
  "conversationId": "uuid",
  "content": "Tell me about Python"
}
```

**Receive Streaming Response:**
```json
// Token 1
{
  "type": "token",
  "content": "Python",
  "timestamp": "2026-01-07T10:00:00.123Z"
}

// Token 2
{
  "type": "token",
  "content": " is",
  "timestamp": "2026-01-07T10:00:00.156Z"
}

// ... more tokens

// Completion
{
  "type": "done",
  "messageId": "msg-uuid",
  "tokensUsed": 150,
  "conversationId": "uuid"
}
```

**Error Message:**
```json
{
  "type": "error",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "You've reached your daily limit of 50 messages",
  "remainingTime": 43200  // seconds until reset
}
```

---

### 3.5 Admin Endpoints

#### GET `/health`
Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "python-agent",
  "version": "1.0.0",
  "uptime": 86400,
  "models": {
    "openai": "connected",
    "anthropic": "connected"
  }
}
```

---

#### GET `/metrics`
Prometheus-style metrics (internal monitoring).

**Response (200 OK):**
```
# HELP llm_requests_total Total LLM API requests
# TYPE llm_requests_total counter
llm_requests_total{model="gpt-4"} 1250
llm_requests_total{model="gpt-3.5-turbo"} 3400
llm_requests_total{model="claude-3.5-sonnet"} 890

# HELP llm_latency_seconds LLM API response latency
# TYPE llm_latency_seconds histogram
llm_latency_seconds_bucket{model="gpt-4",le="1"} 450
llm_latency_seconds_bucket{model="gpt-4",le="2"} 1100
llm_latency_seconds_bucket{model="gpt-4",le="5"} 1240
```

---

## 4. Error Codes & Responses

### Standard Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional context
    },
    "timestamp": "2026-01-07T10:00:00Z"
  }
}
```

### Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request data |
| 400 | `INCOMPLETE_ONBOARDING` | User must complete onboarding first |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 401 | `INVALID_TOKEN` | JWT expired or malformed |
| 403 | `FORBIDDEN` | User doesn't have access to resource |
| 404 | `NOT_FOUND` | Resource doesn't exist |
| 409 | `CONFLICT` | Resource already exists |
| 413 | `PAYLOAD_TOO_LARGE` | Request exceeds size limit |
| 429 | `RATE_LIMIT_EXCEEDED` | User exceeded rate limit |
| 500 | `INTERNAL_ERROR` | Server error |
| 502 | `LLM_API_ERROR` | External LLM service error |
| 503 | `SERVICE_UNAVAILABLE` | Temporary service outage |

### Example Error Responses

**Rate Limit Exceeded:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "You've sent 50 messages today. Limit resets in 6 hours.",
    "details": {
      "limit": 50,
      "used": 50,
      "resetAt": "2026-01-08T00:00:00Z"
    }
  }
}
```

**LLM API Error:**
```json
{
  "error": {
    "code": "LLM_API_ERROR",
    "message": "OpenAI API is temporarily unavailable. Please try again.",
    "details": {
      "provider": "openai",
      "upstreamStatus": 503
    }
  }
}
```

---

## 5. Rate Limits

### User Limits (Default)

| Resource | Limit | Window |
|----------|-------|--------|
| Messages to AI | 50 | Per day |
| Input tokens | 100,000 | Per day |
| Output tokens | 20,000 | Per day |
| Planning sessions | 3 | Per week |
| Bulk task creation | 50 tasks | Per request |
| API requests | 1000 | Per hour |

### Headers in Rate-Limited Responses
```http
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 23
X-RateLimit-Reset: 1704672000
```

---

## 6. Webhooks (Future)

### POST `/api/webhooks/task-completed`
Notify external systems when task is completed.

**Payload:**
```json
{
  "event": "task.completed",
  "userId": "uuid",
  "task": {
    "id": "uuid",
    "title": "Video recording",
    "completedAt": "2026-01-07T10:00:00Z"
  }
}
```

---

## 7. API Versioning

**Current:** v1 (implicit in base URL)  
**Future:** `/api/v2/...` when breaking changes needed

---

## 8. SDK Examples

### JavaScript/TypeScript Client

```typescript
import axios from 'axios';

class ContentPlannerClient {
  private baseURL = 'http://localhost:3000/api';
  private token: string;

  constructor(token: string) {
    this.token = token;
  }

  async startOnboarding() {
    const response = await axios.post(
      `${this.baseURL}/agent/onboarding/start`,
      { conversationId: null },
      {
        headers: {
          Authorization: `Bearer ${this.token}`
        }
      }
    );
    return response.data;
  }

  async sendOnboardingMessage(conversationId: string, message: string) {
    const response = await axios.post(
      `${this.baseURL}/agent/onboarding/message`,
      { conversationId, message },
      {
        headers: {
          Authorization: `Bearer ${this.token}`
        }
      }
    );
    return response.data;
  }

  async generatePlan(timeframe: string, videoCount: number) {
    const response = await axios.post(
      `${this.baseURL}/agent/planning/generate`,
      { timeframe, videoCount },
      {
        headers: {
          Authorization: `Bearer ${this.token}`
        }
      }
    );
    return response.data;
  }

  async bulkCreateTasks(planId: string, tasks: any[]) {
    const response = await axios.post(
      `${this.baseURL}/tasks/bulk`,
      { planId, tasks },
      {
        headers: {
          Authorization: `Bearer ${this.token}`
        }
      }
    );
    return response.data;
  }
}
```

### Python Client

```python
import requests

class ContentPlannerClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def start_onboarding(self):
        response = requests.post(
            f'{self.base_url}/agent/onboarding/start',
            json={'conversationId': None},
            headers=self.headers
        )
        return response.json()
    
    def send_onboarding_message(self, conversation_id: str, message: str):
        response = requests.post(
            f'{self.base_url}/agent/onboarding/message',
            json={
                'conversationId': conversation_id,
                'message': message
            },
            headers=self.headers
        )
        return response.json()
```

---

## 9. Postman Collection

Import the following URL into Postman:
```
https://api.example.com/postman/content-planner-v1.json
```

Or use the collection in [`docs/postman/`](./postman/content-planner.postman_collection.json)

---

## 10. Testing Endpoints

### Development URLs
- **Next.js:** http://localhost:3000
- **Python Agent:** http://localhost:8000 (internal only)
- **PostgreSQL:** postgresql://postgres:password@localhost:5432/content_planner

### Test Credentials
```
Email: admin@example.com
Password: Admin123!
```

### Sample cURL Requests

**Login:**
```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin123!"
  }'
```

**List Tasks:**
```bash
curl http://localhost:3000/api/tasks \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Start Onboarding:**
```bash
curl -X POST http://localhost:3000/api/agent/onboarding/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"conversationId": null}'
```

---

## Appendices

### A. Response Time SLAs

| Endpoint Category | P50 | P95 | P99 |
|-------------------|-----|-----|-----|
| Auth | 100ms | 200ms | 500ms |
| Task CRUD | 150ms | 300ms | 600ms |
| Conversation List | 100ms | 250ms | 500ms |
| Agent Message | 1s | 3s | 5s |
| Planning Generate | 5s | 10s | 15s |
| WebSocket Token | 50ms | 150ms | 300ms |

### B. Database Query Examples

**Get user with context:**
```sql
SELECT u.*, uc.*
FROM users u
LEFT JOIN user_context uc ON u.id = uc.user_id
WHERE u.id = $1;
```

**Get conversation with messages:**
```sql
SELECT *
FROM conversations
WHERE id = $1
AND user_id = $2;
```

**Get tasks with dependencies:**
```sql
SELECT
  t1.*,
  json_agg(t2.*) AS dependencies
FROM tasks t1
LEFT JOIN task_dependencies td
  ON td.task_id = t1.id
LEFT JOIN tasks t2
  ON t2.id = td.dependency_id
WHERE t1.user_id = $1
GROUP BY t1.id;
```

### C. OpenAPI Specification

Full OpenAPI 3.0 spec available at:
```
http://localhost:8000/docs
```
(Python FastAPI auto-generates this)

---

**Document Version:** 1.0  
**Last Updated:** January 7, 2026  
**Maintainer:** Engineering Team
