'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { TaskStatus, Priority } from '@prisma/client';

interface TaskNote {
  id: string;
  content: string;
  createdBy?: string | null;
  createdAt: string;
  updatedAt: string;
}

interface TaskDependency {
  id: string;
  dependentId: number;
  blockingId: number;
  dependencyType?: string;
  blocking?: {
    id: number;
    taskKey?: string;
    title: string;
    status?: TaskStatus;
  };
  dependent?: {
    id: number;
    taskKey?: string;
    title: string;
    status?: TaskStatus;
  };
}

interface Task {
  id: string;
  taskKey?: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority?: Priority;
  startDate?: string | null;
  endDate?: string | null;
  dueDate?: string | null;
  completedAt?: string | null;
  tags?: string[];
  assignedTo?: string | null;
  estimatedHours?: number | null;
  actualHours?: number | null;
  parentId?: string | null;
  subtasks?: Task[];
  notes?: TaskNote[];
  project?: { id: string; name: string; color?: string | null } | null;
  blockedBy?: TaskDependency[];
  blocks?: TaskDependency[];
  createdAt?: string;
  updatedAt?: string;
}

interface Project {
  id: string;
  name: string;
  description?: string | null;
  color?: string | null;
  status?: string;
}

export default function TaskModalPage({ params }: { params: Promise<{ taskId: string }> }) {
  const router = useRouter();
  const unwrappedParams = React.use(params);
  const [task, setTask] = useState<Task | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch task details
        const taskRes = await fetch(`/api/tasks/${unwrappedParams.taskId}`);
        if (taskRes.ok) {
          const taskData = await taskRes.json();
          setTask(taskData);
        }

        // Fetch projects and all tasks for dependencies
        const [projectsRes, tasksRes] = await Promise.all([
          fetch('/api/projects'),
          fetch('/api/tasks')
        ]);

        if (projectsRes.ok) {
          const projectsData = await projectsRes.json();
          setProjects(projectsData);
        }

        if (tasksRes.ok) {
          const tasksData = await tasksRes.json();
          setAllTasks(tasksData);
        }
      } catch (error) {
        console.error('Failed to fetch task data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [unwrappedParams.taskId]);

  const handleClose = () => {
    router.back();
  };

  const handleSave = async (taskId: string, updates: Partial<Task>) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        const updatedTask = await response.json();
        setTask(updatedTask);
      }
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 shadow-xl">
          <p className="text-gray-700">Loading task details...</p>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={handleClose}>
        <div className="bg-white rounded-lg p-6 shadow-xl">
          <p className="text-gray-700">Task not found</p>
          <button onClick={handleClose} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-indigo-900 p-8">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-2xl">
        <TaskDetailView 
          task={task}
          projects={projects}
          allTasks={allTasks}
          onClose={handleClose}
          onSave={handleSave}
        />
      </div>
    </div>
  );
}

