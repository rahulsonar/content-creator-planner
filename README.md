# Content Creator Planner

An AI-assisted planning workspace for content creators. Describe what you want to make — "plan a 6-episode YouTube series on Deccan history" — and a team of LLM agents breaks it down into projects and tasks, writes them to your board, and keeps track of what you've told it about yourself.

Built as a full-stack playground for multi-agent orchestration: a Next.js app for the product UI, and a separate Python service where the agents plan, execute tool calls, check their own work, and replan.

## Highlights

- **Plan → Execute → Synthesize → Replan loop** — a planner turns a request into a dependency graph of tasks, an executor runs them (tool calls or spawned child agents), and a synthesizer judges whether the goal was actually met before either answering or triggering another iteration. Design notes in [docs/plan-execute-synthesize-design.md](docs/plan-execute-synthesize-design.md).
- **Tool registry** — agents act on real data through function-calling tools: `manage_tasks`, `manage_projects`, `manage_context_files`, `redis_storage` (shared scratchpad between agents), and `executor_agent` (delegate a sub-task to a child agent).
- **MCP server** — the task/project database is also exposed as a [Model Context Protocol](https://modelcontextprotocol.io) server, so Claude Desktop, Claude Code, or any MCP client can manage the board directly.
- **Multi-provider models** — OpenAI and Anthropic clients behind one factory; the model is chosen per agent through environment variables.
- **Real-time chat** — a custom Node server adds WebSockets alongside Next.js; the Python service calls back through an authenticated webhook when a run finishes.
- **Observability** — every agent call (model, tokens, tool calls, workflow iteration) is logged and viewable in the app's Agent Logs page.
- **Planner UI** — Kanban board with drag-and-drop, calendar view, projects, hierarchical subtasks, and human-friendly task keys (`CCP-030`).

## Architecture

```mermaid
flowchart LR
    Browser -- HTTP / WebSocket --> Next["Next.js 16<br/>UI, API routes, JWT auth"]
    Next -- "X-Internal-Secret" --> Py["FastAPI agents service"]
    Py -- webhook --> Next
    Next --> PG[(PostgreSQL<br/>Prisma)]
    Py --> PG
    Py --> Redis[(Redis<br/>agent scratchpad,<br/>workflow state)]
    Py --> LLM["OpenAI / Anthropic"]
    MCP["MCP clients"] --> MCPS["MCP server"] --> PG
```

| Directory | What's inside |
| --- | --- |
| [`nextjs/`](nextjs) | Next.js App Router app — pages, API routes, auth middleware, WebSocket server, Prisma schema and migrations |
| [`python-agents/agents/`](python-agents/agents) | Planner, task executor, child executor agent, synthesizer, context manager, workflow orchestrator |
| [`python-agents/agents/tools/`](python-agents/agents/tools) | Tool registry and the Redis storage tool |
| [`python-agents/mcp_server/`](python-agents/mcp_server) | MCP server for tasks and projects |
| [`python-agents/models/`](python-agents/models) | OpenAI / Anthropic client wrappers and model factory |
| [`docs/`](docs) | Architecture design notes |

## Tech stack

**Frontend / API:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, Prisma 7, dnd-kit, FullCalendar, `ws`
**Agents:** Python, FastAPI, OpenAI & Anthropic SDKs, MCP (FastMCP), SQLAlchemy / asyncpg, Pydantic
**Infra:** PostgreSQL 16, Redis 7, Docker Compose

## Running locally

Prerequisites: Docker and Docker Compose, plus an OpenAI and/or Anthropic API key.

```bash
cp .env.example .env          # add your API key(s)
docker compose up -d
docker exec -it content-planner-app npx prisma migrate deploy
docker exec -it content-planner-app npm run db:seed
```

Then open http://localhost:3000 and sign in with the seeded user `admin@example.com` / `Admin123!`.

Set `USE_DUMMY_AI=true` in `.env` to click around without making any API calls, and `USE_WORKFLOW_ORCHESTRATOR=true` to enable the iterative Plan → Execute → Synthesize → Replan loop.

| Service | URL |
| --- | --- |
| App | http://localhost:3000 |
| Agents API | http://localhost:8000 |
| Prisma Studio | http://localhost:5555 |
| Adminer (Postgres) | http://localhost:8081 |
| RedisInsight | http://localhost:5540 |

### Using the MCP server

```bash
cd python-agents
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/content_planner \
OPENAI_API_KEY=unused INTERNAL_API_SECRET=unused \
python -m mcp_server.task_management
```

A ready-made VS Code config is in [`.vscode/mcp.json`](.vscode/mcp.json).

## Status

A personal prototype for exploring agent orchestration patterns — not production-hardened. The Docker setup is development-oriented; set real values for `JWT_SECRET` and `INTERNAL_API_SECRET` before deploying anywhere (the app refuses to start in production without them).
