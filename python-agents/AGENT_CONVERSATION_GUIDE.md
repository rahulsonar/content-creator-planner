# Agent Conversation Script - Quick Reference

## What You Get

✅ **agent_conversation.py** - Independent Python script for AI-to-AI conversations  
✅ **conversation_config.json** - Your editable configuration file  
✅ **README_CONVERSATION.md** - Full documentation  
✅ **run_conversation.sh** - Quick run script for Docker  
✅ **conversation_config_example2.json** - Additional example config  

## Quick Start (3 Steps)

### 1. Edit the Topic (conversation_config.json)
```json
{
  "topic": "Your conversation topic here",
  "claude_role": "What role Claude plays",
  "openai_role": "What role OpenAI plays",
  "max_turns": 5
}
```

### 2. Run the Script

**Option A - Using the helper script:**
```bash
./python-agents/run_conversation.sh
```

**Option B - Direct command:**
```bash
cd python-agents
python agent_conversation.py
```

**Option C - Inside Docker:**
```bash
docker exec -it content-planner-python-agents python agent_conversation.py
```

### 3. Check the Output
- Real-time conversation displayed in terminal
- Exported to `conversation_YYYYMMDD_HHMMSS.jsonl`

## How It Works

1. **Claude (User)** initiates the conversation based on the topic
2. **OpenAI (Assistant)** responds
3. They go back and forth for the number of turns you specify
4. Everything is saved to a JSONL file

## Configuration Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| topic | ✅ Yes | - | Conversation subject |
| claude_role | ✅ Yes | - | Claude's persona |
| openai_role | ✅ Yes | - | OpenAI's persona |
| max_turns | ✅ Yes | - | Number of exchanges (4-5 recommended) |
| claude_instructions | ❌ No | "" | Detailed behavior for Claude |
| openai_instructions | ❌ No | "" | Detailed behavior for OpenAI |
| temperature | ❌ No | 0.7 | Creativity (0.0-1.0) |
| max_tokens | ❌ No | 800 | Max response length |
| claude_model | ❌ No | claude-3-5-sonnet-20241022 | Claude model |
| openai_model | ❌ No | gpt-4 | OpenAI model |

## Example Topics

### 🎨 Creative Brainstorming
```json
{
  "topic": "Viral video ideas for eco-conscious brands",
  "claude_role": "Social Media Manager at eco-brand",
  "openai_role": "Viral Content Strategist",
  "max_turns": 5
}
```

### 🎯 Problem Solving
```json
{
  "topic": "Dealing with algorithm changes on Instagram",
  "claude_role": "Fashion Influencer losing reach",
  "openai_role": "Instagram Growth Expert",
  "max_turns": 4
}
```

### 🤝 Interview Style
```json
{
  "topic": "Journey to 1M YouTube subscribers",
  "claude_role": "Podcast Host",
  "openai_role": "Successful YouTuber sharing story",
  "max_turns": 5
}
```

### 🥊 Debate Format
```json
{
  "topic": "Is consistent posting or quality more important?",
  "claude_role": "Quality-over-quantity advocate",
  "openai_role": "Consistency-first strategist",
  "max_turns": 5
}
```

## Output Format (JSONL)

**First line (metadata):**
```json
{
  "type": "metadata",
  "topic": "...",
  "total_messages": 10,
  "export_time": "2026-01-16T..."
}
```

**Subsequent lines (messages):**
```json
{
  "turn": 1,
  "agent": "claude",
  "role": "user",
  "content": "The message content...",
  "timestamp": "2026-01-16T..."
}
```

## Tips for Best Results

1. **Clear Roles**: Specific roles = better conversations
   - ❌ "Expert" → ✅ "Instagram Growth Strategist with 5+ years experience"

2. **Concrete Topics**: Focused topics = more useful output
   - ❌ "Content creation" → ✅ "Creating engaging hooks for short-form videos"

3. **Use Instructions**: Guide agent behavior
   - For Claude: "Ask follow-up questions", "Share personal examples"
   - For OpenAI: "Provide actionable tips", "Use specific examples"

4. **Optimal Length**: 4-5 turns keeps conversations focused
   - Too short (2-3): Not enough depth
   - Too long (7+): May lose focus

5. **Temperature Settings**:
   - 0.5-0.6: Professional, focused discussions
   - 0.7-0.8: Natural, creative conversations
   - 0.9+: Highly creative, less predictable

## Customization Examples

### Change Models
```json
{
  "claude_model": "claude-3-opus-20240229",
  "openai_model": "gpt-4-turbo"
}
```

### Longer Responses
```json
{
  "max_tokens": 1200,
  "temperature": 0.8
}
```

### More Exchanges
```json
{
  "max_turns": 7
}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Config file not found" | Create `conversation_config.json` in python-agents/ |
| API key errors | Check `.env` file has ANTHROPIC_API_KEY and OPENAI_API_KEY |
| Import errors | Run from python-agents/ directory |
| Permission denied | Run `chmod +x agent_conversation.py` |

## File Locations

```
python-agents/
├── agent_conversation.py          # Main script
├── conversation_config.json       # Your config (edit this!)
├── conversation_config_example2.json  # Example config
├── run_conversation.sh           # Quick run helper
├── README_CONVERSATION.md        # Full docs
└── conversation_YYYYMMDD_HHMMSS.jsonl  # Output (auto-generated)
```

## Next Steps

1. ✏️ Edit `conversation_config.json` with your topic
2. ▶️ Run the script: `python agent_conversation.py`
3. 📄 Review the generated `.jsonl` file
4. 🔄 Edit config and run again for different conversations

**Happy conversing! 🤖💬**
