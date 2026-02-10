import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { verifyToken } from '@/lib/auth/helpers';

export async function GET(request: NextRequest) {
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

    // Get projectId from query params if present
    const { searchParams } = new URL(request.url);
    const projectIdParam = searchParams.get('projectId');
    const projectId = projectIdParam ? parseInt(projectIdParam, 10) : undefined;

    const tasks = await prisma.task.findMany({
      where: {
        userId: decoded.userId,
        ...(projectId && { projectId }),
      },
      select: {
        id: true,
        taskKey: true,
        title: true,
        description: true,
        status: true,
        priority: true,
        project: {
          select: {
            id: true,
            name: true,
            color: true,
          },
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    return NextResponse.json(tasks);
  } catch (error) {
    console.error('Failed to fetch tasks:', error);
    return NextResponse.json(
      { error: 'Failed to fetch tasks' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
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

    // Verify user exists
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId },
    });

    if (!user) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    const body = await request.json();
    const { title, description, status, priority, dueDate, estimatedHours, projectId, tags, dependencies } = body;

    console.log('Creating task with data:', {
      title,
      projectId,
      status,
      priority,
      dependenciesCount: dependencies?.length || 0,
      userId: decoded.userId
    });

    if (!title) {
      return NextResponse.json(
        { error: 'Title is required' },
        { status: 400 }
      );
    }

    if (!projectId) {
      return NextResponse.json(
        { error: 'Project is required' },
        { status: 400 }
      );
    }

    // Validate dependencies if provided
    if (dependencies && Array.isArray(dependencies)) {
      for (const dep of dependencies) {
        if (!dep.taskId || !dep.type) {
          console.error('Invalid dependency:', dep);
          return NextResponse.json(
            { error: 'Each dependency must have taskId and type (blockedBy or blocks)' },
            { status: 400 }
          );
        }
        
        if (!['blockedBy', 'blocks'].includes(dep.type)) {
          console.error('Invalid dependency type:', dep.type);
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
          console.error('Referenced task not found:', dep.taskId, 'for user:', decoded.userId);
          return NextResponse.json(
            { error: `Task with ID ${dep.taskId} not found or not accessible` },
            { status: 400 }
          );
        }
      }
    }

    // Create task first to get the ID
    const task = await prisma.task.create({
      data: {
        taskKey: 'TEMP', // Temporary value
        title,
        description: description || null,
        status: status || 'TODO',
        priority: priority || 'MEDIUM',
        userId: decoded.userId,
        dueDate: dueDate ? new Date(dueDate) : null,
        estimatedHours: estimatedHours ? parseFloat(estimatedHours) : null,
        projectId: projectId,
        tags: Array.isArray(tags) ? tags : [],
      },
      include: {
        project: {
          select: {
            id: true,
            name: true,
            color: true,
          },
        },
      },
    });

    // Update with proper task key using the ID (CCP-001, CCP-042, CCP-123, etc.)
    const paddedId = String(task.id).padStart(3, '0');
    const taskKey = `CCP-${paddedId}`;
    
    await prisma.task.update({
      where: { id: task.id },
      data: { taskKey },
    });

    // Update the task object with the correct taskKey
    task.taskKey = taskKey;

    // Create task dependencies if provided
    if (dependencies && Array.isArray(dependencies) && dependencies.length > 0) {
      const dependencyData = dependencies.map((dep: any) => {
        if (dep.type === 'blockedBy') {
          // This task is blocked by another task
          return {
            dependentId: task.id,
            blockingId: parseInt(dep.taskId),
          };
        } else {
          // This task blocks another task
          return {
            dependentId: parseInt(dep.taskId),
            blockingId: task.id,
          };
        }
      });

      await prisma.taskDependency.createMany({
        data: dependencyData,
      });
    }

    // Fetch the complete task with dependencies
    const completeTask = await prisma.task.findUnique({
      where: { id: task.id },
      include: {
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

    return NextResponse.json(completeTask, { status: 201 });
  } catch (error) {
    console.error('Failed to create task:', error);
    return NextResponse.json(
      { error: 'Failed to create task' },
      { status: 500 }
    );
  }
}
