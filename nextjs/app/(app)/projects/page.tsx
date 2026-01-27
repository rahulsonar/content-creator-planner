'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Task {
  id: string;
  title: string;
  status: string;
  priority: string;
}

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  isDefault: boolean;
  startDate: string | null;
  endDate: string | null;
  dueDate: string | null;
  color: string | null;
  icon: string | null;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  tasks: Task[];
  _count: {
    tasks: number;
  };
}

const statusColors: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  ON_HOLD: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  COMPLETED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  ARCHIVED: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  CANCELLED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

const statusLabels: Record<string, string> = {
  ACTIVE: 'Active',
  ON_HOLD: 'On Hold',
  COMPLETED: 'Completed',
  ARCHIVED: 'Archived',
  CANCELLED: 'Cancelled',
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [updatingDefaultId, setUpdatingDefaultId] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/projects');
      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }
      const data = await response.json();
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (projectId: string) => {
    if (updatingDefaultId) return;
    try {
      setUpdatingDefaultId(projectId);
      const response = await fetch('/api/projects', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ projectId, isDefault: true }),
      });

      if (!response.ok) {
        throw new Error('Failed to set default project');
      }

      setProjects((prev: Project[]) =>
        prev.map((project: Project) => ({
          ...project,
          isDefault: project.id === projectId,
        }))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setUpdatingDefaultId(null);
    }
  };

  const calculateProgress = (project: Project) => {
    const totalTasks = project.tasks.length;
    if (totalTasks === 0) return 0;
    const completedTasks = project.tasks.filter(t => t.status === 'COMPLETED').length;
    return Math.round((completedTasks / totalTasks) * 100);
  };

  const filteredProjects = projects.filter(project => {
    if (filter === 'all') return true;
    return project.status === filter;
  });

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-blue-900 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-white text-xl">Loading projects...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-blue-900 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-500/10 border border-red-500 text-red-200 p-4 rounded-lg">
            Error: {error}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-blue-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Projects</h1>
          <p className="text-gray-300">Manage and track your content creation projects</p>
        </div>

        {/* Filter Tabs */}
        <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
              filter === 'all'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            All Projects ({projects.length})
          </button>
          {Object.entries(statusLabels).map(([key, label]) => {
            const count = projects.filter(p => p.status === key).length;
            return (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                  filter === key
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {label} ({count})
              </button>
            );
          })}
        </div>

        {/* Projects Grid */}
        {filteredProjects.length === 0 ? (
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-12 text-center">
            <p className="text-gray-400 text-lg">No projects found</p>
            <p className="text-gray-500 mt-2">
              {filter !== 'all' ? 'Try changing the filter' : 'Create your first project to get started'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project) => {
              const progress = calculateProgress(project);
              return (
                <div
                  key={project.id}
                  className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 hover:bg-gray-800/70 transition-all border border-gray-700 hover:border-purple-500"
                >
                  {/* Project Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      {project.icon && (
                        <span className="text-2xl">{project.icon}</span>
                      )}
                      <div>
                        <h3 className="text-xl font-semibold text-white">
                          {project.name}
                        </h3>
                        {project.isDefault && (
                          <span className="inline-flex items-center mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/20 text-purple-200">
                            Default
                          </span>
                        )}
                      </div>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        statusColors[project.status] || statusColors.ACTIVE
                      }`}
                    >
                      {statusLabels[project.status] || project.status}
                    </span>
                  </div>

                  {/* Description */}
                  {project.description && (
                    <p className="text-gray-300 text-sm mb-4 line-clamp-2">
                      {project.description}
                    </p>
                  )}

                  {/* Tags */}
                  {project.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {project.tags.map((tag, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-gray-700 text-gray-300 text-xs rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Progress Bar */}
                  <div className="mb-4">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">Progress</span>
                      <span className="text-gray-300">{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <p className="text-gray-400 text-xs">Tasks</p>
                      <p className="text-white font-semibold">{project._count.tasks}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-xs">Due Date</p>
                      <p className="text-white font-semibold text-sm">
                        {formatDate(project.dueDate)}
                      </p>
                    </div>
                  </div>

                  {/* Dates */}
                  <div className="text-xs text-gray-500 mb-4">
                    <div>Created: {formatDate(project.createdAt)}</div>
                    <div>Updated: {formatDate(project.updatedAt)}</div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Link
                      href={`/projects/${project.id}`}
                      className="flex-1 bg-purple-600 hover:bg-purple-700 text-white text-center py-2 rounded-lg transition-colors text-sm font-medium"
                    >
                      View Details
                    </Link>
                    {!project.isDefault && (
                      <button
                        onClick={() => handleSetDefault(project.id)}
                        disabled={updatingDefaultId === project.id}
                        className="flex-1 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-900/60 disabled:cursor-not-allowed text-white text-center py-2 rounded-lg transition-colors text-sm font-medium"
                        title="Mark as default project"
                      >
                        {updatingDefaultId === project.id ? 'Setting...' : 'Make Default'}
                      </button>
                    )}
                    <Link
                      href={`/kanban?projectId=${project.id}`}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-center py-2 rounded-lg transition-colors text-sm font-medium"
                      title="View Kanban Board"
                    >
                      Board
                    </Link>
                    <button
                      className="px-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                      title="More options"
                    >
                      •••
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
