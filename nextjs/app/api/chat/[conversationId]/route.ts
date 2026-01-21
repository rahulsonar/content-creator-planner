import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth/helpers';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ conversationId: string }> }
) {
  try {
    const { conversationId } = await params;

    // Extract user info from token
    const token = request.cookies.get('token')?.value || request.cookies.get('auth-token')?.value;
    let userId = 'anonymous';
    
    if (token) {
      const decoded = verifyToken(token);
      if (decoded) {
        userId = decoded.userId;
        console.log('Authenticated userId:', userId);
      } else {
        console.error('Token verification failed: invalid token');
        // Continue with anonymous for now instead of rejecting
        // This allows loading conversations from query string
      }
    } else {
      console.warn('No token found in cookies');
    }

    // Fetch conversation directly from database
    const conversation = await prisma.conversation.findUnique({
      where: { id: conversationId },
    });

    if (!conversation) {
      return NextResponse.json(
        { error: 'Conversation not found' },
        { status: 404 }
      );
    }

    // Verify user has access to this conversation
    // Allow access if: user is anonymous OR user owns the conversation
    if (userId !== 'anonymous' && conversation.userId !== userId) {
      return NextResponse.json(
        { error: 'Access denied' },
        { status: 403 }
      );
    }

    return NextResponse.json(conversation);
    
  } catch (error: any) {
    console.error('Get Conversation API Error:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve conversation', details: error?.message },
      { status: 500 }
    );
  }
}
