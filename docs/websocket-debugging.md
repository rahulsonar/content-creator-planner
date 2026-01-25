## WebSocket Connection Debugging Guide

### Issue
When accessing the chat page at `http://192.168.29.106:3000/chat/[chatId]`, it shows "connecting" but never connects to the WebSocket server.

### Root Cause
The WebSocket connection requires:
1. A valid JWT token stored in `localStorage` under the key `'auth-token'`
2. The token must be available BEFORE the WebSocket hook tries to connect

### Quick Diagnosis

#### Option 1: Use the Test Page
Access: `http://192.168.29.106:3000/chat/test-ws`

This page will:
- Show you if a token exists in localStorage
- Allow you to store a test token
- Test the WebSocket connection manually
- Show detailed connection logs

#### Option 2: Browser Console Check

Open browser console (F12) and run:

```javascript
// Check if token exists
console.log('Token:', localStorage.getItem('auth-token'));

// Check if user exists
console.log('User:', localStorage.getItem('user'));

// Manually store the test token
localStorage.setItem('auth-token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjbWs0MmU4NnIwMDAwcDRueXVwM3QxMXhnIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsIm5hbWUiOiJBZG1pbiBVc2VyIiwiaWF0IjoxNzY4OTg1MDg2LCJleHAiOjE3Njk1ODk4ODZ9.T0jF1EfgXrKjeHQhd5O_RPYheQ7QhFpo-y83Wf0FaRM');

localStorage.setItem('user', JSON.stringify({
  userId: 'cmk42e86r0000p4nyup3t11xg',
  email: 'admin@example.com',
  name: 'Admin User'
}));

// Reload the page
location.reload();
```

#### Option 3: Log In First

1. Go to: `http://192.168.29.106:3000/login`
2. Log in with:
   - Email: `admin@example.com`
   - Password: `Admin123!`
3. After login, navigate to the chat page

### How the WebSocket Connection Works

1. **Page loads** → `useWebSocket` hook initializes
2. **Hook checks** → `getStoredToken()` looks for token in localStorage
3. **If token exists** → Connects to `ws://192.168.29.106:3000/api/ws`
4. **On connection** → Sends auth message with token
5. **Server verifies** → Returns `auth_success` message
6. **Client subscribes** → Sends subscribe message with conversationId
7. **Ready** → Can send/receive messages

### Why "Connecting" Stuck?

Possible reasons:
1. ❌ **No token in localStorage** (most likely)
   - Solution: Log in first or manually store token
   
2. ❌ **Token expired**
   - Check expiration: The test token expires at `1769589886` (Feb 2026)
   - Solution: Get a new token by logging in

3. ❌ **WebSocket server not responding**
   - Check server logs: `docker logs content-planner-app`
   - Server should log: `[WS Server] Upgrade request`

4. ❌ **Browser blocking WebSocket**
   - Check browser console for errors
   - Check if mixed content (HTTP page trying WSS)

### Server-Side Debugging

```bash
# Watch WebSocket server logs in real-time
docker logs -f content-planner-app 2>&1 | grep -i "WS"

# Check if server is listening
docker exec -it content-planner-app netstat -tlnp | grep 3000

# Test from container
docker exec -it content-planner-app curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Host: localhost:3000" \
  -H "Origin: http://localhost:3000" \
  http://localhost:3000/api/ws
```

### Expected Server Logs When Connecting

```
[WS Server] Upgrade request: {
  pathname: '/api/ws',
  host: '192.168.29.106:3000',
  origin: 'http://192.168.29.106:3000',
  upgrade: 'websocket'
}
[WS Server] Upgrade successful
[WS Server] New connection established
[WS Server] Received message type: auth
[WS Server] Authenticated user: cmk42e86r0000p4nyup3t11xg
[WS Server] Received message type: subscribe
[WS Server] Added connection for 1fd29fe0-53f2-43c6-81e7-1baacf87882c
```

### Testing WebSocket from Command Line

```bash
# Using wscat (install: npm install -g wscat)
wscat -c ws://192.168.29.106:3000/api/ws

# After connection, send:
{"type":"auth","token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjbWs0MmU4NnIwMDAwcDRueXVwM3QxMXhnIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsIm5hbWUiOiJBZG1pbiBVc2VyIiwiaWF0IjoxNzY4OTg1MDg2LCJleHAiOjE3Njk1ODk4ODZ9.T0jF1EfgXrKjeHQhd5O_RPYheQ7QhFpo-y83Wf0FaRM"}

# Then subscribe:
{"type":"subscribe","conversationId":"1fd29fe0-53f2-43c6-81e7-1baacf87882c"}
```

### Summary

**Most likely solution**: 
1. Open browser console
2. Store the token (see Option 2 code above)
3. Reload the page
4. Connection should work

Or simply log in first at `/login` before accessing the chat page.
