# Agent Model Configuration

## Overview
Each AI agent (Planner, Task Manager, Context Manager) can now be configured to use a specific OpenAI model via environment variables. This allows you to optimize costs, performance, and capabilities based on your needs.

## Configuration

### Environment Variables

Add these variables to your `.env` file or set them in your deployment environment:

```bash
# Agent Model Configuration
PLANNER_MODEL=gpt-4              # Model for the Planning Agent
TASK_MANAGER_MODEL=gpt-4         # Model for the Task Manager Agent  
CONTEXT_MANAGER_MODEL=gpt-4      # Model for the Context Manager Agent
```

### Supported Models

Any OpenAI chat model is supported:
- `gpt-3.5-turbo` - Fast, cost-effective, suitable for simpler tasks
- `gpt-4` - Balanced performance and cost
- `gpt-4-turbo` - Faster GPT-4 with larger context window
- `gpt-4o` - Latest GPT-4 optimized model
- `gpt-4o-mini` - Smaller, faster GPT-4o variant

### Default Values

If not specified, all agents default to `gpt-4`.

## Agent Responsibilities

### Planner Agent
- Generates content plans and task breakdowns
- Analyzes project requirements
- Delegates to Task Manager and Context Manager
- **Recommendation**: `gpt-4` or higher for complex planning

### Task Manager Agent  
- Creates, updates, and searches tasks
- Manages task relationships and priorities
- **Recommendation**: `gpt-4` or `gpt-3.5-turbo` for structured operations

### Context Manager Agent
- Manages user context in markdown files
- Extracts and stores user preferences, goals, and information
- **Recommendation**: `gpt-4` for nuanced context understanding

## Configuration Examples

### Cost-Optimized Setup
```bash
PLANNER_MODEL=gpt-4
TASK_MANAGER_MODEL=gpt-3.5-turbo
CONTEXT_MANAGER_MODEL=gpt-3.5-turbo
```

### Performance-Optimized Setup
```bash
PLANNER_MODEL=gpt-4o
TASK_MANAGER_MODEL=gpt-4-turbo
CONTEXT_MANAGER_MODEL=gpt-4
```

### Development/Testing Setup
```bash
PLANNER_MODEL=gpt-3.5-turbo
TASK_MANAGER_MODEL=gpt-3.5-turbo
CONTEXT_MANAGER_MODEL=gpt-3.5-turbo
```

## Docker Configuration

The models are configured in `docker-compose.yml` under the `python-agents` service:

```yaml
environment:
  - PLANNER_MODEL=${PLANNER_MODEL:-gpt-4}
  - TASK_MANAGER_MODEL=${TASK_MANAGER_MODEL:-gpt-4}
  - CONTEXT_MANAGER_MODEL=${CONTEXT_MANAGER_MODEL:-gpt-4}
```

The `:-gpt-4` syntax provides fallback defaults if the environment variable is not set.

## Applying Changes

After modifying model configuration:

1. Update your `.env` file or environment variables
2. Restart the Python agents service:
   ```bash
   docker compose restart python-agents
   ```

Or restart all services:
```bash
docker compose down
docker compose up -d
```

## Monitoring

Model selection is logged when agents are initialized. Check logs with:

```bash
docker logs content-planner-python
```

Look for log entries like:
```
Initialized OpenAI client with model: gpt-4, metadata: ['agent_name', 'conversation_id', 'user_id']
```

## Cost Considerations

Model pricing (per 1M tokens):
- `gpt-3.5-turbo`: ~$0.50 input / $1.50 output
- `gpt-4`: ~$10 input / $30 output  
- `gpt-4-turbo`: ~$10 input / $30 output
- `gpt-4o`: Check OpenAI pricing page for latest

Using `gpt-3.5-turbo` for task management and context storage while keeping `gpt-4` for planning can significantly reduce costs.

## Implementation Details

The configuration is implemented in:
- **Settings**: [python-agents/config/settings.py](../python-agents/config/settings.py)
- **Route Handler**: [python-agents/api/routes.py](../python-agents/api/routes.py)
- **Docker Config**: [docker-compose.yml](../docker-compose.yml)
