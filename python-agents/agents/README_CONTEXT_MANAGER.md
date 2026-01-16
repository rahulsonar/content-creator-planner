# Context Manager Agent

## Overview
The Context Manager Agent is responsible for receiving information about users from other AI agents and organizing it into structured markdown files. It maintains user context in the `agent_context/{userId}` directory using a well-organized file structure.

## Purpose
- **Receive** information from other agents (Onboarding, Planning, etc.)
- **Organize** user data into logical, structured markdown files
- **Maintain** an index file for easy navigation
- **Update** context files as new information becomes available

## File Structure

The agent creates and maintains the following file structure for each user:

```
agent_context/
└── {userId}/
    ├── INDEX.md              # Main index with overview and navigation
    ├── profile.md            # Basic user information
    ├── goals.md              # User goals and objectives
    ├── preferences.md        # User preferences and workflows
    ├── challenges.md         # Pain points and obstacles
    ├── content_strategy.md   # Content strategy and pillars
    ├── audience.md           # Target audience details
    ├── schedule.md           # Content calendar preferences
    ├── history.md            # Conversation history and milestones
    └── notes.md              # Miscellaneous notes
```

## Usage

### Basic Usage

```python
from agents.context_manager import ContextManagerAgent
from models.openai_client import OpenAIClient

# Initialize the agent
client = OpenAIClient(api_key="your-key", model="gpt-4")
agent = ContextManagerAgent(client)

# Process user information from another agent
user_info = """
User completed onboarding:
- Name: Sarah Johnson
- Content Type: YouTube videos
- Goals: Reach 100K subscribers
"""

user_context = {
    "user_id": "user_123",
    "email": "sarah@example.com"
}

response = await agent.process_message(user_info, user_context)
```

### Integration with Orchestrator

The Context Manager Agent is typically called by the orchestrator after conversations with other agents:

```python
# After onboarding conversation
onboarding_summary = await onboarding_agent.process_message(...)

# Pass to context manager
context_response = await context_manager.process_message(
    onboarding_summary,
    {"user_id": user_id}
)
```

## Tool-Based Operations

When using models that support tool calling (GPT-4, Claude 3.5), the agent can use structured tools to manage files:

### Available Tool Actions

1. **create_index** - Create or update INDEX.md
2. **update_section** - Create or update a section file (profile.md, goals.md, etc.)
3. **read_context** - Read an existing context file
4. **list_files** - List all context files for a user

### Tool Schema

```json
{
  "action": "update_section",
  "user_id": "user_123",
  "filename": "profile.md",
  "content": "# User Profile\n\n...",
  "append": false
}
```

## Direct File Operations

You can also use the utility functions directly for file operations:

```python
from utils.user_context_manager import (
    write_user_context,
    read_user_context,
    update_user_context,
    list_user_context_files
)

# Write a file
write_user_context("user_123", "profile.md", content)

# Read a file
content = read_user_context("user_123", "profile.md")

# Append to a file
update_user_context("user_123", "history.md", "\n## 2026-01-16\n...")

# List all files
files = list_user_context_files("user_123")
```

## File Format Guidelines

### INDEX.md Structure
```markdown
# User Context Index

**User ID:** user_123  
**Last Updated:** 2026-01-16  

## Quick Overview
- **Name:** Sarah Johnson
- **Content Type:** YouTube Videos
- **Status:** Active

## Context Files
1. [Profile](profile.md) - Basic information
2. [Goals](goals.md) - Objectives and metrics
...
```

### Section File Structure
```markdown
# Section Title

## Category 1
- Point 1
- Point 2

## Category 2
Details here...

---
*Last updated: 2026-01-16*
```

## Context Management Principles

1. **Always update INDEX.md first** when new information arrives
2. **Update relevant section files** based on information type
3. **Append with timestamps** when adding to existing files
4. **Create new sections** only when information doesn't fit existing ones
5. **Keep files focused** - don't mix unrelated topics
6. **Cross-reference** between files when appropriate

## Example Workflow

### Scenario: User Completes Onboarding

1. **Onboarding Agent** collects user information
2. **Orchestrator** sends summary to Context Manager Agent
3. **Context Manager** creates:
   - `INDEX.md` (overview)
   - `profile.md` (name, channel details)
   - `goals.md` (stated objectives)
   - `challenges.md` (pain points mentioned)

### Scenario: User Has Planning Session

1. **Planning Agent** creates content strategy
2. **Orchestrator** sends summary to Context Manager Agent
3. **Context Manager** updates:
   - `INDEX.md` (add planning session timestamp)
   - `content_strategy.md` (content pillars, themes)
   - `schedule.md` (posting frequency)
   - `history.md` (append planning session details)

## Testing

Run the test suite to verify the agent works correctly:

```bash
# From python-agents directory
python test_context_manager.py
```

This will:
- Test basic context management
- Create sample context files
- Simulate typical workflows
- Verify file operations

## System Prompt

The agent uses the `CONTEXT_MANAGER_SYSTEM_PROMPT` from `config/prompts.py`, which includes:
- File structure guidelines
- Markdown formatting rules
- Context management principles
- When to create/update specific files

## Dependencies

- `agents.base.BaseAgent` - Base agent class
- `utils.user_context_manager` - File operation utilities
- `utils.logger` - Logging functionality
- Model client (OpenAI or Anthropic) - For LLM capabilities

## Error Handling

The agent gracefully handles:
- Missing user_id in context
- File read/write errors
- Tool execution failures
- Model API errors

All errors are logged and user-friendly messages are returned.

## Best Practices

1. **Always pass user_id** in user_context dictionary
2. **Use descriptive filenames** that match content type
3. **Include timestamps** when appending to history
4. **Keep markdown clean** and properly formatted
5. **Regular maintenance** - Archive old history periodically
6. **Cross-reference** related information between files

## Future Enhancements

Potential improvements:
- Automatic summarization of long history files
- Search functionality across context files
- Version control for context changes
- Automatic archiving of old context
- Context compression for large files
- Multi-format support (JSON, YAML)
