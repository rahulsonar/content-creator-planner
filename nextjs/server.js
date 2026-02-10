/**
 * Custom Next.js Server with WebSocket Support
 * Handles WebSocket upgrades while serving Next.js app
 */

const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');
const { WebSocketServer } = require('ws');
const jwt = require('jsonwebtoken');

const dev = process.env.NODE_ENV !== 'production';
const hostname = '0.0.0.0'; // Listen on all interfaces in Docker
const port = parseInt(process.env.PORT || '3000', 10);
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

// Simple JWT verification
function verifyToken(token) {
  try {
    return jwt.verify(token, JWT_SECRET);
  } catch (error) {
    console.error('[Server] Token verification failed:', error.message);
    return null;
  }
}

// WebSocket connection manager
const wsConnections = new Map(); // conversationId -> Set<WebSocket>
const processingConversations = new Set(); // Track conversations with ongoing agent processing

async function addConnection(conversationId, ws, userId) {
  if (!wsConnections.has(conversationId)) {
    wsConnections.set(conversationId, new Set());
  }
  wsConnections.get(conversationId).add({ ws, userId });
  console.log(`[WS Server] Added connection for ${conversationId}, user ${userId}`);
  
  // BUGFIX: Check actual database for IN_PROGRESS logs, not just in-memory state
  // The in-memory Set can get out of sync after server restarts or crashes
  try {
    const { PrismaClient } = require('@prisma/client');
    const prisma = new PrismaClient();
    
    const inProgressCount = await prisma.agentCallLog.count({
      where: {
        conversationId: parseInt(conversationId),
        status: 'IN_PROGRESS'
      }
    });
    
    await prisma.$disconnect();
    
    if (inProgressCount > 0) {
      console.log(`[WS Server] Found ${inProgressCount} IN_PROGRESS logs for conversation ${conversationId}`);
      processingConversations.add(conversationId);
      ws.send(JSON.stringify({ type: 'processing' }));
    } else {
      // Ensure we remove from processing set if no actual processing is happening
      processingConversations.delete(conversationId);
      console.log(`[WS Server] No IN_PROGRESS logs for conversation ${conversationId}`);
    }
  } catch (error) {
    console.error(`[WS Server] Error checking processing state for ${conversationId}:`, error);
    // Fallback to in-memory state on error
    if (processingConversations.has(conversationId)) {
      console.log(`[WS Server] Falling back to in-memory state - conversation ${conversationId} marked as processing`);
      ws.send(JSON.stringify({ type: 'processing' }));
    }
  }
}

function removeConnection(conversationId, ws) {
  const connections = wsConnections.get(conversationId);
  if (connections) {
    const toRemove = Array.from(connections).find((conn) => conn.ws === ws);
    if (toRemove) {
      connections.delete(toRemove);
      if (connections.size === 0) {
        wsConnections.delete(conversationId);
      }
    }
  }
}

function broadcast(conversationId, message) {
  const connections = wsConnections.get(conversationId);
  if (!connections) return;

  const messageStr = JSON.stringify(message);
  connections.forEach(({ ws }) => {
    if (ws.readyState === 1) { // WebSocket.OPEN
      ws.send(messageStr);
    }
  });
  
  // Track processing state
  if (message.type === 'processing') {
    processingConversations.add(conversationId);
    console.log(`[WS Server] Marked conversation ${conversationId} as processing`);
  } else if (message.type === 'message' || message.type === 'error') {
    processingConversations.delete(conversationId);
    console.log(`[WS Server] Removed conversation ${conversationId} from processing`);
  }
}

