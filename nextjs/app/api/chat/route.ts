import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth/helpers';
import { prisma } from '@/lib/prisma';
import { getInternalApiSecret } from '@/lib/auth/secrets';

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
    const token = request.cookies.get('auth-token')?.value;
    let userId: number | null = null;
    let userName = null;
    
    if (token) {
      const decoded = verifyToken(token);
      if (decoded) {
        userId = decoded.userId;
        userName = decoded.name;
        console.log('Authenticated userId:', userId, 'userName:', userName);
      } else {
        console.error('Token verification failed: invalid token');
      }
    } else {
      console.warn('No token found in cookies');
    }

    // If this is the first conversation (no conversationId) and we have a userId,
    // fetch the latest user name from the database to ensure context manager has accurate info
    if (!conversationId && userId !== null) {
      try {
        const user = await prisma.user.findUnique({
          where: { id: userId as number },
          select: { name: true }
        });
        
        if (user?.name) {
          userName = user.name;
          console.log('Fetched user name from DB for first conversation:', userName);
        }
      } catch (dbError) {
        console.error('Failed to fetch user name from DB:', dbError);
        // Continue with userName from token if DB fetch fails
      }
    }

    // Call Python Planning Agent API
    const response = await fetch(`${PYTHON_API_URL}/api/planning/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId !== null ? userId.toString() : '',
        'X-User-Name': userName || '',
        'X-Internal-Secret': getInternalApiSecret(),
      },
      body: JSON.stringify({
        message: message,
        conversationId: conversationId,
        context: userName ? { user_name: userName } : null,
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
