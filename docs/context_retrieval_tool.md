# Context Retrieval Tool for Planner Agent

## Overview

The planner agent now has a **context retrieval tool** (`request_user_context`) that allows it to dynamically request information about the user from the context manager agent. This enables the planner to access historical user information (goals, preferences, past conversations, content plans, etc.) as needed during planning conversations.

## How It Works

### Architecture

```
┌─────────────────┐          ┌──────────────────────┐          ┌─────────────────┐
│                 │          │                      │          │                 │
│  Planner Agent  │ ◄─────── │  request_user_context│ ──────► │  Context Manager│
│                 │  calls   │       Tool           │  queries │      Agent      │
│                 │          │                      │          │                 │
└─────────────────┘          └──────────────────────┘          └─────────────────┘
        │                                                               │
        │                                                               │
        ▼                                                               ▼
  Creates tasks                                            Reads user context files
  based on context                                         (INDEX.md, profile.md, etc.)
```

### Flow

1. **User makes a planning request** to the planner agent
2. **Planner analyzes** if it needs more context about the user
3. **Planner calls `request_user_context` tool** with:
   - `query`: Specific question about the user (e.g., "What are the user's content goals?")
   - `reasoning`: Why this information is needed
4. **Tool handler invokes context manager agent** with the query
5. **Context manager retrieves information** from user's context files
6. **Context returned to planner** to inform its response
7. **Planner can call multiple times** with different queries as needed

## Tool Definition

### Parameters

| Parameter   | Type   | Required | Description |
|------------|--------|----------|-------------|
| `query`    | string | Yes      | Clear, specific question about the user |
| `reasoning`| string | Yes      | Explanation of why this information is needed |

### Example Tool Calls

```python
# Query about user goals
{
    "query": "What are the user's content creation goals?",
    "reasoning": "I need to understand their objectives to create an aligned content plan"
}

# Query about platforms
{
    "query": "What platforms does the user create content for?",
    "reasoning": "To tailor task recommendations for specific platforms"
}

# Query about target audience
{
    "query": "Who is the user's target audience?",
    "reasoning": "To ensure content ideas resonate with their intended viewers"
}

# Query about past topics
{
    "query": "What content topics has the user worked on previously?",
    "reasoning": "To avoid repetition and build on existing content themes"
}
```

## Usage Examples

### Example 1: Basic Context Retrieval

```python
from agents.planner import PlanningAgent
from agents.context_manager import ContextManagerAgent
from models.openai_client import OpenAIClient

# Initialize agents
openai_client = OpenAIClient()
context_manager = ContextManagerAgent(openai_client)
planner = PlanningAgent(
    openai_client, 
    context_manager_agent=context_manager
)

# User makes a planning request
user_context = {"user_id": "user_123"}
response = await planner.process_message(
    user_message="Help me create a content calendar for next month",
    user_context=user_context
)

# Behind the scenes, planner might call:
# 1. request_user_context(query="What are user's content goals?", ...)
# 2. request_user_context(query="What platforms does user use?", ...)
# 3. Use retrieved context to create personalized plan
```

### Example 2: Multiple Context Requests

The planner can make multiple context requests in a single conversation:

```python
# User: "Create 10 video ideas for my channel"

# Planner internally:
# Call 1: request_user_context(query="What is user's niche/topic focus?")
# Call 2: request_user_context(query="Who is user's target audience?")
# Call 3: request_user_context(query="What platform are they primarily on?")
# Call 4: request_user_context(query="What are their subscriber/reach goals?")

# Then creates video ideas based on all retrieved context
```

## Implementation Details

### Planner Agent Changes

1. **Tool Definition**: Added `request_user_context` tool to OpenAI formats
2. **User ID Tracking**: Stores `_current_user_id` from `user_context` during `process_message`
3. **Tool Execution**: Handles `request_user_context` in `_execute_tools_openai`
4. **Context Manager Communication**: New method `_request_context_from_manager` formats queries and calls context manager

### Key Code Additions

```python
# In __init__
self.tools_anthropic = [
    {
        "name": "request_user_context",
        "description": "Request information about the user...",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {...},
                "reasoning": {...}
            },
            "required": ["query", "reasoning"]
        }
    },
    # ... other tools
]

# In process_message
if user_context and 'user_id' in user_context:
    self._current_user_id = user_context['user_id']

# New method
async def _request_context_from_manager(
    self,
    query: str,
    reasoning: str,
    user_id: str
) -> str:
    """Request specific information from context manager"""
    # Formats query and calls context_manager_agent.process_message()
    # Returns retrieved context information
```

## Testing

Run the test script to see the feature in action:

```bash
# Inside the python-agents container
cd /app
python test_context_retrieval.py
```

This test:
1. Saves sample user context (goals, audience, platforms)
2. Makes a planning request that triggers context retrieval
3. Demonstrates multiple context queries
4. Shows how planner uses retrieved context in responses

## Benefits

1. **Dynamic Context Access**: Planner retrieves only the context it needs, when it needs it
2. **Flexible Queries**: Can ask specific questions tailored to the current task
3. **Multiple Calls**: Can gather various pieces of information in one conversation
4. **AI-to-AI Communication**: Leverages context manager's intelligence to interpret and retrieve relevant information
5. **Separation of Concerns**: Planner focuses on planning, context manager handles context storage/retrieval

## Configuration

The tool is automatically available when:
- Planner agent is initialized with a `context_manager_agent` parameter
- User context includes a valid `user_id`

```python
planner = PlanningAgent(
    model_client=openai_client,
    enable_openai_tools=True,  # Enable tools for OpenAI models
    context_manager_agent=context_manager_instance  # Required for context retrieval
)
```

## Error Handling

The tool gracefully handles errors:

- **No context manager**: Returns "Context manager agent is not available"
- **No user_id**: Returns "No user_id available for context retrieval"
- **Context manager errors**: Returns error message without failing the planning flow
- **No context found**: Context manager returns "No information found about this topic"

## Best Practices

1. **Be specific in queries**: Ask focused questions rather than broad ones
2. **Provide clear reasoning**: Helps with debugging and understanding tool usage
3. **Call multiple times if needed**: Better to make several focused requests than one vague one
4. **Handle "no context found"**: Planner should gracefully proceed even if some context is missing

## Future Enhancements

Potential improvements:
- Cache retrieved context to avoid duplicate requests in same conversation
- Add context priority/ranking in queries
- Support batch context requests in a single tool call
- Add context confidence scores
- Track which context was most useful for analytics
