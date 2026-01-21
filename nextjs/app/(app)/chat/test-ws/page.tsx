'use client';

import { useState, useEffect } from 'react';
import { getStoredToken, getStoredUser } from '@/lib/auth/client';

export default function TestWSPage() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
  const [wsStatus, setWsStatus] = useState<string>('Not started');
  const [logs, setLogs] = useState<string[]>([]);
  const [testToken, setTestToken] = useState('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjbWs0MmU4NnIwMDAwcDRueXVwM3QxMXhnIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsIm5hbWUiOiJBZG1pbiBVc2VyIiwiaWF0IjoxNzY4OTg1MDg2LCJleHAiOjE3Njk1ODk4ODZ9.T0jF1EfgXrKjeHQhd5O_RPYheQ7QhFpo-y83Wf0FaRM');
  const [conversationId, setConversationId] = useState('1fd29fe0-53f2-43c6-81e7-1baacf87882c');

  const addLog = (msg: string) => {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    setLogs(prev => [...prev, `[${timestamp}] ${msg}`]);
    console.log(`[Test WS] ${msg}`);
  };

  useEffect(() => {
    const storedToken = getStoredToken();
    const storedUser = getStoredUser();
    setToken(storedToken);
    setUser(storedUser);
    
    addLog(`Token in localStorage: ${storedToken ? 'YES' : 'NO'}`);
    addLog(`User in localStorage: ${storedUser ? JSON.stringify(storedUser) : 'NO'}`);
  }, []);

  const storeTestToken = () => {
    localStorage.setItem('auth-token', testToken);
    localStorage.setItem('user', JSON.stringify({
      userId: 'cmk42e86r0000p4nyup3t11xg',
      email: 'admin@example.com',
      name: 'Admin User'
    }));
    addLog('✅ Token stored in localStorage');
    setToken(testToken);
    setUser({ email: 'admin@example.com', name: 'Admin User' });
  };

  const testWebSocket = () => {
    addLog('Starting WebSocket test...');
    setWsStatus('Connecting...');
    
    const currentToken = getStoredToken() || testToken;
    if (!currentToken) {
      addLog('❌ No token available');
      setWsStatus('Error: No token');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    
    addLog(`Connecting to: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      addLog('✅ WebSocket opened');
      setWsStatus('Connected');
      
      // Authenticate
      addLog('Sending auth...');
      ws.send(JSON.stringify({
        type: 'auth',
        token: currentToken,
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      addLog(`📩 Received: ${data.type}`);
      
      if (data.type === 'auth_success') {
        addLog(`✅ Authenticated as: ${data.userId}`);
        setWsStatus('Authenticated');
        
        // Subscribe to conversation
        addLog(`Subscribing to conversation: ${conversationId}`);
        ws.send(JSON.stringify({
          type: 'subscribe',
          conversationId: conversationId,
        }));
      } else if (data.type === 'subscribed') {
        addLog(`✅ Subscribed to: ${data.conversationId}`);
        setWsStatus('Subscribed');
      } else if (data.type === 'error') {
        addLog(`❌ Error: ${data.error}`);
        setWsStatus(`Error: ${data.error}`);
      }
    };

    ws.onerror = (error) => {
      addLog(`❌ WebSocket error: ${JSON.stringify(error)}`);
      setWsStatus('Error');
    };

    ws.onclose = (event) => {
      addLog(`🔌 Closed: code=${event.code}, reason=${event.reason || 'none'}`);
      setWsStatus(`Disconnected (${event.code})`);
    };
  };

  const clearStorage = () => {
    localStorage.clear();
    setToken(null);
    setUser(null);
    addLog('🗑️ localStorage cleared');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">WebSocket Connection Test</h1>
        
        {/* Status */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Current Status</h2>
          <div className="space-y-2">
            <div>
              <span className="font-medium">Token in localStorage:</span>{' '}
              <span className={token ? 'text-green-600' : 'text-red-600'}>
                {token ? '✓ YES' : '✗ NO'}
              </span>
              {token && (
                <div className="text-xs text-gray-500 mt-1 break-all">
                  {token.substring(0, 50)}...
                </div>
              )}
            </div>
            <div>
              <span className="font-medium">User in localStorage:</span>{' '}
              <span className={user ? 'text-green-600' : 'text-red-600'}>
                {user ? `✓ ${user.email}` : '✗ NO'}
              </span>
            </div>
            <div>
              <span className="font-medium">WebSocket Status:</span>{' '}
              <span className="font-mono">{wsStatus}</span>
            </div>
          </div>
        </div>

        {/* Test Token Input */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Test Configuration</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                JWT Token
              </label>
              <textarea
                value={testToken}
                onChange={(e) => setTestToken(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-xs"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Conversation ID
              </label>
              <input
                type="text"
                value={conversationId}
                onChange={(e) => setConversationId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Actions</h2>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={storeTestToken}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Store Test Token
            </button>
            <button
              onClick={testWebSocket}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Test WebSocket
            </button>
            <button
              onClick={clearStorage}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
            >
              Clear Storage
            </button>
            <button
              onClick={() => setLogs([])}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Clear Logs
            </button>
          </div>
        </div>

        {/* Logs */}
        <div className="bg-gray-900 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Connection Log</h2>
          <div className="bg-black rounded p-4 h-96 overflow-y-auto">
            {logs.length === 0 ? (
              <div className="text-gray-500 text-sm">No logs yet...</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="text-green-400 text-xs font-mono mb-1">
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
