import { prisma } from '../lib/prisma';
import { TaskStatus, Priority } from '@prisma/client';
import bcrypt from 'bcrypt';

async function main() {
  console.log('🌱 Starting seed...');

  // Clear existing data
  await prisma.task.deleteMany({});
  await prisma.user.deleteMany({});
  
  // Reset auto-increment counters
  await prisma.$executeRawUnsafe('TRUNCATE TABLE "Task" RESTART IDENTITY CASCADE;');
  await prisma.$executeRawUnsafe('TRUNCATE TABLE "User" RESTART IDENTITY CASCADE;');
  
  console.log('✨ Cleared existing data');

  // Create default user with hashed password
  const hashedPassword = await bcrypt.hash('Admin123!', 12);
  const defaultUser = await prisma.user.create({
    data: {
      email: 'admin@example.com',
      password: hashedPassword,
      name: 'Admin User',
    },
  });
  console.log('👤 Created default user:', defaultUser.email);

  // Create YouTube content creator tasks
  const tasks = [
    // Video Production Tasks
    {
      title: 'Plan Q1 2026 Content Calendar',
      description: 'Create detailed content calendar for first quarter including trending topics, SEO keywords, and upload schedule',
      status: TaskStatus.IN_PROGRESS,
      priority: Priority.HIGH,
      startDate: new Date('2026-01-05'),
      dueDate: new Date('2026-01-15'),
      tags: ['planning', 'content-strategy', 'Q1'],
      estimatedHours: 8,
      actualHours: 3.5,
    },
    {
      title: 'Film "Top 10 AI Tools for Creators" Video',
      description: 'Research, script, and film comprehensive review of AI tools. Include demos and real-world examples.',
      status: TaskStatus.TODO,
      priority: Priority.HIGH,
      startDate: new Date('2026-01-10'),
      dueDate: new Date('2026-01-12'),
      tags: ['video-production', 'AI', 'tutorial'],
      estimatedHours: 12,
    },
    {
      title: 'Edit Weekly Vlog',
      description: 'Edit last week\'s vlog footage. Add music, transitions, and color grading. Target: 15-minute runtime.',
      status: TaskStatus.IN_PROGRESS,
      priority: Priority.URGENT,
      startDate: new Date('2026-01-06'),
      dueDate: new Date('2026-01-08'),
      tags: ['editing', 'vlog', 'weekly-content'],
      estimatedHours: 6,
      actualHours: 2,
    },
    {
      title: 'Create Thumbnails for 3 Upcoming Videos',
      description: 'Design eye-catching thumbnails for: AI Tools video, Weekly Vlog, and Gear Review. A/B test variations.',
      status: TaskStatus.TODO,
      priority: Priority.MEDIUM,
      dueDate: new Date('2026-01-11'),
      tags: ['design', 'thumbnails', 'branding'],
      estimatedHours: 4,
    },
    {
      title: 'Write Script: "My YouTube Journey - 1 Year Later"',
      description: 'Write emotional and data-driven script about channel growth. Include stats, lessons learned, and future plans.',
      status: TaskStatus.COMPLETED,
      priority: Priority.MEDIUM,
      startDate: new Date('2026-01-01'),
      dueDate: new Date('2026-01-05'),
      completedAt: new Date('2026-01-04'),
      tags: ['scriptwriting', 'milestone', 'storytelling'],
      estimatedHours: 5,
      actualHours: 6,
    },

    // Channel Growth & Marketing
    {
      title: 'Optimize Last 5 Videos for SEO',
      description: 'Update titles, descriptions, and tags based on YouTube Analytics. Add chapters and improved keywords.',
      status: TaskStatus.TODO,
      priority: Priority.MEDIUM,
      dueDate: new Date('2026-01-20'),
      tags: ['SEO', 'optimization', 'analytics'],
      estimatedHours: 3,
    },
    {
      title: 'Research Trending Topics in Creator Niche',
      description: 'Use Google Trends, VidIQ, and TubeBuddy to identify trending topics. Document top 20 ideas for next month.',
      status: TaskStatus.IN_PROGRESS,
      priority: Priority.HIGH,
      startDate: new Date('2026-01-07'),
      dueDate: new Date('2026-01-09'),
      tags: ['research', 'trends', 'content-ideas'],
      estimatedHours: 4,
      actualHours: 1.5,
    },
    {
      title: 'Collab Outreach: Email 10 Creators',
      description: 'Reach out to creators with similar audience size for potential collaborations. Personalize each email.',
      status: TaskStatus.TODO,
      priority: Priority.LOW,
      dueDate: new Date('2026-01-25'),
      tags: ['networking', 'collaboration', 'outreach'],
      estimatedHours: 2,
    },
    {
      title: 'Create Instagram Reels from Latest Video',
      description: 'Repurpose best moments from latest video into 3-5 Instagram Reels. Optimize for 9:16 format.',
      status: TaskStatus.TODO,
      priority: Priority.MEDIUM,
      dueDate: new Date('2026-01-14'),
      tags: ['social-media', 'repurposing', 'instagram'],
      estimatedHours: 2,
    },

    // Equipment & Technical
    {
      title: 'Review New Sony Camera for Channel',
      description: 'Test Sony A7 IV for video quality. Create detailed review video with sample footage and comparisons.',
      status: TaskStatus.BLOCKED,
      priority: Priority.MEDIUM,
      dueDate: new Date('2026-01-30'),
      tags: ['gear-review', 'camera', 'sponsored'],
      estimatedHours: 10,
    },
    {
      title: 'Upgrade Studio Lighting Setup',
      description: 'Install new key light and backlight. Test different configurations and document settings.',
      status: TaskStatus.TODO,
      priority: Priority.LOW,
      dueDate: new Date('2026-01-31'),
      tags: ['studio', 'lighting', 'production-quality'],
      estimatedHours: 5,
    },
    {
      title: 'Backup All Video Projects to Cloud',
      description: 'Upload December 2025 projects to Google Drive and external SSD. Verify integrity of backups.',
      status: TaskStatus.COMPLETED,
      priority: Priority.HIGH,
      startDate: new Date('2026-01-03'),
      dueDate: new Date('2026-01-05'),
      completedAt: new Date('2026-01-05'),
      tags: ['backup', 'data-management', 'maintenance'],
      estimatedHours: 3,
      actualHours: 4,
    },

    // Community & Engagement
    {
      title: 'Respond to Comments on Last 3 Videos',
      description: 'Engage with community by responding to comments. Prioritize questions and thoughtful feedback.',
      status: TaskStatus.IN_PROGRESS,
      priority: Priority.MEDIUM,
      startDate: new Date('2026-01-07'),
      dueDate: new Date('2026-01-08'),
      tags: ['community', 'engagement', 'comments'],
      estimatedHours: 2,
      actualHours: 0.5,
    },
    {
      title: 'Plan Live Stream: Q&A Session',
      description: 'Organize live Q&A stream. Create announcement, prepare topics, and test streaming setup.',
      status: TaskStatus.TODO,
      priority: Priority.MEDIUM,
      dueDate: new Date('2026-01-18'),
      tags: ['livestream', 'community', 'QA'],
      estimatedHours: 6,
    },
    {
      title: 'Update Channel Banner & About Section',
      description: 'Refresh channel art to reflect new branding. Update about section with recent achievements and contact info.',
      status: TaskStatus.TODO,
      priority: Priority.LOW,
      dueDate: new Date('2026-02-01'),
      tags: ['branding', 'channel-optimization', 'design'],
      estimatedHours: 2,
    },

    // Business & Admin
    {
      title: 'Review December Analytics Report',
      description: 'Analyze December performance: views, watch time, CTR, subscriber growth. Identify what worked and what didn\'t.',
      status: TaskStatus.COMPLETED,
      priority: Priority.HIGH,
      startDate: new Date('2026-01-01'),
      dueDate: new Date('2026-01-03'),
      completedAt: new Date('2026-01-02'),
      tags: ['analytics', 'reporting', 'data-analysis'],
      estimatedHours: 3,
      actualHours: 3,
    },
    {
      title: 'Negotiate Brand Deal with TechCorp',
      description: 'Review contract terms for sponsored content. Negotiate rates and deliverables. Ensure FTC compliance.',
      status: TaskStatus.REVIEW,
      priority: Priority.HIGH,
      dueDate: new Date('2026-01-12'),
      tags: ['sponsorship', 'business', 'legal'],
      estimatedHours: 4,
    },
    {
      title: 'Organize Receipts for Tax Season',
      description: 'Collect and categorize all business expenses from 2025. Prepare documents for accountant.',
      status: TaskStatus.IN_PROGRESS,
      priority: Priority.HIGH,
      startDate: new Date('2026-01-05'),
      dueDate: new Date('2026-01-31'),
      tags: ['taxes', 'admin', 'finance'],
      estimatedHours: 8,
      actualHours: 2,
    },
  ];

  // Create tasks with task keys
  for (let i = 0; i < tasks.length; i++) {
    const task = tasks[i];
    
    const createdTask = await prisma.task.create({
      data: {
        ...task,
        taskKey: 'TEMP',
        userId: defaultUser.id,
      },
    });
    
    // Update with correct taskKey based on actual ID
    await prisma.task.update({
      where: { id: createdTask.id },
      data: { taskKey: `CCP-${String(createdTask.id).padStart(3, '0')}` },
    });
  }

  console.log(`✅ Created ${tasks.length} YouTube content creator tasks`);

  // Create example with subtasks
  const mainTask = await prisma.task.create({
    data: {
      taskKey: 'TEMP',
      title: 'Complete "Ultimate Productivity Setup" Video Project',
      description: 'End-to-end production of comprehensive productivity video',
      status: TaskStatus.IN_PROGRESS,
      priority: Priority.URGENT,
      startDate: new Date('2026-01-08'),
      dueDate: new Date('2026-01-15'),
      tags: ['video-project', 'productivity', 'tutorial'],
      estimatedHours: 30,
      actualHours: 12,
      userId: defaultUser.id,
    },
  });
  
  // Update with correct taskKey based on actual ID
  await prisma.task.update({
    where: { id: mainTask.id },
    data: { taskKey: `CCP-${String(mainTask.id).padStart(3, '0')}` },
  });

  const subtasks = [
    {
      title: 'Research productivity tools and workflows',
      description: 'Compile list of 15-20 productivity tools and techniques',
      status: TaskStatus.COMPLETED,
      priority: Priority.HIGH,
      parentId: mainTask.id,
      completedAt: new Date('2026-01-08'),
      tags: ['research', 'subtask'],
      estimatedHours: 4,
      actualHours: 5,
    },
    {
      title: 'Write and revise script',
      description: 'Draft script with intro, main content, and call-to-action',
      status: TaskStatus.COMPLETED,
      priority: Priority.HIGH,
      parentId: mainTask.id,
      completedAt: new Date('2026-01-09'),
      tags: ['scriptwriting', 'subtask'],
      estimatedHours: 6,
      actualHours: 7,
    },
    {
      title: 'Film A-roll and B-roll footage',
      description: 'Record talking head segments and screen recordings',
      status: TaskStatus.IN_PROGRESS,
      priority: Priority.HIGH,
      parentId: mainTask.id,
      tags: ['filming', 'subtask'],
      estimatedHours: 8,
    },
    {
      title: 'Edit video in Premiere Pro',
      description: 'Complete edit with transitions, effects, and color grading',
      status: TaskStatus.TODO,
      priority: Priority.HIGH,
      parentId: mainTask.id,
      tags: ['editing', 'subtask'],
      estimatedHours: 10,
    },
    {
      title: 'Create custom thumbnail',
      description: 'Design thumbnail with attention-grabbing text and imagery',
      status: TaskStatus.TODO,
      priority: Priority.MEDIUM,
      parentId: mainTask.id,
      tags: ['design', 'subtask'],
      estimatedHours: 2,
    },
  ];

  for (let i = 0; i < subtasks.length; i++) {
    const subtask = subtasks[i];
    
    const createdSubtask = await prisma.task.create({
      data: {
        ...subtask,
        userId: defaultUser.id,
        taskKey: 'TEMP',
      },
    });
    
    // Update with correct taskKey based on actual ID
    await prisma.task.update({
      where: { id: createdSubtask.id },
      data: { taskKey: `CCP-${String(createdSubtask.id).padStart(3, '0')}` },
    });
  }

  console.log(`✅ Created 1 parent task with ${subtasks.length} subtasks`);
  console.log('🎉 Seed completed successfully!');
}

main()
  .catch((e) => {
    console.error('❌ Seed failed:');
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
