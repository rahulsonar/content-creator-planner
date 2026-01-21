/**
 * Webhook Endpoint for Python Agent Callbacks
 * Receives completion notifications and broadcasts to WebSocket clients
 */

import { NextRequest, NextResponse } from 'next/server';

const INTERNAL_API_SECRET = process.env.INTERNAL_API_SECRET || 'dev-secret-change-in-production';

export async function POST(request: NextRequest) {
  try {
    // Verify internal secret
    const secret = request.headers.get('X-Internal-Secret');
    if (secret !== INTERNAL_API_SECRET) {
      console.error('[Webhook] Unauthorized webhook attempt');
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { conversationId, message, role, model, status, error } = body;

    if (!conversationId) {
      return NextResponse.json(
        { error: 'conversationId is required' },
        { status: 400 }
      );
    }

    console.log(`[Webhook] Received callback for conversation ${conversationId}, status: ${status || 'message'}`);

    // Broadcast to WebSocket clients via global function
    // @ts-ignore - global broadcast function from custom server
    if (typeof global.wsBroadcast === 'function') {
      if (error) {
        // @ts-ignore
        global.wsBroadcast(conversationId, {
          type: 'error',
          conversationId,
          error: error,
        });
      } else if (status === 'processing') {
        // @ts-ignore
        global.wsBroadcast(conversationId, {
          type: 'status',
          conversationId,
          status: 'processing',
        });
      } else if (message) {
        // @ts-ignore
        global.wsBroadcast(conversationId, {
          type: 'message',
          conversationId,
          role: role || 'assistant',
          content: message,
          model: model || 'unknown',
          timestamp: new Date().toISOString(),
        });

        console.log(`[Webhook] Broadcast message to conversation ${conversationId}`);
      }

      return NextResponse.json({
        success: true,
        message: 'Webhook processed and broadcast to WebSocket clients',
      });
    } else {
      console.warn('[Webhook] WebSocket broadcast function not available - using fallback');
      
      // Fallback: Store in database only (WebSocket might not be running)
      return NextResponse.json({
        success: true,
        message: 'Message stored (WebSocket not available)',
      });
    }
  } catch (error: any) {
    console.error('[Webhook] Error processing webhook:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    );
  }
}
