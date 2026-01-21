/**
 * WebSocket Hook for Real-Time Chat
 * Manages WebSocket connection lifecycle and message handling
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { getStoredToken } from '@/lib/auth/client';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  model?: string;
}

interface UseWebSocketProps {
  conversationId: string | null;
  onMessage?: (message: Message) => void;
  onError?: (error: string) => void;
  onStatusChange?: (status: 'connected' | 'disconnected' | 'processing') => void;
}

export function useWebSocket({
  conversationId,
  onMessage,
  onError,
  onStatusChange,
}: UseWebSocketProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const messageQueueRef = useRef<any[]>([]);
  const isConnectingRef = useRef(false); // Prevent multiple simultaneous connections

  const connect = useCallback(() => {
    if (!conversationId) {
      console.log('[WS Hook] No conversationId, skipping connection');
      return;
    }

    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current) {
      console.log('[WS Hook] Already connecting, skipping');
      return;
    }

    if (wsRef.current) {
      const state = wsRef.current.readyState;
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        console.log('[WS Hook] Already connected or connecting, skipping');
        return;
      }
    }

    isConnectingRef.current = true;

    const token = getStoredToken();
    if (!token) {
      console.error('[WS Hook] No auth token available');
      onError?.('Not authenticated');
      isConnectingRef.current = false;
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;

    console.log('[WS Hook] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS Hook] Connected');
      isConnectingRef.current = false;
      setIsConnected(true);
      onStatusChange?.('connected');

      // Authenticate
      ws.send(JSON.stringify({
        type: 'auth',
        token: token,
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WS Hook] Received:', data.type);

        switch (data.type) {
          case 'connected':
            console.log('[WS Hook] Welcome message received');
            break;

          case 'auth_success':
            console.log('[WS Hook] Authenticated as:', data.userId);
            // Subscribe to conversation
            if (conversationId) {
              ws.send(JSON.stringify({
                type: 'subscribe',
                conversationId: conversationId,
              }));
            }
            break;

          case 'subscribed':
            console.log('[WS Hook] Subscribed to conversation:', data.conversationId);
            // Process any queued messages
            if (messageQueueRef.current.length > 0) {
              console.log('[WS Hook] Processing queued messages:', messageQueueRef.current.length);
              messageQueueRef.current.forEach((msg) => {
                ws.send(JSON.stringify(msg));
              });
              messageQueueRef.current = [];
            }
            break;

          case 'processing':
            console.log('[WS Hook] Message is processing...');
            setIsProcessing(true);
            onStatusChange?.('processing');
            break;

          case 'message':
            // Only process if it's for our conversation
            if (data.conversationId === conversationId) {
              console.log('[WS Hook] Received message for our conversation');
              setIsProcessing(false);
              onStatusChange?.('connected');

              const message: Message = {
                id: Date.now(),
                role: data.role || 'assistant',
                content: data.content,
                timestamp: new Date(data.timestamp || Date.now()),
                model: data.model,
              };

              onMessage?.(message);
            } else {
              console.log('[WS Hook] Ignoring message for different conversation:', data.conversationId);
            }
            break;

          case 'error':
            console.error('[WS Hook] Error:', data.error);
            setIsProcessing(false);
            onError?.(data.error);
            break;

          case 'pong':
            // Heartbeat response
            break;

          default:
            console.log('[WS Hook] Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('[WS Hook] Error parsing message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS Hook] WebSocket error:', {
        error: error,
        readyState: ws.readyState,
        readyStateText: ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState],
        url: wsUrl,
      });
      isConnectingRef.current = false;
      // Don't set disconnected here - wait for onclose
    },

    ws.onclose = (event) => {
      console.log('[WS Hook] Disconnected', {
        code: event.code,
        reason: event.reason || 'No reason provided',
        wasClean: event.wasClean,
      });
      isConnectingRef.current = false;
      setIsConnected(false);
      setIsProcessing(false);
      onStatusChange?.('disconnected');

      // Only show error to user if it wasn't a clean close
      if (!event.wasClean && event.code !== 1000) {
        onError?.(`Connection closed unexpectedly (code: ${event.code})`);
      }

      // Attempt to reconnect after 3 seconds if not a normal closure or component unmounting
      if (event.code !== 1000 && event.code !== 1001 && conversationId) {
        console.log('[WS Hook] Will attempt to reconnect in 3 seconds...');
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WS Hook] Attempting to reconnect...');
          connect();
        }, 3000);
      }
    };
  }, [conversationId, onMessage, onError, onStatusChange]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsProcessing(false);
  }, []);

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[WS Hook] WebSocket not ready, queueing message');
      messageQueueRef.current.push({
        type: 'message',
        content: content,
      });
      return;
    }

    if (!conversationId) {
      console.error('[WS Hook] No conversationId set');
      onError?.('No conversation selected');
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content: content,
    }));
  }, [conversationId, onError]);

  // Connect when conversationId changes
  useEffect(() => {
    if (!conversationId) {
      console.log('[WS Hook] No conversationId in effect');
      return;
    }

    console.log('[WS Hook] Effect running for conversationId:', conversationId);
    connect();

    return () => {
      console.log('[WS Hook] Cleanup triggered for conversationId:', conversationId);
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }

      if (wsRef.current) {
        console.log('[WS Hook] Cleaning up - closing connection');
        const ws = wsRef.current;
        wsRef.current = null; // Clear ref first to prevent reconnect attempts
        isConnectingRef.current = false;
        ws.close(1000, 'Component unmounting');
      }

      setIsConnected(false);
      setIsProcessing(false);
    };
  }, [conversationId]); // Only depend on conversationId, not connect

  // Heartbeat to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, [isConnected]);

  return {
    isConnected,
    isProcessing,
    sendMessage,
    disconnect,
  };
}
