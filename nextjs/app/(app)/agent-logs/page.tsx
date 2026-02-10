'use client';

import { useState, useEffect } from 'react';

interface AgentCallLog {
  id: number;
  userId: number;
  conversationId: string | null;
  messageId: string;
  sessionId: string | null;
  agentName: string;
  agentType: string | null;
  agentVersion: string | null;
  modelName: string;
  modelProvider: string;
  inputMessage: string | null;
  outputMessage: string | null;
  toolsEnabled: boolean;
  toolCalls: any | null;
  toolResults: any | null;
  status: string;
  startedAt: string;
  completedAt: string | null;
  durationMs: number | null;
  promptTokens: number | null;
  completionTokens: number | null;
  totalTokens: number | null;
  error: string | null;
  errorType: string | null;
  stackTrace: string | null;
  metadata: any | null;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

interface GroupedLogs {
  [messageId: string]: AgentCallLog[];
}

export default function AgentLogsPage() {
  const [groupedLogs, setGroupedLogs] = useState<GroupedLogs>({});
  const [allLogs, setAllLogs] = useState<AgentCallLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState({ agentName: '', status: '' });

  useEffect(() => {
    fetchLogs();
  }, [filter]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filter.agentName) params.append('agentName', filter.agentName);
      if (filter.status) params.append('status', filter.status);

      const response = await fetch(`/api/agent-logs?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to fetch logs');
      
      const data = await response.json();
      setGroupedLogs(data.groupedLogs);
      setAllLogs(data.logs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const toggleMessage = (messageId: string) => {
    const newExpanded = new Set(expandedMessages);
    if (newExpanded.has(messageId)) {
      newExpanded.delete(messageId);
    } else {
      newExpanded.add(messageId);
    }
    setExpandedMessages(newExpanded);
  };

  const toggleLog = (logId: string) => {
    const newExpanded = new Set(expandedLogs);
    if (newExpanded.has(logId)) {
      newExpanded.delete(logId);
    } else {
      newExpanded.add(logId);
    }
    setExpandedLogs(newExpanded);
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30';
      case 'FAILED': return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
      case 'IN_PROGRESS': return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30';
      case 'CANCELLED': return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30';
      default: return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-gray-800 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading agent logs...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            Agent Call Logs
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            View all agent interactions grouped by message ID
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Agent Name
              </label>
              <input
                type="text"
                value={filter.agentName}
                onChange={(e) => setFilter({ ...filter, agentName: e.target.value })}
                placeholder="Filter by agent name..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Status
              </label>
              <select
                value={filter.status}
                onChange={(e) => setFilter({ ...filter, status: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Statuses</option>
                <option value="COMPLETED">Completed</option>
                <option value="FAILED">Failed</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => setFilter({ agentName: '', status: '' })}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
          
          <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
            Showing {allLogs.length} log entries across {Object.keys(groupedLogs).length} messages
          </div>
        </div>

        {error && (
          <div className="bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 p-4 rounded-lg mb-6">
            Error: {error}
          </div>
        )}

        {/* Grouped Logs */}
        <div className="space-y-4">
          {Object.keys(groupedLogs).length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8 text-center">
              <p className="text-gray-600 dark:text-gray-400">No agent logs found</p>
            </div>
          ) : (
            Object.entries(groupedLogs).map(([messageId, logs]) => (
              <div key={messageId} className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
                <div
                  className="p-4 bg-gradient-to-r from-purple-100 to-blue-100 dark:from-purple-900/50 dark:to-blue-900/50 cursor-pointer hover:from-purple-200 hover:to-blue-200 dark:hover:from-purple-900/70 dark:hover:to-blue-900/70 transition-all"
                  onClick={() => toggleMessage(messageId)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        Message ID: {messageId}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {logs.length} agent call{logs.length !== 1 ? 's' : ''} • 
                        {' '}{logs[0].conversationId ? `Conversation: ${logs[0].conversationId}` : 'No conversation ID'}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {formatDate(logs[0].startedAt)}
                        </div>
                      </div>
                      <svg
                        className={`w-6 h-6 text-gray-600 dark:text-gray-400 transition-transform ${
                          expandedMessages.has(messageId) ? 'rotate-180' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>

                {expandedMessages.has(messageId) && (
                  <div className="p-4 space-y-3">
                    {logs
                      .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
                      .map((log) => {
                        // Check if this is a subtask log
                        const isSubtask = log.messageId.includes('_task_');
                        const taskId = isSubtask ? log.messageId.split('_task_')[1] : null;
                        
                        return (
                      <div
                        key={log.id}
                        className={`border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden ${isSubtask ? 'ml-6' : ''}`}
                      >
                        <div
                          className="p-3 bg-gray-50 dark:bg-gray-700/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                          onClick={() => toggleLog(log.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              {isSubtask && (
                                <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                  ↳ {taskId}
                                </span>
                              )}
                              <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(log.status)}`}>
                                {log.status}
                              </span>
                              <span className="font-medium text-gray-900 dark:text-white">
                                {log.agentName}
                              </span>
                              <span className="text-sm text-gray-600 dark:text-gray-400">
                                {log.modelName}
                              </span>
                            </div>
                            <div className="flex items-center gap-4">
                              <span className="text-sm text-gray-600 dark:text-gray-400">
                                {formatDuration(log.durationMs)}
                              </span>
                              {log.totalTokens && (
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                  {log.totalTokens} tokens
                                </span>
                              )}
                              <svg
                                className={`w-5 h-5 text-gray-600 dark:text-gray-400 transition-transform ${
                                  expandedLogs.has(log.id) ? 'rotate-180' : ''
                                }`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </div>
                          </div>
                        </div>

                        {expandedLogs.has(log.id) && (
                          <div className="p-4 space-y-4 bg-white dark:bg-gray-800">
                            {/* Basic Info */}
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">User ID:</span>
                                <span className="ml-2 text-gray-600 dark:text-gray-400">{log.userId}</span>
                              </div>
                              {log.sessionId && (
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Session ID:</span>
                                  <span className="ml-2 text-gray-600 dark:text-gray-400">{log.sessionId}</span>
                                </div>
                              )}
                              {log.agentType && (
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Agent Type:</span>
                                  <span className="ml-2 text-gray-600 dark:text-gray-400">{log.agentType}</span>
                                </div>
                              )}
                              {log.agentVersion && (
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Version:</span>
                                  <span className="ml-2 text-gray-600 dark:text-gray-400">{log.agentVersion}</span>
                                </div>
                              )}
                            </div>

                            {/* Input Message */}
                            {log.inputMessage && (
                              <div>
                                <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Input:</h4>
                                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded border border-gray-200 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-300 whitespace-pre-wrap">
                                  {log.inputMessage}
                                </div>
                              </div>
                            )}

                            {/* Output Message */}
                            {log.outputMessage && (
                              <div>
                                <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Output:</h4>
                                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded border border-gray-200 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-300 whitespace-pre-wrap">
                                  {log.outputMessage}
                                </div>
                              </div>
                            )}

                            {/* Tool Calls */}
                            {log.toolCalls && (
                              <div>
                                <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Tool Calls:</h4>
                                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded border border-gray-200 dark:border-gray-700">
                                  <pre className="text-sm text-gray-800 dark:text-gray-300 overflow-x-auto">
                                    {JSON.stringify(log.toolCalls, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {/* Tool Results */}
                            {log.toolResults && (
                              <div>
                                <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Tool Results:</h4>
                                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded border border-gray-200 dark:border-gray-700">
                                  <pre className="text-sm text-gray-800 dark:text-gray-300 overflow-x-auto">
                                    {JSON.stringify(log.toolResults, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {/* Error */}
                            {log.error && (
                              <div>
                                <h4 className="font-medium text-red-700 dark:text-red-400 mb-2">Error:</h4>
                                <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded border border-red-200 dark:border-red-800 text-sm text-red-800 dark:text-red-300">
                                  <div className="font-medium mb-1">{log.errorType || 'Unknown Error'}</div>
                                  <div className="whitespace-pre-wrap">{log.error}</div>
                                  {log.stackTrace && (
                                    <details className="mt-2">
                                      <summary className="cursor-pointer font-medium">Stack Trace</summary>
                                      <pre className="mt-2 text-xs overflow-x-auto">{log.stackTrace}</pre>
                                    </details>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* Token Usage */}
                            {log.totalTokens && (
                              <div className="grid grid-cols-3 gap-4 text-sm bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Prompt:</span>
                                  <span className="ml-2 text-gray-600 dark:text-gray-400">{log.promptTokens}</span>
                                </div>
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Completion:</span>
                                  <span className="ml-2 text-gray-600 dark:text-gray-400">{log.completionTokens}</span>
                                </div>
                                <div>
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Total:</span>
                                  <span className="ml-2 text-gray-600 dark:text-gray-400">{log.totalTokens}</span>
                                </div>
                              </div>
                            )}

                            {/* Metadata */}
                            {log.metadata && (
                              <div>
                                <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Metadata:</h4>
                                <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded border border-gray-200 dark:border-gray-700">
                                  <pre className="text-sm text-gray-800 dark:text-gray-300 overflow-x-auto">
                                    {JSON.stringify(log.metadata, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {/* Tags */}
                            {log.tags && log.tags.length > 0 && (
                              <div>
                                <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Tags:</h4>
                                <div className="flex flex-wrap gap-2">
                                  {log.tags.map((tag, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded text-xs"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Timestamps */}
                            <div className="grid grid-cols-2 gap-4 text-xs text-gray-600 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-3">
                              <div>
                                <span className="font-medium">Started:</span> {formatDate(log.startedAt)}
                              </div>
                              {log.completedAt && (
                                <div>
                                  <span className="font-medium">Completed:</span> {formatDate(log.completedAt)}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )})}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
