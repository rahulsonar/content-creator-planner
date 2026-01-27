import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { ProjectStatus } from '@prisma/client';

// GET /api/projects - Get all projects for the authenticated user
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status') as ProjectStatus | null;
    const userId = request.headers.get('x-user-id'); // This would come from middleware

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify user exists (in case of stale token)
    const userExists = await prisma.user.findUnique({
      where: { id: userId },
      select: { id: true },
    });

    if (!userExists) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    const whereClause: any = {
      userId,
    };

    if (status) {
      whereClause.status = status;
    }

    const projects = await prisma.project.findMany({
      where: whereClause,
      select: {
        id: true,
        name: true,
        description: true,
        status: true,
        isDefault: true,
        startDate: true,
        endDate: true,
        dueDate: true,
        color: true,
        icon: true,
        tags: true,
        createdAt: true,
        updatedAt: true,
        tasks: {
          select: {
            id: true,
            title: true,
            status: true,
            priority: true,
          },
        },
        _count: {
          select: {
            tasks: true,
          },
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    // Create a default project if user has no projects
    if (projects.length === 0) {
      const defaultProject = await prisma.project.create({
        data: {
          name: 'Default',
          description: 'Your default project for organizing tasks',
          status: ProjectStatus.ACTIVE,
          isDefault: true,
          userId,
        },
        select: {
          id: true,
          name: true,
          description: true,
          status: true,
          isDefault: true,
          startDate: true,
          endDate: true,
          dueDate: true,
          color: true,
          icon: true,
          tags: true,
          createdAt: true,
          updatedAt: true,
          tasks: {
            select: {
              id: true,
              title: true,
              status: true,
              priority: true,
            },
          },
          _count: {
            select: {
              tasks: true,
            },
          },
        },
      });
      projects.unshift(defaultProject); // Add to beginning of array
    }

    return NextResponse.json(projects);
  } catch (error) {
    console.error('Error fetching projects:', error);
    return NextResponse.json({ error: 'Failed to fetch projects' }, { status: 500 });
  }
}

// POST /api/projects - Create a new project
export async function POST(request: Request) {
  try {
    const userId = request.headers.get('x-user-id'); // This would come from middleware

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { name, description, status, startDate, endDate, dueDate, color, icon, tags, isDefault } = body;

    if (!name) {
      return NextResponse.json({ error: 'Project name is required' }, { status: 400 });
    }

    if (isDefault === true) {
      await prisma.project.updateMany({
        where: { userId, isDefault: true },
        data: { isDefault: false },
      });
    }

    const project = await prisma.project.create({
      data: {
        name,
        description,
        status: status || ProjectStatus.ACTIVE,
        startDate: startDate ? new Date(startDate) : null,
        endDate: endDate ? new Date(endDate) : null,
        dueDate: dueDate ? new Date(dueDate) : null,
        color,
        icon,
        tags: tags || [],
        ...(isDefault !== undefined && { isDefault: Boolean(isDefault) }),
        userId,
      },
      include: {
        _count: {
          select: {
            tasks: true,
          },
        },
      },
    });

    return NextResponse.json(project, { status: 201 });
  } catch (error) {
    console.error('Error creating project:', error);
    return NextResponse.json({ error: 'Failed to create project' }, { status: 500 });
  }
}

// PATCH /api/projects - Update project (set default)
export async function PATCH(request: Request) {
  try {
    const userId = request.headers.get('x-user-id'); // This would come from middleware

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { projectId, isDefault } = body as { projectId?: string; isDefault?: boolean };

    if (!projectId) {
      return NextResponse.json({ error: 'Project ID is required' }, { status: 400 });
    }

    const project = await prisma.project.findFirst({
      where: { id: projectId, userId },
      select: { id: true },
    });

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 });
    }

    if (isDefault === true) {
      await prisma.$transaction([
        prisma.project.updateMany({
          where: { userId, isDefault: true },
          data: { isDefault: false },
        }),
        prisma.project.update({
          where: { id: projectId },
          data: { isDefault: true },
        }),
      ]);
    }

    const updatedProject = await prisma.project.findUnique({
      where: { id: projectId },
      include: {
        _count: { select: { tasks: true } },
        tasks: {
          select: {
            id: true,
            title: true,
            status: true,
            priority: true,
          },
        },
      },
    });

    return NextResponse.json(updatedProject);
  } catch (error) {
    console.error('Error updating project:', error);
    return NextResponse.json({ error: 'Failed to update project' }, { status: 500 });
  }
}