app.prepare().then(() => {
  const server = createServer(async (req, res) => {
    try {
      const parsedUrl = parse(req.url, true);
      await handle(req, res, parsedUrl);
    } catch (err) {
      console.error('Error handling request:', err);
      res.statusCode = 500;
      res.end('Internal server error');
    }
  });

  // Create WebSocket server
  const wss = new WebSocketServer({ noServer: true });

  // Handle WebSocket upgrade requests
  server.on('upgrade', (request, socket, head) => {
    const { pathname } = parse(request.url);

    console.log('[WS Server] Upgrade request:', {
      pathname,
      host: request.headers.host,
      origin: request.headers.origin,
      upgrade: request.headers.upgrade,
    });

    // Handle custom WebSocket connections for chat
    if (pathname === '/api/ws') {
      wss.handleUpgrade(request, socket, head, (ws) => {
        console.log('[WS Server] Upgrade successful');
        wss.emit('connection', ws, request);
      });
    } 
    // Allow Next.js HMR WebSocket connections in development
    else if (dev && pathname.startsWith('/_next/webpack-hmr')) {
      // Let Next.js handle its own HMR WebSocket
      // Don't destroy - Next.js will handle it internally
    }
    else {
      console.log('[WS Server] Rejected upgrade for:', pathname);
      socket.destroy();
    }
  });

  // Handle WebSocket connections
  wss.on('connection', (ws) => {
    console.log('[WS Server] New connection established');

    let userId = null;
    let conversationId = null;
    let isAuthenticated = false;

    // Set up ping/pong for keep-alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === 1) { // WebSocket.OPEN
        ws.ping();
      }
    }, 30000); // Ping every 30 seconds

    ws.on('pong', () => {
      console.log('[WS Server] Received pong');
    });

    ws.on('error', (error) => {
      console.error('[WS Server] WebSocket error:', error.message, {
        readyState: ws.readyState,
        userId,
        conversationId,
      });
    });

    ws.on('message', async (data) => {
      try {
        const message = JSON.parse(data.toString());
        console.log('[WS Server] Received message type:', message.type, {
          hasToken: !!message.token,
          hasConversationId: !!message.conversationId,
          hasContent: !!message.content,
          messageConversationId: message.conversationId, // Show what's in the message
          serverUserId: userId, // Show server's stored state
          serverConversationId: conversationId,
        });

        switch (message.type) {
          case 'auth':
            const decoded = verifyToken(message.token);
            if (!decoded) {
              ws.send(JSON.stringify({ type: 'error', error: 'Invalid token' }));
              ws.close();
              return;
            }
            userId = decoded.userId;
            isAuthenticated = true;
            ws.send(JSON.stringify({ type: 'auth_success', userId }));
            break;

          case 'subscribe':
            if (!userId) {
              ws.send(JSON.stringify({ type: 'error', error: 'Not authenticated' }));
              return;
            }
            conversationId = message.conversationId;
            await addConnection(conversationId, ws, userId);
            ws.send(JSON.stringify({ type: 'subscribed', conversationId }));
            break;

          case 'message':
            if (!userId || !conversationId) {
              ws.send(JSON.stringify({ type: 'error', error: 'Not authenticated or subscribed' }));
              return;
            }

            // Mark conversation as processing
            processingConversations.add(conversationId);
            ws.send(JSON.stringify({ type: 'processing' }));
            // Also broadcast to all connected clients
            broadcast(conversationId, { type: 'processing' });

            // Forward to Python API
            const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://python-agents:8000';
            const response = await fetch(`${PYTHON_API_URL}/api/planning/chat`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-User-ID': userId,
                'X-Internal-Secret': process.env.INTERNAL_API_SECRET || 'dev-secret-change-in-production',
              },
              body: JSON.stringify({
                message: message.content,
                conversationId: conversationId,
                context: null,
              }),
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              processingConversations.delete(conversationId);
              ws.send(JSON.stringify({ type: 'error', error: errorData.detail || 'Processing failed' }));
            }
            break;

          case 'ping':
            ws.send(JSON.stringify({ type: 'pong' }));
            break;
        }
      } catch (error) {
        console.error('[WS Server] Error:', error);
        ws.send(JSON.stringify({ type: 'error', error: 'Invalid message' }));
      }
    });

    ws.on('close', (code, reason) => {
      console.log('[WS Server] Connection closed', {
        code,
        reason: reason.toString(),
        userId,
        conversationId,
        wasAuthenticated: isAuthenticated,
      });
      clearInterval(pingInterval);
      if (conversationId) {
        removeConnection(conversationId, ws);
      }
    });

    ws.send(JSON.stringify({ type: 'connected', message: 'Please authenticate' }));
    console.log('[WS Server] Sent welcome message');
  });

  // Export broadcast function for webhook
  global.wsBroadcast = broadcast;

  server.listen(port, (err) => {
    if (err) throw err;
    console.log(`> Ready on http://${hostname}:${port}`);
    console.log(`> WebSocket server ready on ws://${hostname}:${port}/api/ws`);
    if (hostname === '0.0.0.0') {
      console.log(`> Access from host: http://localhost:${port}`);
    }
  });
});
