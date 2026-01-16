# Context Manager Agent - Quick Start Guide

## Installation
No additional installation needed - the agent uses existing dependencies.

## Basic Usage

### 1. Import the Agent
```python
from agents.context_manager import ContextManagerAgent
from models.openai_client import OpenAIClient

# Initialize model client
client = OpenAIClient(
    api_key="your-openai-key",
    model="gpt-4"
)

# Create agent instance
context_agent = ContextManagerAgent(client)
```

### 2. Process User Information
```python
# Information from another agent (e.g., onboarding)
user_info = """
User completed onboarding:
- Name: Sarah Johnson
- Content Type: YouTube tech tutorials
- Channel: TechWithSarah
- Subscribers: 50,000
- Goal: Reach 100K subscribers by year-end
- Challenge: Inconsistent posting schedule
"""

# User context with ID
user_context = {
    "user_id": "user_sarah_123",
    "email": "sarah@example.com"
}

# Process and organize context
response = await context_agent.process_message(user_info, user_context)
print(response)
```

### 3. Read Context Files
```python
from utils.user_context_manager import read_user_context

# Read specific file
profile = read_user_context("user_sarah_123", "profile.md")
print(profile)

# Read index for overview
index = read_user_context("user_sarah_123", "INDEX.md")
print(index)
```

### 4. List All Context Files
```python
from utils.user_context_manager import list_user_context_files

# Get all files for a user
files = list_user_context_files("user_sarah_123")
print(f"Context files: {files}")
# Output: ['INDEX.md', 'profile.md', 'goals.md', ...]
```

## Direct File Operations

### Create/Update Files Directly
```python
from utils.user_context_manager import write_user_context, update_user_context

# Create new file
write_user_context("user_123", "profile.md", """
# User Profile

## Basic Info
- Name: John Doe
- Content: Blog posts
""")

# Append to existing file
update_user_context("user_123", "history.md", """

## 2026-01-16 10:00
User started planning session...
""")
```

## Integration with Orchestrator

### Add to Orchestrator
```python
# In orchestrator.py
from agents.context_manager import ContextManagerAgent

class ModelOrchestrator:
    def __init__(self, openai_client, anthropic_client):
        # ... existing agents
        self.context_manager = ContextManagerAgent(openai_client)
    
    async def route_message(self, user_message, user_id, agent_type):
        # Route to appropriate agent
        if agent_type == "onboarding":
            response = await self.onboarding_agent.process_message(...)
            
            # Update context after onboarding
            await self._update_user_context(response, user_id)
            
        return response
    
    async def _update_user_context(self, information, user_id):
        """Update user context after agent interactions"""
        await self.context_manager.process_message(
            information,
            {"user_id": user_id}
        )
```

## Example Workflows

### Workflow 1: New User Onboarding
```python
async def onboard_new_user(user_id, onboarding_data):
    # 1. Process onboarding data
    summary = f"""
    New user onboarded:
    - Name: {onboarding_data['name']}
    - Content Type: {onboarding_data['content_type']}
    - Goals: {onboarding_data['goals']}
    """
    
    # 2. Create context files
    await context_agent.process_message(
        summary,
        {"user_id": user_id}
    )
    
    # 3. Verify files created
    files = list_user_context_files(user_id)
    print(f"Created: {files}")
```

### Workflow 2: Add Planning Session Notes
```python
async def save_planning_session(user_id, session_notes):
    # Append to history
    from utils.user_context_manager import update_user_context
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    update_user_context(user_id, "history.md", f"""

## {timestamp} - Planning Session
{session_notes}
""")
    
    # Update strategy file if needed
    write_user_context(user_id, "content_strategy.md", f"""
# Content Strategy

## Content Pillars
{session_notes['pillars']}

## Posting Schedule
{session_notes['schedule']}
""")
```

### Workflow 3: Retrieve User Context
```python
async def get_full_user_context(user_id):
    """Load all context for an agent to use"""
    from utils.user_context_manager import read_user_context
    
    context_parts = []
    
    # Read key files
    for filename in ["profile.md", "goals.md", "content_strategy.md"]:
        content = read_user_context(user_id, filename)
        if content:
            context_parts.append(content)
    
    # Combine into single context string
    full_context = "\n\n---\n\n".join(context_parts)
    return full_context
```

