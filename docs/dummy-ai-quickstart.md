# Quick Start: Using Dummy AI Mode

## Enable Dummy Mode

1. Create or edit your `.env` file in the project root:
   ```bash
   cd /var/www/html/content-creator-planner
   echo "USE_DUMMY_AI=true" >> .env
   ```

2. Restart the Python agents service:
   ```bash
   docker compose restart python-agents
   ```

3. Open the chat interface at http://localhost:3000/chat

4. Send a message - you'll get dummy responses with no API costs!

## Disable Dummy Mode (Use Real AI)

1. Update your `.env` file:
   ```bash
   # Change to:
   USE_DUMMY_AI=false
   
   # Ensure you have API keys:
   OPENAI_API_KEY=your_actual_key
   ```

2. Restart the service:
   ```bash
   docker compose restart python-agents
   ```

## Test the Feature

Run the test script:
```bash
./test_dummy_ai.sh
```

This will send test messages and show you the responses.

## Check Logs

To confirm dummy mode is active:
```bash
docker logs content-planner-python | grep "DUMMY MODE"
```

You should see: `[DUMMY MODE] Processing chat for user: ...`

## Benefits

✅ No API costs during development  
✅ Test UI/UX without rate limits  
✅ Faster response times  
✅ Work offline  
✅ Perfect for demos  

## When to Use Each Mode

**Use Dummy Mode:**
- Frontend development
- UI/UX testing
- Basic feature testing
- Demos without API keys
- Learning the codebase

**Use Real AI:**
- Testing actual planning logic
- Evaluating AI responses
- Context retrieval testing
- Production deployment
- User acceptance testing
