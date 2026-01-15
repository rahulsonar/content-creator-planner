# Content Creator Agent Service

Python FastAPI service for AI-powered content creator planning and onboarding.

## Features

- **Onboarding Agent**: Interactive conversation flow to gather user context
- **Planning Agent**: Generate project plans with actionable tasks
- **Model Orchestration**: Cost-optimized model selection (GPT-3.5, GPT-4, Claude 3.5)
- **WebSocket Streaming**: Real-time streaming responses
- **Rate Limiting**: Built-in request rate limiting
- **Context Storage**: File-based user context management

## Project Structure

```
python-agents/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container definition
├── .env.example           # Environment template
├── config/                # Configuration & prompts
├── agents/                # AI agent logic
├── models/                # LLM client wrappers
├── api/                   # FastAPI routes & middleware
├── storage/               # Data persistence layer
├── schemas/               # Pydantic request/response models
└── utils/                 # Utilities (logging, token counting)
```

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `INTERNAL_API_SECRET`: Shared secret with Next.js (64+ char random string)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or with Docker:
```bash
docker build -t python-agent .
docker run -p 8000:8000 --env-file .env python-agent
```

## API Endpoints

### Health Check
```
GET /health
```

### Onboarding
```
POST /api/onboarding/start
POST /api/onboarding/message
```

### Planning
```
POST /api/planning/generate
```

### Chat
```
POST /api/chat
```

### WebSocket
```
WS /ws?userId={userId}
```

## Authentication

All API requests require headers:
- `X-Internal-Secret`: Shared secret with Next.js
- `X-User-Id`: User identifier

These are automatically added by the Next.js proxy (`/api/agent/*` routes).

## Development

### Adding a New Agent

1. Create agent class in `agents/` extending `BaseAgent`
2. Implement `process_message()` and `stream_response()`
3. Add route in `api/routes.py`
4. Update `api/websocket.py` for streaming support

### Adding a New Model Provider

1. Create client wrapper in `models/`
2. Implement `generate_completion()` and `stream_completion()`
3. Update `ModelOrchestrator` selection logic

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=.
```

## Production Deployment

1. Set `ENVIRONMENT=production` in `.env`
2. Use production ASGI server (uvicorn with workers)
3. Enable HTTPS
4. Configure proper rate limits
5. Set up monitoring and logging

## Documentation

- API docs (dev only): http://localhost:8000/docs
- Technical Architecture: See `/docs/technical-architecture.md` in main project

## License

MIT
