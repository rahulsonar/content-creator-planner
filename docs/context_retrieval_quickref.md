# Quick Reference: request_user_context Tool

## TL;DR

The planner agent can now request information from the context manager agent using the `request_user_context` tool. This enables autonomous retrieval of user goals, preferences, history, and other context during planning conversations.

---

## Tool Signature

```typescript
interface RequestUserContextTool {
  name: "request_user_context",
  parameters: {
    query: string;      // Specific question about the user
    reasoning: string;  // Why this info is needed
  }
}
```

---

## Quick Setup

```python
from agents.planner import PlanningAgent
from agents.context_manager import ContextManagerAgent
from models.anthropic_client import AnthropicClient

# 1. Initialize context manager
context_manager = ContextManagerAgent(anthropic_client)

# 2. Initialize planner WITH context manager
planner = PlanningAgent(
    anthropic_client,
    context_manager_agent=context_manager  # ← Required!
)

# 3. Use normally - tool is automatically available
response = await planner.process_message(
    user_message="Create a content plan",
    user_context={"user_id": "user_123"}  # ← user_id required!
)
```

---

## Common Query Patterns

### Goals & Objectives
```python
query="What are the user's content creation goals?"
query="What metrics or targets is the user trying to achieve?"
query="What does the user want to accomplish with their content?"
```

### Platforms & Format
```python
query="What platforms does the user create content for?"
query="What is the user's primary content distribution channel?"
query="Does the user prefer video, written, or audio content?"
```

### Audience & Demographics
```python
query="Who is the user's target audience?"
query="What demographics does the user's content serve?"
query="What are the characteristics of the user's viewers/readers?"
```

### Topics & Niche
```python
query="What topics or niche does the user focus on?"
query="What subject areas has the user covered in past content?"
query="What is the user's content specialization?"
```

### Preferences & Constraints
```python
query="What content preferences has the user mentioned?"
query="Are there any time or resource constraints for the user?"
query="What content formats does the user prefer to create?"
```

### History & Past Work
```python
query="What content has the user created previously?"
query="What projects is the user currently working on?"
query="Has the user mentioned any past successes or challenges?"
```

---

## Code Examples

### Example 1: Basic Usage (Automatic)

```python
# Planner automatically calls tool when needed
response = await planner.process_message(
    user_message="Help me plan my content for next week",
    user_context={"user_id": "creator_456"}
)
# Planner internally calls request_user_context to get goals, platforms, etc.
```

### Example 2: Manual Testing

```python
# Simulate what planner does internally
context_info = await planner._request_context_from_manager(
    query="What are the user's content goals?",
    reasoning="To create aligned content plan",
    user_id="creator_456"
)
print(context_info)
# Output: "User wants to reach 10k subscribers on YouTube..."
```

### Example 3: Multiple Retrievals

```python
# Planner can call multiple times in one conversation
# This happens automatically, but conceptually:

# Call 1: Get goals
# Call 2: Get platforms
# Call 3: Get audience
# Then: Generate response using all retrieved context
```

---

## Return Values

### Success
```python
"The user's goal is to reach 10,000 YouTube subscribers by end of year. 
They currently have 3,500 subscribers."
```

### No Context Found
```python
"No information found about this topic."
```

### Error
```python
"Error retrieving context: [error message]"
```

### Context Manager Not Available
```python
"Context manager agent is not available. Unable to retrieve user context."
```

---

## Debugging

### Enable Debug Logging
```python
import logging
logging.getLogger('agents.planner').setLevel(logging.DEBUG)
logging.getLogger('agents.context_manager').setLevel(logging.DEBUG)
```

### Check If Tool Was Called
```python
# Look for these log messages:
# "Executing tool: request_user_context"
# "Requesting context from context manager: [query]"
# "Context manager returned: [result]..."
```

### Verify Context Manager Connection
```python
assert planner.context_manager_agent is not None, "Context manager not set!"
```

### Verify User ID
```python
assert hasattr(planner, '_current_user_id'), "User ID not stored!"
assert planner._current_user_id is not None, "User ID is None!"
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Context manager agent is not available" | `context_manager_agent=None` | Pass context manager to planner's `__init__` |
| "No user_id available" | No `user_id` in `user_context` | Include `user_id` in context dict |
| Tool not called | Model doesn't support tools | Use OpenAI GPT-4 |
| Empty context | User context not saved | Ensure context was saved via context manager first |
| Tool not defined | Wrong model client | Check `tools_openai` arrays |

---

## Performance Tips

1. **Be specific in queries**: "What are the user's YouTube subscriber goals?" vs "Tell me about the user"
2. **One query per call**: Don't try to get multiple pieces of info in one query
3. **Let planner decide**: Don't force tool calls, let the model determine when to use it
4. **Cache context**: Retrieved context is in conversation history, no need to re-request

---

## Integration Checklist

- [ ] Context manager initialized
- [ ] Planner initialized with `context_manager_agent` parameter
- [ ] User context includes `user_id`
- [ ] Context files exist for user (created via context manager)
- [ ] Model supports tool calling (Claude 3+ or GPT-4+)
- [ ] Tool appears in `tools_openai` arrays
- [ ] Tool execution handlers updated in `_execute_tools_*` methods

---

## Files to Check

| File | What to Look For |
|------|------------------|
| `agents/planner.py` | Tool definition, execution handlers, `_request_context_from_manager()` |
| `agents/context_manager.py` | Context file reading logic |
| `utils/user_context_manager.py` | File system operations for context |
| `agent_context/{user_id}/INDEX.md` | User's context index file |

---

## Testing Checklist

```python
# 1. Save some context
await context_manager.process_message(
    user_message="User wants to grow YouTube channel to 10k subs",
    user_context={"user_id": "test_user"}
)

# 2. Make planning request (should trigger tool)
response = await planner.process_message(
    user_message="Help me create a growth plan",
    user_context={"user_id": "test_user"}
)

# 3. Verify tool was called (check logs)
# Should see: "Executing tool: request_user_context"

# 4. Verify response uses context
assert "10k" in response or "10,000" in response
```

---

## API Surface

### Planner Agent
```python
class PlanningAgent:
    def __init__(
        self, 
        model_client, 
        enable_openai_tools: bool = True,
        context_manager_agent = None  # ← New parameter
    )
    
    async def _request_context_from_manager(  # ← New method
        self,
        query: str,
        reasoning: str,
        user_id: str
    ) -> str
```

### Context Manager Agent
```python
class ContextManagerAgent:
    async def process_message(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str
```

---

## Related Documentation

- **Full Guide**: [context_retrieval_tool.md](context_retrieval_tool.md)
- **Example Flow**: [context_retrieval_example.md](context_retrieval_example.md)
- **Implementation Summary**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Test Script**: [../python-agents/test_context_retrieval.py](../python-agents/test_context_retrieval.py)

---

## Support

For issues or questions:
1. Check logs with DEBUG level enabled
2. Verify all checklist items above
3. Review example flow in documentation
4. Test with the provided test script
