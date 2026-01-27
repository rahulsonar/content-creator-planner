/**
 * Script to add task dependencies for testing
 * Run with: npx tsx test-dependencies.ts
 */

import { prisma } from './lib/prisma';

async function addTestDependencies() {
  try {
    console.log('Fetching existing tasks...');
    
    // Get some existing tasks
    const tasks = await prisma.task.findMany({
      take: 5,
      orderBy: { id: 'asc' },
      select: { id: true, taskKey: true, title: true }
    });

    if (tasks.length < 2) {
      console.log('Not enough tasks in database. Please seed the database first.');
      return;
    }

    console.log(`Found ${tasks.length} tasks:`);
    tasks.forEach(task => {
      console.log(`  - [${task.taskKey}] ${task.title}`);
    });

    // Create a dependency: Task 2 depends on Task 1
    if (tasks[0] && tasks[1]) {
      console.log(`\nCreating dependency: [${tasks[1].taskKey}] depends on [${tasks[0].taskKey}]`);
      
      const dep1 = await prisma.taskDependency.upsert({
        where: {
          dependentId_blockingId: {
            dependentId: tasks[1].id,
            blockingId: tasks[0].id,
          }
        },
        create: {
          dependentId: tasks[1].id,
          blockingId: tasks[0].id,
        },
        update: {}
      });
      
      console.log('✓ Dependency created:', dep1.id);
    }

    // Create another dependency: Task 3 depends on Task 2
    if (tasks[1] && tasks[2]) {
      console.log(`\nCreating dependency: [${tasks[2].taskKey}] depends on [${tasks[1].taskKey}]`);
      
      const dep2 = await prisma.taskDependency.upsert({
        where: {
          dependentId_blockingId: {
            dependentId: tasks[2].id,
            blockingId: tasks[1].id,
          }
        },
        create: {
          dependentId: tasks[2].id,
          blockingId: tasks[1].id,
        },
        update: {}
      });
      
      console.log('✓ Dependency created:', dep2.id);
    }

    // Verify dependencies
    console.log('\nVerifying dependencies...');
    const taskWithDeps = await prisma.task.findUnique({
      where: { id: tasks[1]?.id },
      include: {
        blockedBy: {
          include: {
            blocking: {
              select: { id: true, taskKey: true, title: true, status: true }
            }
          }
        },
        blocks: {
          include: {
            dependent: {
              select: { id: true, taskKey: true, title: true, status: true }
            }
          }
        }
      }
    });

    console.log('\nTask:', taskWithDeps?.taskKey, taskWithDeps?.title);
    console.log('Blocked by:', taskWithDeps?.blockedBy.map(d => `[${d.blocking.taskKey}] ${d.blocking.title}`));
    console.log('Blocks:', taskWithDeps?.blocks.map(d => `[${d.dependent.taskKey}] ${d.dependent.title}`));
    
    console.log('\n✓ Test dependencies created successfully!');
    console.log('\nYou can now view these dependencies in the Kanban board by clicking on the tasks.');
    
  } catch (error) {
    console.error('Error:', error);
  }
}

addTestDependencies();
