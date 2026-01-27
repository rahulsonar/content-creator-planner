import { prisma } from '@/lib/prisma';

/**
 * Generate next task key in format CCP-XXX
 * E.g., CCP-001, CCP-002, ..., CCP-999, CCP-1000
 */
export async function generateTaskKey(): Promise<string> {
  try {
    // Get the highest task key number
    const latestTask = await prisma.task.findFirst({
      where: {
        taskKey: {
          startsWith: 'CCP-',
        },
      },
      orderBy: {
        taskKey: 'desc',
      },
      select: {
        taskKey: true,
      },
    });

    let nextNumber = 1;

    if (latestTask?.taskKey) {
      // Extract number from CCP-XXX format
      const match = latestTask.taskKey.match(/CCP-(\d+)/);
      if (match && match[1]) {
        nextNumber = parseInt(match[1], 10) + 1;
      }
    }

    // Pad with zeros (minimum 3 digits)
    const paddedNumber = String(nextNumber).padStart(3, '0');
    return `CCP-${paddedNumber}`;
  } catch (error) {
    console.error('Error generating task key:', error);
    // Fallback to timestamp-based key
    return `CCP-${Date.now().toString().slice(-6)}`;
  }
}
