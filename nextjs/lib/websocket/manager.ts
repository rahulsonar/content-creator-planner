/**
 * WebSocket Connection Manager
 * Manages active WebSocket connections per conversation
 */

import { WebSocket } from 'ws';

interface ConnectionInfo {
  ws: WebSocket;
  userId: string;
  conversationId: string;
  connectedAt: Date;
}

class WebSocketManager {
  private connections: Map<string, Set<ConnectionInfo>>;

  constructor() {
    this.connections = new Map();
  }

  /**
   * Add a WebSocket connection for a conversation
   */
  addConnection(conversationId: string, ws: WebSocket, userId: string): void {
    if (!this.connections.has(conversationId)) {
      this.connections.set(conversationId, new Set());
    }

    const connectionInfo: ConnectionInfo = {
      ws,
      userId,
      conversationId,
      connectedAt: new Date(),
    };

    this.connections.get(conversationId)!.add(connectionInfo);

    console.log(`[WS] Added connection for conversation ${conversationId}, user ${userId}`);
    console.log(`[WS] Total connections for ${conversationId}: ${this.connections.get(conversationId)!.size}`);

    // Clean up on close
    ws.on('close', () => {
      this.removeConnection(conversationId, ws);
    });
  }

  /**
   * Remove a WebSocket connection
   */
  removeConnection(conversationId: string, ws: WebSocket): void {
    const connections = this.connections.get(conversationId);
    if (!connections) return;

    const toRemove = Array.from(connections).find((conn) => conn.ws === ws);
    if (toRemove) {
      connections.delete(toRemove);
      console.log(`[WS] Removed connection for conversation ${conversationId}`);

      // Clean up empty sets
      if (connections.size === 0) {
        this.connections.delete(conversationId);
        console.log(`[WS] Removed empty conversation ${conversationId}`);
      }
    }
  }

  /**
   * Broadcast message to all connections for a specific conversation
   */
  broadcast(conversationId: string, message: any): void {
    const connections = this.connections.get(conversationId);
    if (!connections || connections.size === 0) {
      console.log(`[WS] No active connections for conversation ${conversationId}`);
      return;
    }

    const messageStr = JSON.stringify(message);
    let sentCount = 0;

    connections.forEach((conn) => {
      if (conn.ws.readyState === WebSocket.OPEN) {
        conn.ws.send(messageStr);
        sentCount++;
      }
    });

    console.log(`[WS] Broadcast to ${sentCount}/${connections.size} connections for ${conversationId}`);
  }

  /**
   * Get all active connections for a conversation
   */
  getConnections(conversationId: string): ConnectionInfo[] {
    const connections = this.connections.get(conversationId);
    return connections ? Array.from(connections) : [];
  }

  /**
   * Check if there are active connections for a conversation
   */
  hasConnections(conversationId: string): boolean {
    const connections = this.connections.get(conversationId);
    return connections ? connections.size > 0 : false;
  }

  /**
   * Get total number of active connections across all conversations
   */
  getTotalConnections(): number {
    let total = 0;
    this.connections.forEach((connections) => {
      total += connections.size;
    });
    return total;
  }

  /**
   * Get all active conversation IDs
   */
  getActiveConversations(): string[] {
    return Array.from(this.connections.keys());
  }
}

// Singleton instance
export const wsManager = new WebSocketManager();