// Reuse the TaskModal component logic but as a full page view
function TaskDetailView({
  task,
  projects,
  allTasks,
  onClose,
  onSave,
}: {
  task: Task;
  projects: Project[];
  allTasks: Task[];
  onClose: () => void;
  onSave: (taskId: string, updates: Partial<Task>) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editFormData, setEditFormData] = useState({
    title: task.title || '',
    description: task.description || '',
    status: task.status || 'TODO',
    priority: task.priority || 'MEDIUM',
    projectId: task.project?.id ? String(task.project.id) : '',
    startDate: '',
    endDate: '',
    dueDate: '',
    tags: (task.tags || []).join(', '),
    dependencies: [] as Array<{ taskId: string; type: 'blockedBy' | 'blocks'; dependencyType?: string }>,
  });

  useEffect(() => {
    const toDateInputValue = (value?: string | null) => {
      if (!value) return '';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return '';
      return date.toISOString().slice(0, 10);
    };

    const deps: Array<{ taskId: string; type: 'blockedBy' | 'blocks'; dependencyType?: string }> = [];
    
    if ((task as any).blockedBy && Array.isArray((task as any).blockedBy)) {
      (task as any).blockedBy.forEach((dep: any) => {
        deps.push({
          taskId: String(dep.blockingId || dep.blocking?.id || ''),
          type: 'blockedBy',
          dependencyType: dep.dependencyType,
        });
      });
    }
    
    if ((task as any).blocks && Array.isArray((task as any).blocks)) {
      (task as any).blocks.forEach((dep: any) => {
        deps.push({
          taskId: String(dep.dependentId || dep.dependent?.id || ''),
          type: 'blocks',
          dependencyType: dep.dependencyType,
        });
      });
    }

    setEditFormData({
      title: task.title || '',
      description: task.description || '',
      status: task.status || 'TODO',
      priority: task.priority || 'MEDIUM',
      projectId: task.project?.id ? String(task.project.id) : '',
      startDate: toDateInputValue(task.startDate),
      endDate: toDateInputValue(task.endDate),
      dueDate: toDateInputValue(task.dueDate),
      tags: (task.tags || []).join(', '),
      dependencies: deps,
    });
  }, [task]);

  const formatDate = (date: string | null | undefined) => {
    if (!date) return 'Not set';
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const priorityColors: Record<Priority, string> = {
    LOW: 'bg-gray-100 text-gray-700',
    MEDIUM: 'bg-blue-100 text-blue-700',
    HIGH: 'bg-orange-100 text-orange-700',
    URGENT: 'bg-red-100 text-red-700',
  };

  const statusColors: Record<TaskStatus, string> = {
    TODO: 'bg-gray-100 text-gray-700',
    IN_PROGRESS: 'bg-blue-100 text-blue-700',
    REVIEW: 'bg-purple-100 text-purple-700',
    BLOCKED: 'bg-red-100 text-red-700',
    COMPLETED: 'bg-green-100 text-green-700',
    CANCELLED: 'bg-gray-100 text-gray-700',
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);

    try {
      const parsedTags = editFormData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean);

      await onSave(task.id, {
        title: editFormData.title,
        description: editFormData.description,
        status: editFormData.status as TaskStatus,
        priority: editFormData.priority as Priority,
        projectId: editFormData.projectId ? parseInt(editFormData.projectId, 10) : null,
        startDate: editFormData.startDate || null,
        endDate: editFormData.endDate || null,
        dueDate: editFormData.dueDate || null,
        tags: parsedTags,
        dependencies: editFormData.dependencies,
      } as any);

      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save task:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-lg">
        <h2 className="text-2xl font-bold text-gray-900">Task Details</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsEditing((prev) => !prev)}
            className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
          >
            {isEditing ? 'Cancel Edit' : 'Edit'}
          </button>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold w-8 h-8 flex items-center justify-center"
          >
            ×
          </button>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {isEditing ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Title</label>
              <input
                type="text"
                value={editFormData.title}
                onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Description</label>
              <textarea
                value={editFormData.description}
                onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 min-h-[100px]"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Status</label>
                <select
                  value={editFormData.status}
                  onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value as TaskStatus })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="TODO">To Do</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="REVIEW">Review</option>
                  <option value="BLOCKED">Blocked</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Priority</label>
                <select
                  value={editFormData.priority}
                  onChange={(e) => setEditFormData({ ...editFormData, priority: e.target.value as Priority })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Tags</label>
              <input
                type="text"
                value={editFormData.tags}
                onChange={(e) => setEditFormData({ ...editFormData, tags: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                placeholder="Comma-separated tags"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Dependencies
              </label>
              <div className="space-y-2">
                {editFormData.dependencies.map((dep, index) => (
                  <div key={index} className="flex gap-2 items-start">
                    <select
                      value={dep.type}
                      onChange={(e) => {
                        const newDeps = [...editFormData.dependencies];
                        newDeps[index].type = e.target.value as 'blockedBy' | 'blocks';
                        setEditFormData({ ...editFormData, dependencies: newDeps });
                      }}
                      className="px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="blockedBy">Blocked By</option>
                      <option value="blocks">Blocks</option>
                    </select>
                    <select
                      value={dep.taskId}
                      onChange={(e) => {
                        const newDeps = [...editFormData.dependencies];
                        newDeps[index].taskId = e.target.value;
                        setEditFormData({ ...editFormData, dependencies: newDeps });
                      }}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="">Select task...</option>
                      {allTasks.filter(t => t.id !== task.id).map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.taskKey ? `[${t.taskKey}] ` : ''}{t.title}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => {
                        const newDeps = editFormData.dependencies.filter((_, i) => i !== index);
                        setEditFormData({ ...editFormData, dependencies: newDeps });
                      }}
                      className="px-3 py-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                      title="Remove dependency"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => {
                    setEditFormData({
                      ...editFormData,
                      dependencies: [...editFormData.dependencies, { taskId: '', type: 'blockedBy' }],
                    });
                  }}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Dependency
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Define task dependencies to manage workflow order
              </p>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={isSaving}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-6">
            <div>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">
                    {task.taskKey && <span className="text-blue-600 mr-2">[{task.taskKey}]</span>}
                    {task.title}
                  </h3>
                  {task.project && (
                    <span
                      className="inline-flex items-center text-xs px-2 py-1 rounded-full font-medium mt-2"
                      style={{
                        backgroundColor: task.project.color ? `${task.project.color}20` : '#E5E7EB',
                        color: task.project.color || '#374151'
                      }}
                    >
                      {task.project.name}
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {task.priority && (
                    <span className={`text-xs px-3 py-1 rounded-full ${priorityColors[task.priority]}`}>
                      {task.priority}
                    </span>
                  )}
                  <span className={`text-xs px-3 py-1 rounded-full ${statusColors[task.status]}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <p className="text-gray-700 whitespace-pre-wrap">{task.description || 'No description provided'}</p>
            </div>

            {task.tags && task.tags.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Tags</h4>
                <div className="flex flex-wrap gap-2">
                  {task.tags.map((tag) => (
                    <span key={tag} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div>
                <p className="text-sm text-gray-600">Due Date</p>
                <p className="font-medium text-gray-900">{formatDate(task.dueDate)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Completed At</p>
                <p className="font-medium text-gray-900">{formatDate(task.completedAt)}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
