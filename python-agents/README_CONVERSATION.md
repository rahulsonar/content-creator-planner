# Agent Conversation Script

## Overview
This script enables two AI agents (Claude and OpenAI) to have a natural conversation with each other. Claude acts as the user, and OpenAI acts as the assistant.

## Files
- **agent_conversation.py** - Main script that orchestrates the conversation
- **conversation_config.json** - Configuration file with topic, roles, and instructions

## Configuration File Structure

Create a `conversation_config.json` file with the following fields:

```json
{
  "topic": "Your conversation topic",
  "claude_role": "Role description for Claude",
  "openai_role": "Role description for OpenAI",
  "claude_instructions": "Specific instructions for Claude's behavior",
  "openai_instructions": "Specific instructions for OpenAI's behavior",
  "max_turns": 5,
  "temperature": 0.7,
  "max_tokens": 800,
  "claude_model": "claude-3-5-sonnet-20241022",
  "openai_model": "gpt-4"
}
```

### Required Fields
- **topic** - The subject of the conversation
- **claude_role** - Claude's role/persona
- **openai_role** - OpenAI's role/persona
- **max_turns** - Number of back-and-forth exchanges (4-5 recommended)

### Optional Fields
- **claude_instructions** - Detailed instructions for Claude's behavior
- **openai_instructions** - Detailed instructions for OpenAI's behavior
- **temperature** - Sampling temperature (0.0-1.0, default: 0.7)
- **max_tokens** - Max tokens per response (default: 800)
- **claude_model** - Claude model to use (default: claude-3-5-sonnet-20241022)
- **openai_model** - OpenAI model to use (default: gpt-4)

## Usage

### 1. Set Up Environment Variables
Make sure you have a `.env` file with your API keys:

```bash
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
```

### 2. Edit Configuration
Edit `conversation_config.json` with your desired topic and instructions.

### 3. Run the Script

**Outside Docker:**
```bash
cd python-agents
python agent_conversation.py
```

**Inside Docker:**
```bash
docker exec -it content-planner-python-agents python agent_conversation.py
```

**With custom config file:**
```bash
python agent_conversation.py my_custom_config.json
```

### 4. View Output
The conversation will be displayed in the terminal in real-time. After completion, it will be exported to a JSONL file named `conversation_YYYYMMDD_HHMMSS.jsonl`.

## Output Format

The JSONL file contains:

1. **Metadata line** (first line):
```json
{
  "type": "metadata",
  "topic": "...",
  "claude_role": "...",
  "openai_role": "...",
  "claude_model": "...",
  "openai_model": "...",
  "max_turns": 5,
  "total_messages": 10,
  "export_time": "2026-01-16T..."
}
```

2. **Conversation entries** (one per line):
```json
{
  "turn": 1,
  "agent": "claude",
  "role": "user",
  "content": "...",
  "timestamp": "2026-01-16T..."
}
```

## Example Configurations

### Debate Format
```json
{
  "topic": "Should AI-generated art be considered 'real' art?",
  "claude_role": "Traditional Artist defending human creativity",
  "openai_role": "AI Art Advocate arguing for technological progress",
  "max_turns": 5
}
```

### Interview Format
```json
{
  "topic": "Building a successful content creator business",
  "claude_role": "Podcast Host interviewing experts",
  "openai_role": "Successful Content Creator sharing insights",
  "max_turns": 4
}
```

### Brainstorming Format
```json
{
  "topic": "Innovative content ideas for 2026",
  "claude_role": "Creative Director brainstorming",
  "openai_role": "Marketing Strategist providing feedback",
  "max_turns": 5
}
```

## Tips

1. **Keep turns reasonable**: 4-5 turns (8-10 total messages) works well
2. **Be specific with roles**: Clear roles lead to better conversations
3. **Use instructions**: Detailed instructions help agents stay in character
4. **Adjust temperature**: Lower (0.5) for focused, higher (0.9) for creative
5. **Edit between runs**: Modify the config file for each new conversation

## Troubleshooting

- **"Config file not found"**: Create `conversation_config.json` first
- **API errors**: Check your API keys in `.env` file
- **Import errors**: Make sure you're in the `python-agents` directory
- **Missing dependencies**: Run `pip install -r requirements.txt`
