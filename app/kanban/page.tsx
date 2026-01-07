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

import { TaskStatus } from '@prisma/client';

interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
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

function TaskCard({ task }: { task: Task }) {
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

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
    >
      <h3 className="font-semibold text-gray-900 mb-2">{task.title}</h3>
      <p className="text-sm text-gray-600">{task.description || 'No description'}</p>
    </div>
  );
}

function KanbanColumn({
  column,
  tasks,
}: {
  column: Column;
  tasks: Task[];
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 min-h-[500px] w-80">
      <h2 className="font-bold text-lg mb-4 text-gray-800">{column.title}</h2>
      <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
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
  const [loading, setLoading] = useState(true);

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
      </div>
    </div>
  );
}
