# Dummy AI Mode

## Overview
The dummy AI mode allows you to test the chat interface and basic features without making real API calls to OpenAI. This is useful for:
- Development and testing without incurring API costs
- Demoing the UI/UX without needing API keys
- Testing conversation storage and message flow
- Quick prototyping of new features

## Configuration

### Enable Dummy Mode
Set the environment variable in your `.env` file:

```env
USE_DUMMY_AI=true
```

Or set it directly in `docker-compose.yml`:

```yaml
environment:
  - USE_DUMMY_AI=true
```

### Disable Dummy Mode (Use Real AI)
```env
USE_DUMMY_AI=false
```

When disabled, ensure you have valid API keys:
```env
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

## How It Works

When `USE_DUMMY_AI=true`:
1. The Python agents service checks this setting before making AI API calls
2. Instead of calling OpenAI, it returns predefined responses
3. Conversations are still saved to the database normally
4. The response model is labeled as "dummy-ai"
5. Token usage is reported as 0

## Dummy Response Behavior

The dummy AI provides context-aware responses based on keywords:
- **Greetings** (hello, hi, hey) → Welcome message
- **Task/Plan requests** → Sample project plan with tasks
- **Help requests** → List of capabilities
- **Other messages** → Generic acknowledgment with message echo

## Testing the Feature

1. Start your containers:
   ```bash
   docker compose up --build
   ```

2. Open the chat interface at http://localhost:3000/chat

3. Send messages and observe dummy responses

4. Check logs to confirm dummy mode:
   ```bash
   docker logs content-planner-python
   ```
   Look for: `[DUMMY MODE] Processing chat for user: ...`

## Switching Between Modes

You can switch between dummy and real AI without rebuilding:

1. Update your `.env` file:
   ```bash
   echo "USE_DUMMY_AI=true" >> .env  # Enable
   # or
   echo "USE_DUMMY_AI=false" >> .env  # Disable
   ```

2. Restart the Python service:
   ```bash
   docker compose restart python-agents
   ```

## Development Tips

- Use dummy mode during UI/frontend development
- Switch to real AI when testing actual planning logic
- Add custom dummy responses by editing `_handle_dummy_chat()` in `/python-agents/api/routes.py`
- Check conversation storage works the same in both modes

## API Response Format

Both dummy and real modes return the same response structure:

```json
{
  "message": "Response text...",
  "conversationId": "uuid",
  "model": "dummy-ai" | "gpt-4" | "claude-3.5-sonnet",
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

## Limitations

Dummy mode does NOT:
- Generate personalized responses
- Use context from previous conversations
- Call tools (task insertion, context retrieval)
- Learn or adapt based on user input
- Provide actual AI-powered planning

It only provides static, pattern-matched responses for basic testing.
