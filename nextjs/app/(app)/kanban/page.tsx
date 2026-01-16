'use client';

import React, { useState, useEffect } from 'react';
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

interface Task {
  id: string;
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
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-gray-900 flex-1">{task.title}</h3>
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

function TaskModal({ task, onClose }: { task: Task | null; onClose: () => void }) {
  if (!task) return null;

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
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold w-8 h-8 flex items-center justify-center"
          >
            ×
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">{task.title}</h3>
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

          {task.tags && task.tags.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Tags</h4>
              <div className="flex flex-wrap gap-2">
                {task.tags.map((tag, index) => (
                  <span key={index} className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full text-sm">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {task.subtasks && task.subtasks.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Subtasks ({task.subtasks.length})</h4>
              <ul className="space-y-2">
                {task.subtasks.map((subtask) => (
                  <li key={subtask.id} className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${subtask.status === 'COMPLETED' ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                    <span className={subtask.status === 'COMPLETED' ? 'line-through text-gray-500' : 'text-gray-700'}>
                      {subtask.title}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(task.createdAt || task.updatedAt) && (
            <div className="border-t pt-4 text-xs text-gray-500 space-y-1">
              {task.createdAt && <p>Created: {formatDate(task.createdAt)}</p>}
              {task.updatedAt && <p>Last updated: {formatDate(task.updatedAt)}</p>}
            </div>
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
  const [columns, setColumns] = useState<Column[]>(
    statusColumns.map((col) => ({ ...col, tasks: [] }))
  );
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingTask, setLoadingTask] = useState(false);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await fetch('/api/tasks');
        const tasks: Task[] = await response.json();
        
        const columnsWithTasks = statusColumns.map((col) => ({
          ...col,
          tasks: tasks.filter((task) => task.status === col.id),
        }));
        
        setColumns(columnsWithTasks);
      } catch (error) {
        console.error('Failed to fetch tasks:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  const handleTaskClick = async (taskId: string) => {
    setLoadingTask(true);
    try {
      const response = await fetch(`/api/tasks/${taskId}`);
      if (response.ok) {
        const task = await response.json();
        setSelectedTask(task);
      } else {
        console.error('Failed to fetch task details');
      }
    } catch (error) {
      console.error('Error fetching task:', error);
    } finally {
      setLoadingTask(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedTask(null);
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
        <h1 className="text-4xl font-bold text-gray-900 mb-8">Kanban Board</h1>
        
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

        {selectedTask && <TaskModal task={selectedTask} onClose={handleCloseModal} />}
        {loadingTask && (
          <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 shadow-xl">
              <p className="text-gray-700">Loading task details...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
