# OpenAI Tools Configuration

## Overview
The PlanningAgent now supports configurable tool usage for OpenAI models. This allows you to enable or disable function calling capabilities at the class level.

## Configuration

### Environment Variable
Add to your `.env` file:
```bash
# Enable or disable OpenAI tools (default: true)
ENABLE_OPENAI_TOOLS=true
```

Set to `false` to disable tool calling for OpenAI models:
```bash
ENABLE_OPENAI_TOOLS=false
```

### Settings
The configuration is defined in [config/settings.py](../python-agents/config/settings.py):
```python
# Agent Configuration
ENABLE_OPENAI_TOOLS: bool = True
```

## Usage

### Class-Level Configuration
When instantiating the PlanningAgent:

```python
from agents.planner import PlanningAgent
from models.openai_client import OpenAIClient
from config.settings import settings

# Using global settings (recommended)
client = OpenAIClient(model="gpt-4")
agent = PlanningAgent(client, enable_openai_tools=settings.ENABLE_OPENAI_TOOLS)

# Or explicitly enable/disable
agent_with_tools = PlanningAgent(client, enable_openai_tools=True)
agent_without_tools = PlanningAgent(client, enable_openai_tools=False)
```

### Default Behavior
If not specified, tools are **enabled by default**:
```python
# This enables tools by default
agent = PlanningAgent(client)  # Same as enable_openai_tools=True
```

## Behavior

### With Tools Enabled (`enable_openai_tools=True`)
- OpenAI models can call the `insert_tasks_to_db` function
- Agent can directly create tasks in the database
- Full function calling workflow is active

### With Tools Disabled (`enable_openai_tools=False`)
- OpenAI models will NOT receive tool definitions
- Agent operates in text-only mode
- No function calling capabilities
- Useful for testing conversational responses without side effects

## Notes

- **Anthropic models**: Tool usage is always enabled for Anthropic (Claude) models regardless of this flag
- **Backward compatibility**: Existing code continues to work as tools are enabled by default
- **API routes**: The routes in `api/routes.py` automatically use the global settings configuration

## Use Cases

### Disable Tools During Testing
```python
# Test conversational responses without database writes
agent = PlanningAgent(client, enable_openai_tools=False)
response = await agent.process_message("Create a video plan")
# Response will be text-only, no tasks created
```

### Production with Fine-Grained Control
```python
# Different behavior based on environment
if settings.is_development:
    agent = PlanningAgent(client, enable_openai_tools=False)
else:
    agent = PlanningAgent(client, enable_openai_tools=True)
```

## Related Files
- Configuration: [config/settings.py](../python-agents/config/settings.py)
- Implementation: [agents/planner.py](../python-agents/agents/planner.py)
- API routes: [api/routes.py](../python-agents/api/routes.py)
