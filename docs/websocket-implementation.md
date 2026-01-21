# WebSocket Implementation Summary

## Overview
Successfully implemented real-time WebSocket communication for chat functionality. Users can now send messages and receive responses asynchronously without blocking the UI.

## Architecture

### 1. Frontend (Next.js Client)
- **WebSocket Hook** (`lib/hooks/useWebSocket.ts`)
  - Manages connection lifecycle (connect, disconnect, reconnect)
  - Handles authentication and subscription to conversations
  - Queues messages when disconnected
  - Filters messages by conversationId to prevent cross-conversation mixing
  - Provides connection status indicators

- **Chat Page** (`app/(app)/chat/[chatId]/page.tsx`)
  - Uses WebSocket hook for real-time updates
  - Shows live status indicator (Connected/Processing/Reconnecting)
  - Auto-scrolls to new messages
  - Disables input during processing

### 2. Next.js Backend
- **Custom Server** (`server.js`)
  - Extends Next.js with WebSocket support
  - Handles WebSocket upgrades on `/api/ws` endpoint
  - Manages active connections per conversationId
  - Forwards messages to Python API
  - Exposes `global.wsBroadcast()` for webhooks

- **Webhook Endpoint** (`app/api/chat/webhook/route.ts`)
  - Receives completion notifications from Python
  - Broadcasts to specific conversation's WebSocket clients only
  - Handles error and status updates

### 3. Python FastAPI Backend
- **Background Tasks** (`api/routes.py`)
  - Modified `/api/planning/chat` to use FastAPI BackgroundTasks
  - Returns `202 Accepted` immediately
  - Processes agent call asynchronously in background
  - Calls Next.js webhook when complete

- **Webhook Notifications** (`api/routes.py`)
  - `notify_websocket()` function sends HTTP POST to Next.js
  - Includes conversationId, message, status, or error
  - Uses httpx for async HTTP requests

## Message Flow

```
User types message in UI
  ↓
Frontend adds to messages array (optimistic update)
  ↓
WebSocket sends message to server
  ↓
Custom Next.js server forwards to Python API
  ↓
Python returns 202 Accepted immediately
  ↓
Next.js sends "processing" status via WebSocket
  ↓
User sees "Processing..." indicator
  ↓
Python agent processes in background (30+ seconds)
  ↓
Python calls Next.js webhook with result
  ↓
Next.js broadcasts to WebSocket clients for that conversationId
  ↓
Frontend receives message and appends to UI
  ↓
Auto-scroll to new message
```

## Key Features

### Connection Isolation
- Each conversation has its own WebSocket subscription
- Messages are filtered by conversationId
- Multiple open chats don't interfere with each other

### Resilience
- Auto-reconnect on disconnection (3-second delay)
- Message queueing when offline
- Connection status indicators

### Security
- JWT authentication on WebSocket connection
- Internal secret for webhook validation
- User ID verification

## Files Modified/Created

### Created
1. `nextjs/lib/websocket/manager.ts` - Connection manager
2. `nextjs/app/api/ws/route.ts` - WebSocket API route (unused, using custom server instead)
3. `nextjs/app/api/chat/webhook/route.ts` - Webhook endpoint
4. `nextjs/lib/hooks/useWebSocket.ts` - React WebSocket hook
5. `nextjs/server.js` - Custom Next.js server with WebSocket
6. `nextjs/next.config.js` - Next.js configuration

### Modified
1. `nextjs/app/(app)/chat/[chatId]/page.tsx` - Updated to use WebSocket
2. `nextjs/package.json` - Changed dev/start scripts to use custom server
3. `python-agents/api/routes.py` - Added background tasks and webhooks
4. `python-agents/config/settings.py` - Added NEXTJS_WEBHOOK_URL

### Dependencies Added
- `nextjs`: `ws`, `@types/ws`
- `python`: `httpx` (already installed)

## Usage

### Start Services
```bash
# Rebuild and start containers
docker compose up -d --build

# View logs
docker logs -f content-planner-app
docker logs -f content-planner-python
```

### Test WebSocket
1. Open browser to http://localhost:3000/chat
2. Send a message (creates new conversation)
3. Redirected to `/chat/[conversationId]`
4. WebSocket connects automatically
5. Status indicator shows "Live" (green)
6. Agent processes in background
7. Response appears in real-time when ready

### Multiple Conversations
1. Open two browser tabs/windows
2. Each with different conversationId
3. Send messages in both
4. Each receives only its own responses
5. No cross-contamination

## Configuration

### Environment Variables
```bash
# Python .env
NEXTJS_WEBHOOK_URL=http://nextjs:3000/api/chat/webhook
INTERNAL_API_SECRET=dev-secret-change-in-production

# Next.js .env
INTERNAL_API_SECRET=dev-secret-change-in-production
PYTHON_API_URL=http://python-agents:8000
```

## Troubleshooting

### WebSocket Not Connecting
- Check browser console for connection errors
- Verify custom server is running (not `next dev`)
- Check JWT token is valid

### Messages Not Appearing
- Check Python webhook logs: `docker logs content-planner-python`
- Verify NEXTJS_WEBHOOK_URL is correct
- Check conversationId matches in webhook payload

### Multiple Messages Appearing
- Check conversationId filtering in frontend
- Verify WebSocket connection cleanup on unmount

## Future Enhancements
1. **Streaming responses**: Stream agent output word-by-word
2. **Typing indicators**: Show when agent is thinking
3. **Read receipts**: Track message delivery
4. **Reconnection UX**: Better offline handling
5. **Rate limiting**: Prevent WebSocket abuse
6. **Heartbeat**: Automatic ping/pong to keep connections alive (already implemented)
