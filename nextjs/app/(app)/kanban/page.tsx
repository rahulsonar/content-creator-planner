'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { TaskStatus, Priority } from '@prisma/client';

interface TaskNote {
  id: string;
  content: string;
  createdBy?: string | null;
  createdAt: string;
  updatedAt: string;
}

interface Project {
  id: string;
  name: string;
  description?: string | null;
  color?: string | null;
  status?: string;
}

interface TaskDependency {
  id: string;
  dependentId: number;
  blockingId: number;
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

interface Column {
  id: TaskStatus;
  title: string;
  tasks: Task[];
}

const statusColumns: { id: TaskStatus; title: string }[] = [
  { id: 'TODO', title: 'To Do' },
  { id: 'IN_PROGRESS', title: 'In Progress' },
  { id: 'REVIEW', title: 'Review' },
  { id: 'BLOCKED', title: 'Blocked' },
  { id: 'COMPLETED', title: 'Completed' },
  { id: 'CANCELLED', title: 'Cancelled' },
];

function TaskCard({ task, onTaskClick }: { task: Task; onTaskClick: (taskId: string) => void }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const priorityColors: Record<Priority, string> = {
    LOW: 'bg-gray-100 text-gray-700',
    MEDIUM: 'bg-blue-100 text-blue-700',
    HIGH: 'bg-orange-100 text-orange-700',
    URGENT: 'bg-red-100 text-red-700',
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
    >
      <div
        {...listeners}
        className="cursor-grab active:cursor-grabbing"
      >
        {task.project && (
          <div className="mb-2">
            <span 
              className="inline-flex items-center text-xs px-2 py-1 rounded-full font-medium"
              style={{
                backgroundColor: task.project.color ? `${task.project.color}20` : '#E5E7EB',
                color: task.project.color || '#374151'
              }}
            >
              {task.project.name}
            </span>
          </div>
        )}
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-gray-900 flex-1">
            {task.taskKey && <span className="text-blue-600 mr-2">[{task.taskKey}]</span>}
            {task.title}
          </h3>
          {task.priority && (
            <span className={`text-xs px-2 py-1 rounded ${priorityColors[task.priority]}`}>
              {task.priority}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-600 line-clamp-2">{task.description || 'No description'}</p>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onTaskClick(task.id);
        }}
        className="mt-3 text-sm text-blue-600 hover:text-blue-800 font-medium"
      >
        View Details →
      </button>
    </div>
  );
}

function TaskModal({
  task,
  projects,
  allTasks,
  onClose,
  onSave,
}: {
  task: Task | null;
  projects: Project[];
  allTasks: Task[];
  onClose: () => void;
  onSave: (taskId: string, updates: Partial<Task>) => Promise<void>;
}) {
  if (!task) return null;

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editFormData, setEditFormData] = useState({
    title: task.title || '',
    description: task.description || '',
    status: task.status || 'TODO',
    priority: task.priority || 'MEDIUM',
    projectId: task.project?.id || '',
    startDate: '',
    endDate: '',
    dueDate: '',
    tags: (task.tags || []).join(', '),
    dependencies: [] as Array<{ taskId: string; type: 'blockedBy' | 'blocks' }>,
  });

