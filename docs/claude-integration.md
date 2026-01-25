# Claude Integration Guide

## Overview
This project now supports both OpenAI and Anthropic Claude models. You can mix and match models for different agents based on your needs.

## Setup

### 1. Install Dependencies
```bash
docker exec -it content-planner-python pip install -r requirements.txt
```

Or if running locally:
```bash
cd python-agents
pip install -r requirements.txt
```

### 2. Add Anthropic API Key
Add your Anthropic API key to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 3. Configure Agent Models
Update agent model configuration in `.env`:
```bash
# Use Claude for specific agents
PLANNER_MODEL=claude-opus-4
TASK_MANAGER_MODEL=claude-sonnet-4.5
CONTEXT_MANAGER_MODEL=claude-sonnet-4.5
```

## Available Models

### Anthropic (Claude)
- **claude-sonnet-4.5** - Balanced performance and cost ($3/$15 per 1M tokens)
- **claude-opus-4** - Most capable, higher cost ($15/$75 per 1M tokens)

### OpenAI
- **gpt-3.5-turbo** - Fast and economical ($0.50/$1.50 per 1M tokens)
- **gpt-4** - Advanced capabilities ($10/$30 per 1M tokens)
- **gpt-5** - Latest model ($15/$45 per 1M tokens)

## Usage

### Creating a Client Manually
```python
from models import create_model_client

# Create Claude client
claude_client = create_model_client("claude-sonnet-4.5", metadata={
    "user_id": "user123",
    "session": "abc"
})

# Create OpenAI client
openai_client = create_model_client("gpt-4")
```

### Using in Agents
The agent initialization already uses the model factory based on your environment configuration:

```python
from agents.planner import PlannerAgent
from models import create_model_client
from config.settings import settings

# Client is automatically created based on PLANNER_MODEL env var
client = create_model_client(settings.PLANNER_MODEL)
planner = PlannerAgent(client)
```

### Message Format
Both clients accept the same message format (OpenAI style):
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi! How can I help?"}
]

response = await client.generate_completion(messages)
```

### Tool Calling
Define tools in OpenAI format - they'll be automatically converted for Claude:
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

response = await client.generate_completion(messages, tools=tools)
```

## Key Differences

### Message Handling
- **OpenAI**: System messages are part of messages array
- **Claude**: System message is a separate parameter (handled automatically)

### Tool Calling
- **OpenAI**: Uses `tools` with `tool_choice` parameter
- **Claude**: Uses `tools` with different schema (converted automatically)

### Streaming
Both support streaming with the same interface:
```python
async for chunk in client.stream_completion(messages):
    print(chunk, end="", flush=True)
```

## Cost Optimization

For cost-effective operation:
1. Use **claude-sonnet-4.5** for most tasks (cheaper than GPT-4)
2. Use **claude-opus-4** only for complex planning tasks
3. Use **gpt-3.5-turbo** for simple chat interactions

Example configuration:
```bash
PLANNER_MODEL=claude-opus-4          # Complex planning
TASK_MANAGER_MODEL=claude-sonnet-4.5 # Balanced performance
CONTEXT_MANAGER_MODEL=gpt-3.5-turbo  # Simple context retrieval
```

## Testing

Run the example script to test Claude integration:
```bash
docker exec -it content-planner-python python example_claude_usage.py
```

## Troubleshooting

### Missing API Key
If you see "ANTHROPIC_API_KEY not set", add it to your `.env` file and restart containers:
```bash
docker compose restart python-agents
```

### Model Not Found
Ensure you're using valid model names:
- ✅ `claude-sonnet-4.5`
- ✅ `claude-opus-4`
- ❌ `claude-3-opus` (old naming)
- ❌ `claude` (use full model name)

### Import Errors
Reinstall dependencies:
```bash
docker exec -it content-planner-python pip install -r requirements.txt
```

## Examples

See [example_claude_usage.py](./example_claude_usage.py) for complete usage examples including:
- Basic completion
- Streaming responses
- Tool calling
- Agent initialization with Claude
