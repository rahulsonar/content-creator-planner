import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth/helpers';

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://python-agents:8000';

export async function POST(request: NextRequest) {
  try {
    const { message, conversationId } = await request.json();

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Extract user info from token for internal API call
    const token = request.cookies.get('token')?.value;
    let userId = 'anonymous';
    
    if (token) {
      try {
        const decoded = verifyToken(token);
        userId = decoded.userId;
      } catch (error) {
        console.error('Token verification failed:', error);
      }
    }

    // Call Python Planning Agent API
    const response = await fetch(`${PYTHON_API_URL}/api/planning/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId,
        'X-Internal-Secret': process.env.INTERNAL_API_SECRET || 'dev-secret-change-in-production',
      },
      body: JSON.stringify({
        message: message,
        conversationId: conversationId,
        context: null, // TODO: Pass user context from profile
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Python API Error:', errorData);
      throw new Error(errorData.detail || 'Python API request failed');
    }

    const data = await response.json();

    return NextResponse.json({
      role: 'assistant',
      content: data.message,
      model: data.model,
      conversationId: data.conversationId,
    });
  } catch (error: any) {
    console.error('Chat API Error:', error);

    return NextResponse.json(
      { error: 'Failed to get AI response', details: error?.message },
      { status: 500 }
    );
  }
}
