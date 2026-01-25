import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const messageId = searchParams.get('messageId');
    const agentName = searchParams.get('agentName');
    const status = searchParams.get('status');
    const limit = parseInt(searchParams.get('limit') || '100');

    // Build where clause
    const where: any = {};
    if (messageId) where.messageId = messageId;
    if (agentName) where.agentName = agentName;
    if (status) where.status = status;

    // Fetch agent call logs
    const logs = await prisma.agentCallLog.findMany({
      where,
      orderBy: [
        { createdAt: 'desc' }
      ],
      take: limit,
    });

    // Group by messageId
    const groupedLogs = logs.reduce((acc: any, log) => {
      const msgId = log.messageId;
      if (!acc[msgId]) {
        acc[msgId] = [];
      }
      acc[msgId].push(log);
      return acc;
    }, {});

    return NextResponse.json({
      total: logs.length,
      messageCount: Object.keys(groupedLogs).length,
      groupedLogs,
      logs
    });
  } catch (error) {
    console.error('Error fetching agent logs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch agent logs' },
      { status: 500 }
    );
  }
}