  useEffect(() => {
    const toDateInputValue = (value?: string | null) => {
      if (!value) return '';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return '';
      return date.toISOString().slice(0, 10);
    };

    // Convert task dependencies to form format
    const deps: Array<{ taskId: string; type: 'blockedBy' | 'blocks' }> = [];
    
    if ((task as any).blockedBy && Array.isArray((task as any).blockedBy)) {
      (task as any).blockedBy.forEach((dep: any) => {
        deps.push({
          taskId: String(dep.blockingId || dep.blocking?.id || ''),
          type: 'blockedBy',
        });
      });
    }
    
    if ((task as any).blocks && Array.isArray((task as any).blocks)) {
      (task as any).blocks.forEach((dep: any) => {
        deps.push({
          taskId: String(dep.dependentId || dep.dependent?.id || ''),
          type: 'blockedBy',
        });
      });
    }

    setEditFormData({
      title: task.title || '',
      description: task.description || '',
      status: task.status || 'TODO',
      priority: task.priority || 'MEDIUM',
      projectId: task.project?.id || '',
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
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
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setIsSaving(true);
                try {
                  const parsedTags = editFormData.tags
                    .split(',')
                    .map((tag) => tag.trim())
                    .filter(Boolean);

                  await onSave(task.id, {
                    title: editFormData.title,
                    description: editFormData.description || null,
                    status: editFormData.status as TaskStatus,
                    priority: editFormData.priority as Priority,
                    project: editFormData.projectId ? { id: editFormData.projectId, name: '', color: null } : null,
                    startDate: editFormData.startDate || null,
                    endDate: editFormData.endDate || null,
                    dueDate: editFormData.dueDate || null,
                    tags: parsedTags,
                    dependencies: editFormData.dependencies,
                  } as any);

                  setIsEditing(false);
                } finally {
                  setIsSaving(false);
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Title</label>
                <input
                  type="text"
                  value={editFormData.title}
                  onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                  className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none placeholder:text-gray-400"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Description</label>
                <textarea
                  value={editFormData.description}
                  onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                  className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none min-h-[100px] placeholder:text-gray-400"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Project</label>
                <select
                  value={editFormData.projectId}
                  onChange={(e) => setEditFormData({ ...editFormData, projectId: e.target.value })}
                  className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                >
                  <option value="">No project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Status</label>
                  <select
                    value={editFormData.status}
                    onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value as TaskStatus })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
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
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="URGENT">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Start Date</label>
                  <input
                    type="date"
                    value={editFormData.startDate}
                    onChange={(e) => setEditFormData({ ...editFormData, startDate: e.target.value })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">End Date</label>
                  <input
                    type="date"
                    value={editFormData.endDate}
                    onChange={(e) => setEditFormData({ ...editFormData, endDate: e.target.value })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Due Date</label>
                  <input
                    type="date"
                    value={editFormData.dueDate}
                    onChange={(e) => setEditFormData({ ...editFormData, dueDate: e.target.value })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
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
                        className="px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
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
                        className="flex-1 px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
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

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Labels (tags)</label>
                <input
                  type="text"
                  value={editFormData.tags}
                  onChange={(e) => setEditFormData({ ...editFormData, tags: e.target.value })}
                  className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  placeholder="e.g. social, video, q1"
                />
                <p className="mt-1 text-xs text-gray-500">Comma-separated</p>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  disabled={isSaving}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <>
          <div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {task.taskKey && <span className="text-blue-600 mr-2">[{task.taskKey}]</span>}
              {task.title}
            </h3>
            <div className="flex gap-2">
              {task.status && (
                <span className={`text-xs px-2 py-1 rounded ${statusColors[task.status]}`}>
                  {task.status.replace('_', ' ')}
                </span>
              )}
              {task.priority && (
                <span className={`text-xs px-2 py-1 rounded ${priorityColors[task.priority]}`}>
                  {task.priority}
                </span>
              )}
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Project</h4>
            {task.project ? (
              <div className="flex items-center gap-2 text-gray-600">
                {task.project.color && (
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: task.project.color }}
                    aria-label={`${task.project.name} color`}
                  />
                )}
                <span>{task.project.name}</span>
              </div>
            ) : (
              <p className="text-gray-600">No project</p>
            )}
          </div>

          {task.description && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Description</h4>
              <p className="text-gray-600 whitespace-pre-wrap">{task.description}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="font-semibold text-gray-700 mb-1">Start Date</h4>
              <p className="text-gray-600">{formatDate(task.startDate)}</p>
            </div>
            <div>
              <h4 className="font-semibold text-gray-700 mb-1">End Date</h4>
              <p className="text-gray-600">{formatDate(task.endDate)}</p>
            </div>
            <div>
              <h4 className="font-semibold text-gray-700 mb-1">Due Date</h4>
              <p className="text-gray-600">{formatDate(task.dueDate)}</p>
            </div>
            {task.completedAt && (
              <div>
                <h4 className="font-semibold text-gray-700 mb-1">Completed At</h4>
                <p className="text-gray-600">{formatDate(task.completedAt)}</p>
              </div>
            )}
          </div>

          {task.assignedTo && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-1">Assigned To</h4>
              <p className="text-gray-600">{task.assignedTo}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {task.estimatedHours !== null && task.estimatedHours !== undefined && (
              <div>
                <h4 className="font-semibold text-gray-700 mb-1">Estimated Hours</h4>
                <p className="text-gray-600">{task.estimatedHours}h</p>
              </div>
            )}
            {task.actualHours !== null && task.actualHours !== undefined && (
              <div>
                <h4 className="font-semibold text-gray-700 mb-1">Actual Hours</h4>
                <p className="text-gray-600">{task.actualHours}h</p>
              </div>
            )}
          </div>

          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Tags</h4>
            {task.tags && task.tags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {task.tags.map((tag, index) => (
                  <span key={index} className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full text-sm">
                    {tag}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-600">No tags</p>
            )}
          </div>

          {task.subtasks && task.subtasks.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Subtasks ({task.subtasks.length})</h4>
              <ul className="space-y-2">
                {task.subtasks.map((subtask) => (
                  <li key={subtask.id} className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${subtask.status === 'COMPLETED' ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                    <span className={subtask.status === 'COMPLETED' ? 'line-through text-gray-500' : 'text-gray-700'}>
                      {subtask.taskKey && <span className="text-blue-600 mr-1">[{subtask.taskKey}]</span>}
                      {subtask.title}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Task Dependencies */}
          {((task.blockedBy && task.blockedBy.length > 0) || (task.blocks && task.blocks.length > 0)) && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Dependencies</h4>
              <div className="space-y-3">
                {task.blockedBy && task.blockedBy.length > 0 && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-2">
                      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                      Blocked By ({task.blockedBy.length})
                    </h5>
                    <ul className="space-y-2 ml-6">
                      {task.blockedBy.map((dep) => {
                        const blockingTask = dep.blocking;
                        if (!blockingTask) return null;
                        const isCompleted = blockingTask.status === 'COMPLETED';
                        return (
                          <li key={dep.id} className="flex items-start gap-2 text-sm">
                            <span className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${isCompleted ? 'bg-green-500' : 'bg-orange-400'}`}></span>
                            <div className="flex-1">
                              <span className={isCompleted ? 'text-gray-500' : 'text-gray-700'}>
                                {blockingTask.taskKey && <span className="text-blue-600 mr-1 font-medium">[{blockingTask.taskKey}]</span>}
                                {blockingTask.title}
                              </span>
                              {blockingTask.status && (
                                <span className={`ml-2 text-xs px-2 py-0.5 rounded ${
                                  blockingTask.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                                  blockingTask.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                                  blockingTask.status === 'BLOCKED' ? 'bg-red-100 text-red-700' :
                                  'bg-gray-100 text-gray-700'
                                }`}>
                                  {blockingTask.status.replace('_', ' ')}
                                </span>
                              )}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {task.blocks && task.blocks.length > 0 && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-2">
                      <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                      </svg>
                      Blocks ({task.blocks.length})
                    </h5>
                    <ul className="space-y-2 ml-6">
                      {task.blocks.map((dep) => {
                        const dependentTask = dep.dependent;
                        if (!dependentTask) return null;
                        const isCompleted = task.status === 'COMPLETED';
                        return (
                          <li key={dep.id} className="flex items-start gap-2 text-sm">
                            <span className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${isCompleted ? 'bg-green-500' : 'bg-purple-400'}`}></span>
                            <div className="flex-1">
                              <span className="text-gray-700">
                                {dependentTask.taskKey && <span className="text-blue-600 mr-1 font-medium">[{dependentTask.taskKey}]</span>}
                                {dependentTask.title}
                              </span>
                              {dependentTask.status && (
                                <span className={`ml-2 text-xs px-2 py-0.5 rounded ${
                                  dependentTask.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                                  dependentTask.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                                  dependentTask.status === 'BLOCKED' ? 'bg-red-100 text-red-700' :
                                  'bg-gray-100 text-gray-700'
                                }`}>
                                  {dependentTask.status.replace('_', ' ')}
                                </span>
                              )}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {task.notes && task.notes.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Notes ({task.notes.length})</h4>
              <div className="space-y-3">
                {task.notes.map((note) => (
                  <div key={note.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-gray-700 whitespace-pre-wrap mb-2">{note.content}</p>
                    <div className="text-xs text-gray-500 flex items-center gap-3">
                      {note.createdBy && <span>By: {note.createdBy}</span>}
                      <span>{new Date(note.createdAt).toLocaleString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(task.createdAt || task.updatedAt) && (
            <div className="border-t pt-4 text-xs text-gray-500 space-y-1">
              {task.createdAt && <p>Created: {formatDate(task.createdAt)}</p>}
              {task.updatedAt && <p>Last updated: {formatDate(task.updatedAt)}</p>}
            </div>
          )}
          </>
          )}
        </div>
      </div>
    </div>
  );
}

function KanbanColumn({
  column,
  tasks,
  onTaskClick,
}: {
  column: Column;
  tasks: Task[];
  onTaskClick: (taskId: string) => void;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 min-h-[500px] w-80">
      <h2 className="font-bold text-lg mb-4 text-gray-800">{column.title}</h2>
      <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onTaskClick={onTaskClick} />
          ))}
        </div>
      </SortableContext>
    </div>
  );
}

export default function KanbanPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = searchParams.get('projectId');
  
  const [columns, setColumns] = useState<Column[]>(
    statusColumns.map((col) => ({ ...col, tasks: [] }))
  );
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createFormData, setCreateFormData] = useState({
    title: '',
    description: '',
    status: 'TODO' as TaskStatus,
    priority: 'MEDIUM' as Priority,
    dueDate: '',
    estimatedHours: '',
    projectId: '',
    tags: '',
    dependencies: [] as Array<{ taskId: string; type: 'blockedBy' | 'blocks' }>,
  });
  const [isCreating, setIsCreating] = useState(false);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch tasks
        const url = projectId ? `/api/tasks?projectId=${projectId}` : '/api/tasks';
        const response = await fetch(url);
        const tasks: Task[] = await response.json();
        
        setAllTasks(tasks);
        
        const columnsWithTasks = statusColumns.map((col) => ({
          ...col,
          tasks: tasks.filter((task) => task.status === col.id),
        }));
        
        setColumns(columnsWithTasks);

        // Fetch projects
        const projectsResponse = await fetch('/api/projects');
        if (projectsResponse.ok) {
          const projectsData: Project[] = await projectsResponse.json();
          setProjects(projectsData);
          
          // Set current project if projectId is in query
          if (projectId) {
            const project = projectsData.find(p => p.id === projectId);
            setCurrentProject(project || null);
          } else {
            setCurrentProject(null);
          }
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [projectId]);

  // Filter tasks based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      // If no search query, show all tasks
      const columnsWithTasks = statusColumns.map((col) => ({
        ...col,
        tasks: allTasks.filter((task) => task.status === col.id),
      }));
      setColumns(columnsWithTasks);
    } else {
      // Filter tasks by taskKey first, then ID, title, or description
      const query = searchQuery.toLowerCase();
      const filteredTasks = allTasks.filter((task) => {
        // Prioritize taskKey match (e.g., "PROJ-001")
        const matchesTaskKey = task.taskKey?.toLowerCase().includes(query) || false;
        const matchesId = task.id.toString().includes(query);
        const matchesTitle = task.title.toLowerCase().includes(query);
        const matchesDescription = task.description?.toLowerCase().includes(query) || false;
        return matchesTaskKey || matchesId || matchesTitle || matchesDescription;
      });

      const columnsWithTasks = statusColumns.map((col) => ({
        ...col,
        tasks: filteredTasks.filter((task) => task.status === col.id),
      }));
      setColumns(columnsWithTasks);
    }
  }, [searchQuery, allTasks]);

  const handleTaskClick = async (taskId: string) => {
    router.push(`/kanban/task/${taskId}`);
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);

    try {
      const parsedTags = createFormData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean);

      // Filter out empty dependencies
      const validDependencies = createFormData.dependencies.filter(dep => dep.taskId && dep.taskId.trim() !== '');

      const response = await fetch('/api/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...createFormData,
          tags: parsedTags,
          dependencies: validDependencies,
        }),
      });

      if (response.ok) {
        const newTask = await response.json();
        
        // Add new task to state
        setAllTasks((prev) => [newTask, ...prev]);
        
        // Reset form and close modal
        setCreateFormData({
          title: '',
          description: '',
          status: 'TODO',
          priority: 'MEDIUM',
          dueDate: '',
          estimatedHours: '',
          projectId: '',
          tags: '',
          dependencies: [],
        });
        setShowCreateModal(false);
      } else {
        const error = await response.json();
        console.error('Failed to create task:', error);
        alert(error.error || 'Failed to create task');
      }
    } catch (error) {
      console.error('Error creating task:', error);
      alert('Failed to create task');
    } finally {
      setIsCreating(false);
    }
  };

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const task = columns
      .flatMap((col) => col.tasks)
      .find((t) => t.id === active.id);
    setActiveTask(task || null);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    if (activeId === overId) return;

    const activeColumn = columns.find((col) =>
      col.tasks.some((task) => task.id === activeId)
    );
    const overColumn = columns.find(
      (col) =>
        col.id === overId || col.tasks.some((task) => task.id === overId)
    );

    if (!activeColumn || !overColumn) return;

    if (activeColumn.id !== overColumn.id) {
      setColumns((cols) => {
        const activeItems = activeColumn.tasks;
        const overItems = overColumn.tasks;
        const activeIndex = activeItems.findIndex((t) => t.id === activeId);
        const overIndex = overItems.findIndex((t) => t.id === overId);

        const activeTask = activeItems[activeIndex];

        return cols.map((col) => {
          if (col.id === activeColumn.id) {
            return {
              ...col,
              tasks: activeItems.filter((t) => t.id !== activeId),
            };
          } else if (col.id === overColumn.id) {
            const newTasks = [...overItems];
            const insertAt = overIndex >= 0 ? overIndex : overItems.length;
            newTasks.splice(insertAt, 0, activeTask);
            return { ...col, tasks: newTasks };
          }
          return col;
        });
      });
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    const activeColumn = columns.find((col) =>
      col.tasks.some((task) => task.id === activeId)
    );

    if (!activeColumn) return;

    const activeIndex = activeColumn.tasks.findIndex((t) => t.id === activeId);
    const overIndex = activeColumn.tasks.findIndex((t) => t.id === overId);

    if (activeIndex !== overIndex) {
      setColumns((cols) =>
        cols.map((col) => {
          if (col.id === activeColumn.id) {
            return {
              ...col,
              tasks: arrayMove(col.tasks, activeIndex, overIndex),
            };
          }
          return col;
        })
      );
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl font-bold text-gray-900 mb-8">Kanban Board</h1>
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-600 text-lg">Loading tasks...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">
              Kanban Board
              {currentProject && (
                <span className="ml-3 text-2xl text-gray-600">
                  — {currentProject.name}
                </span>
              )}
            </h1>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-md hover:shadow-lg flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Task
          </button>
        </div>
        
        {/* Search Box */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <input
              type="text"
              placeholder="Search by task key, ID, title, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-3 pr-10 bg-white text-gray-900 placeholder:text-gray-400 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                title="Clear search"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
            {!searchQuery && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            )}
          </div>
          {searchQuery && (
            <p className="mt-2 text-sm text-gray-600">
              Showing {columns.reduce((sum, col) => sum + col.tasks.length, 0)} of {allTasks.length} tasks
            </p>
          )}
        </div>
        
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-6 overflow-x-auto pb-4">
            {columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                tasks={column.tasks}
                onTaskClick={handleTaskClick}
              />
            ))}
          </div>
          
          <DragOverlay>
            {activeTask ? (
              <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-200 w-80 rotate-3">
                <h3 className="font-semibold text-gray-900 mb-2">
                  {activeTask.title}
                </h3>
                <p className="text-sm text-gray-600">{activeTask.description}</p>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        {/* Create Task Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={() => setShowCreateModal(false)}>
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Create New Task</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl font-bold w-8 h-8 flex items-center justify-center"
                >
                  ×
                </button>
              </div>

              <form onSubmit={handleCreateTask} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={createFormData.title}
                    onChange={(e) => setCreateFormData({ ...createFormData, title: e.target.value })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    placeholder="Enter task title"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    value={createFormData.description}
                    onChange={(e) => setCreateFormData({ ...createFormData, description: e.target.value })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none min-h-[100px]"
                    placeholder="Enter task description"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Project <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={createFormData.projectId}
                    onChange={(e) => setCreateFormData({ ...createFormData, projectId: e.target.value })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    required
                  >
                    <option value="">Select a project</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Status
                    </label>
                    <select
                      value={createFormData.status}
                      onChange={(e) => setCreateFormData({ ...createFormData, status: e.target.value as TaskStatus })}
                      className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
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
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Priority
                    </label>
                    <select
                      value={createFormData.priority}
                      onChange={(e) => setCreateFormData({ ...createFormData, priority: e.target.value as Priority })}
                      className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    >
                      <option value="LOW">Low</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HIGH">High</option>
                      <option value="URGENT">Urgent</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Due Date
                    </label>
                    <input
                      type="date"
                      value={createFormData.dueDate}
                      onChange={(e) => setCreateFormData({ ...createFormData, dueDate: e.target.value })}
                      className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Estimated Hours
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      value={createFormData.estimatedHours}
                      onChange={(e) => setCreateFormData({ ...createFormData, estimatedHours: e.target.value })}
                      className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      placeholder="0"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Labels (tags)
                  </label>
                  <input
                    type="text"
                    value={createFormData.tags}
                    onChange={(e) => setCreateFormData({ ...createFormData, tags: e.target.value })}
                    className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    placeholder="e.g. social, video, q1"
                  />
                  <p className="mt-1 text-xs text-gray-500">Comma-separated</p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Dependencies
                  </label>
                  <div className="space-y-2">
                    {createFormData.dependencies.map((dep, index) => (
                      <div key={index} className="flex gap-2 items-start">
                        <select
                          value={dep.type}
                          onChange={(e) => {
                            const newDeps = [...createFormData.dependencies];
                            newDeps[index].type = e.target.value as 'blockedBy' | 'blocks';
                            setCreateFormData({ ...createFormData, dependencies: newDeps });
                          }}
                          className="px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        >
                          <option value="blockedBy">Blocked By</option>
                          <option value="blocks">Blocks</option>
                        </select>
                        <select
                          value={dep.taskId}
                          onChange={(e) => {
                            const newDeps = [...createFormData.dependencies];
                            newDeps[index].taskId = e.target.value;
                            setCreateFormData({ ...createFormData, dependencies: newDeps });
                          }}
                          className="flex-1 px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        >
                          <option value="">Select task...</option>
                          {allTasks.map((task) => (
                            <option key={task.id} value={task.id}>
                              {task.taskKey ? `[${task.taskKey}] ` : ''}{task.title}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => {
                            const newDeps = createFormData.dependencies.filter((_, i) => i !== index);
                            setCreateFormData({ ...createFormData, dependencies: newDeps });
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
                        setCreateFormData({
                          ...createFormData,
                          dependencies: [...createFormData.dependencies, { taskId: '', type: 'blockedBy' }],
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
                    disabled={isCreating}
                    className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    {isCreating ? 'Creating...' : 'Create Task'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    disabled={isCreating}
                    className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
