import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { verifyToken } from '@/lib/auth/helpers';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    // Extract user info from token
    const token = request.cookies.get('auth-token')?.value;
    
    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const decoded = verifyToken(token);
    if (!decoded) {
      return NextResponse.json(
        { error: 'Invalid token' },
        { status: 401 }
      );
    }

    const { id: idParam } = await params;
    const id = parseInt(idParam, 10);
    
    if (isNaN(id)) {
      return NextResponse.json(
        { error: 'Invalid task ID' },
        { status: 400 }
      );
    }

    const task = await prisma.task.findUnique({
      where: {
        id,
      },
      include: {
        subtasks: {
          select: {
            id: true,
            taskKey: true,
            title: true,
            status: true,
            priority: true,
          },
        },
        notes: {
          orderBy: {
            createdAt: 'desc',
          },
        },
        project: {
          select: {
            id: true,
            name: true,
            color: true,
          },
        },
        blockedBy: {
          include: {
            blocking: {
              select: {
                id: true,
                taskKey: true,
                title: true,
              },
            },
          },
        },
        blocks: {
          include: {
            dependent: {
              select: {
                id: true,
                taskKey: true,
                title: true,
              },
            },
          },
        },
      },
    });

    if (!task) {
      return NextResponse.json(
        { error: 'Task not found' },
        { status: 404 }
      );
    }

    // Verify the task belongs to the current user
    if (task.userId !== decoded.userId) {
      return NextResponse.json(
        { error: 'Forbidden' },
        { status: 403 }
      );
    }

    return NextResponse.json(task);
  } catch (error) {
    console.error('Failed to fetch task:', error);
    return NextResponse.json(
      { error: 'Failed to fetch task' },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const token = request.cookies.get('auth-token')?.value;

    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const decoded = verifyToken(token);
    if (!decoded) {
      return NextResponse.json(
        { error: 'Invalid token' },
        { status: 401 }
      );
    }

    const { id: idParam } = await params;
    const id = parseInt(idParam, 10);
    
    if (isNaN(id)) {
      return NextResponse.json(
        { error: 'Invalid task ID' },
        { status: 400 }
      );
    }

    const task = await prisma.task.findUnique({
      where: { id },
      select: {
        id: true,
        userId: true,
        completedAt: true,
      },
    });

    if (!task) {
      return NextResponse.json(
        { error: 'Task not found' },
        { status: 404 }
      );
    }

    if (task.userId !== decoded.userId) {
      return NextResponse.json(
        { error: 'Forbidden' },
        { status: 403 }
      );
    }

    const body = await request.json();
    const {
      title,
      description,
      status,
      priority,
      startDate,
      endDate,
      dueDate,
      projectId,
      tags,
      estimatedHours,
      actualHours,
      assignedTo,
      dependencies,
    } = body;

    const updateData: Record<string, unknown> = {};

    if (typeof title === 'string') updateData.title = title;
    if (typeof description === 'string' || description === null) {
      updateData.description = description || null;
    }
    if (typeof status === 'string') {
      updateData.status = status;
      if (status === 'COMPLETED') {
        updateData.completedAt = task.completedAt ?? new Date();
      } else {
        updateData.completedAt = null;
      }
    }
    if (typeof priority === 'string') updateData.priority = priority;
    if (typeof projectId === 'number' || projectId === null) {
      updateData.projectId = projectId || null;
    }
    if (typeof assignedTo === 'string' || assignedTo === null) {
      updateData.assignedTo = assignedTo || null;
    }
    if (typeof estimatedHours === 'number') updateData.estimatedHours = estimatedHours;
    if (typeof actualHours === 'number') updateData.actualHours = actualHours;

    if (typeof startDate === 'string') {
      updateData.startDate = startDate ? new Date(startDate) : null;
    }
    if (typeof endDate === 'string') {
      updateData.endDate = endDate ? new Date(endDate) : null;
    }
    if (typeof dueDate === 'string') {
      updateData.dueDate = dueDate ? new Date(dueDate) : null;
    }
    if (Array.isArray(tags)) {
      updateData.tags = tags;
    }

    // Validate dependencies if provided
    if (dependencies !== undefined && Array.isArray(dependencies)) {
      for (const dep of dependencies) {
        if (!dep.taskId || !dep.type) {
          return NextResponse.json(
            { error: 'Each dependency must have taskId and type (blockedBy or blocks)' },
            { status: 400 }
          );
        }
        
        if (!['blockedBy', 'blocks'].includes(dep.type)) {
          return NextResponse.json(
            { error: 'Dependency type must be either "blockedBy" or "blocks"' },
            { status: 400 }
          );
        }

        // Verify the referenced task exists and belongs to the user
        const refTask = await prisma.task.findFirst({
          where: {
            id: parseInt(dep.taskId),
            userId: decoded.userId,
          },
        });

        if (!refTask) {
          return NextResponse.json(
            { error: `Task with ID ${dep.taskId} not found or not accessible` },
            { status: 400 }
          );
        }
      }

      // Delete existing dependencies for this task
      await prisma.taskDependency.deleteMany({
        where: {
          OR: [
            { dependentId: id },
            { blockingId: id },
          ],
        },
      });

      // Create new dependencies if provided
      if (dependencies.length > 0) {
        const dependencyData = dependencies.map((dep: any) => {
          if (dep.type === 'blockedBy') {
            // This task is blocked by another task
            return {
              dependentId: id,
              blockingId: parseInt(dep.taskId),
            };
          } else {
            // This task blocks another task
            return {
              dependentId: parseInt(dep.taskId),
              blockingId: id,
            };
          }
        });

        await prisma.taskDependency.createMany({
          data: dependencyData,
        });
      }
    }

    const updatedTask = await prisma.task.update({
      where: { id },
      data: updateData,
      include: {
        subtasks: {
          select: {
            id: true,
            title: true,
            status: true,
            priority: true,
          },
        },
        notes: {
          orderBy: {
            createdAt: 'desc',
          },
        },
        project: {
          select: {
            id: true,
            name: true,
            color: true,
          },
        },
        blockedBy: {
          include: {
            blocking: {
              select: {
                id: true,
                taskKey: true,
                title: true,
              },
            },
          },
        },
        blocks: {
          include: {
            dependent: {
              select: {
                id: true,
                taskKey: true,
                title: true,
              },
            },
          },
        },
      },
    });

    return NextResponse.json(updatedTask);
  } catch (error) {
    console.error('Failed to update task:', error);
    return NextResponse.json(
      { error: 'Failed to update task' },
      { status: 500 }
    );
  }
}
