import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { verifyToken } from '@/lib/auth/helpers';

export async function GET(request: NextRequest) {
  try {
    // Extract user info from token
    const token = request.cookies.get('auth-token')?.value;
    let userId = 'anonymous';
    
    if (token) {
      const decoded = verifyToken(token);
      if (decoded) {
        userId = decoded.userId;
      }
    }

    // Fetch conversations for the user, ordered by most recent
    const conversations = await prisma.conversation.findMany({
      where: {
        userId: userId,
      },
      orderBy: {
        updatedAt: 'desc',
      },
      select: {
        id: true,
        title: true,
        messages: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    // Format conversations for display
    const formattedConversations = conversations.map((conv) => {
      const messages = conv.messages as any[];
      const lastMessage = messages && messages.length > 0 ? messages[messages.length - 1] : null;
      const firstUserMessage = messages && messages.length > 0 
        ? messages.find((m: any) => m.role === 'user') 
        : null;
      
      return {
        id: conv.id,
        title: conv.title || (firstUserMessage?.content?.substring(0, 60) + '...' || 'New Conversation'),
        lastMessage: lastMessage?.content?.substring(0, 100) + '...' || '',
        messageCount: messages?.length || 0,
        createdAt: conv.createdAt,
        updatedAt: conv.updatedAt,
      };
    });

    return NextResponse.json(formattedConversations);
  } catch (error) {
    console.error('Error fetching conversations:', error);
    return NextResponse.json(
      { error: 'Failed to fetch conversations' },
      { status: 500 }
    );
  }
}