## Testing

### Run Test Suite
```bash
cd python-agents
python test_context_manager.py
```

### Validate Syntax
```bash
python validate_context_manager.py
```

### Check Created Files
```bash
# After running tests, check the files
ls -la agent_context/user_*/
cat agent_context/user_test_001/INDEX.md
```

## File Structure Reference

After processing, expect this structure:
```
agent_context/
└── {userId}/
    ├── INDEX.md              ← Always created first
    ├── profile.md            ← Basic user info
    ├── goals.md              ← User objectives
    ├── preferences.md        ← Workflow preferences
    ├── challenges.md         ← Pain points
    ├── content_strategy.md   ← Strategy & pillars
    ├── audience.md           ← Target demographics
    ├── schedule.md           ← Posting schedule
    ├── history.md            ← Conversation log
    └── notes.md              ← Miscellaneous
```

## Common Patterns

### Pattern: Initialize User Context
```python
async def initialize_user_context(user_id, user_data):
    """Create initial context structure for new user"""
    
    # Create INDEX first
    from utils.user_context_manager import write_user_context
    
    write_user_context(user_id, "INDEX.md", f"""
# User Context Index

**User ID:** {user_id}  
**Created:** {datetime.now().strftime("%Y-%m-%d")}  

## Quick Overview
- **Name:** {user_data['name']}
- **Status:** New User

## Context Files
Will be populated as user interacts with the system.
""")
    
    print(f"✓ Initialized context for {user_id}")
```

### Pattern: Update Single Section
```python
async def update_user_goals(user_id, new_goals):
    """Update just the goals section"""
    from utils.user_context_manager import write_user_context
    
    content = f"""
# User Goals

## Primary Goals
{new_goals['primary']}

## Success Metrics
{new_goals['metrics']}

---
*Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
    
    write_user_context(user_id, "goals.md", content)
```

### Pattern: Append to History
```python
async def log_interaction(user_id, interaction_type, summary):
    """Append interaction to history"""
    from utils.user_context_manager import update_user_context
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    update_user_context(user_id, "history.md", f"""

## {timestamp} - {interaction_type}
{summary}
""")
```

## Troubleshooting

### Issue: user_id missing
```python
# ❌ Wrong
await context_agent.process_message("user info", {})

# ✓ Correct
await context_agent.process_message("user info", {"user_id": "user_123"})
```

### Issue: File not found
```python
from utils.user_context_manager import read_user_context

content = read_user_context("user_123", "profile.md")
if content is None:
    print("File doesn't exist yet")
    # Create it
    write_user_context("user_123", "profile.md", "# Profile\n...")
```

### Issue: Directory doesn't exist
```python
from utils.user_context_manager import ensure_user_context_dir

# Always ensure directory exists before operations
ensure_user_context_dir("user_123")
```

## Best Practices

1. **Always pass user_id** in user_context dictionary
2. **Create INDEX.md first** for new users
3. **Use timestamps** when appending to history
4. **Keep files focused** on single topics
5. **Cross-reference** related information
6. **Validate user_id** before operations
7. **Handle None returns** from read operations
8. **Log all context changes** for debugging

## Next Steps

1. ✅ Agent created and validated
2. ⏭️ Add to orchestrator workflow
3. ⏭️ Create API endpoints for context access
4. ⏭️ Test with real user interactions
5. ⏭️ Add monitoring and logging
6. ⏭️ Implement backup strategy

## Resources

- Full documentation: [README_CONTEXT_MANAGER.md](agents/README_CONTEXT_MANAGER.md)
- Architecture diagram: [CONTEXT_MANAGER_ARCHITECTURE.md](CONTEXT_MANAGER_ARCHITECTURE.md)
- Implementation summary: [CONTEXT_MANAGER_SUMMARY.md](CONTEXT_MANAGER_SUMMARY.md)
- Test suite: [test_context_manager.py](test_context_manager.py)
- System prompt: [config/prompts.py](config/prompts.py) (CONTEXT_MANAGER_SYSTEM_PROMPT)

## Support

For issues or questions:
1. Check the test suite for examples
2. Review the README documentation
3. Inspect `utils/user_context_manager.py` for available functions
4. Run validation script to check for syntax errors
