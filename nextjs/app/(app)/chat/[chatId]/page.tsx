'use client';

import { useState, useEffect, Suspense, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWebSocket } from '@/lib/hooks/useWebSocket';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  model?: string;
}

const DEFAULT_MESSAGE: Message = {
  id: 1,
  role: 'assistant',
  content: 'Hello! I\'m your AI content strategy assistant. I can help you plan your content calendar, suggest video ideas, analyze trends, and optimize your posting schedule. How can I help you today?',
  timestamp: new Date(),
};

function getDisplayTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';
  } catch {
    return 'Asia/Kolkata';
  }
}

function formatMessageTimestamp(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    timeZone: getDisplayTimeZone(),
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

function ChatContent() {
  const params = useParams();
  const router = useRouter();
  const chatId = params.chatId as string;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  console.log('ChatContent render - chatId:', chatId, 'mounted:', mounted);
  
  const [messages, setMessages] = useState<Message[]>([DEFAULT_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoadingConversation, setIsLoadingConversation] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'processing'>('disconnected');

  // Only connect WebSocket after component is mounted and chatId is available
  const shouldConnectWs = mounted && chatId;

  // WebSocket hook for real-time updates
  const { isConnected, isProcessing, sendMessage } = useWebSocket({
    conversationId: shouldConnectWs ? chatId : null,
    onMessage: (message) => {
      console.log('[Chat Page] Received WebSocket message:', message.content.substring(0, 100));
      setMessages((prev) => [...prev, message]);
      // Scroll to bottom when new message arrives
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    },
    onError: (errorMsg) => {
      console.error('[Chat Page] WebSocket error:', errorMsg);
      setError(errorMsg);
    },
    onStatusChange: (status) => {
      setWsStatus(status);
    },
  });

  // Load conversation on mount
  useEffect(() => {
    setMounted(true);

    const loadConversation = async () => {
      setIsLoadingConversation(true);
      setError(null);

      try {
        const response = await fetch(`/api/chat/${chatId}`);
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to load conversation');
        }

        const conversation = await response.json();
        
        // Convert stored messages to display format
        const loadedMessages: Message[] = conversation.messages.map((msg: any, index: number) => ({
          id: index + 1,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          model: msg.model,
        }));

        // If no messages, show default greeting
        if (loadedMessages.length === 0) {
          setMessages([DEFAULT_MESSAGE]);
        } else {
          setMessages(loadedMessages);
        }
        
      } catch (error: any) {
        console.error('Failed to load conversation:', error);
        setError(error.message);
        setMessages([DEFAULT_MESSAGE]);
      } finally {
        setIsLoadingConversation(false);
      }
    };

    loadConversation();
  }, [chatId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;

    const userMessage: Message = {
      id: messages.length + 1,
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    const messageToSend = input;
    setInput('');

    // Send via WebSocket for real-time response
    sendMessage(messageToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">AI Content Strategy Assistant</h1>
            <div className="flex items-center gap-3 mt-1">
              <p className="text-sm text-gray-600">
                Conversation ID: {chatId}
              </p>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                wsStatus === 'connected' ? 'bg-green-100 text-green-700' :
                wsStatus === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${
                  wsStatus === 'connected' ? 'bg-green-500' :
                  wsStatus === 'processing' ? 'bg-yellow-500' :
                  'bg-red-500'
                }`}></span>
                {wsStatus === 'connected' ? 'Live' : 
                 wsStatus === 'processing' ? 'Processing' : 
                 'Reconnecting...'}
              </span>
            </div>
          </div>
          <button
            onClick={() => router.push('/chat')}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center gap-2 shadow-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
            New Chat
          </button>
        </div>
        {error && (
          <div className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
            ⚠️ {error}
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoadingConversation && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading conversation...</p>
          </div>
        </div>
      )}

      {/* Messages Container */}
      {!isLoadingConversation && (
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-lg px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-900'
                }`}
              >
                <div className="flex items-start gap-3">
                  {message.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold text-sm">
                      AI
                    </div>
                  )}
                  <div className="flex-1">
                    {message.role === 'assistant' ? (
                      <div className="text-sm prose prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-p:my-2 prose-li:my-1 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    )}
                    <p className={`text-xs mt-2 ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                      {mounted ? formatMessageTimestamp(message.timestamp) : ''}
                      {message.model && message.role === 'assistant' && (
                        <span className="ml-2 opacity-60">• {message.model}</span>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {isProcessing && (
            <div className="flex justify-start">
              <div className="max-w-3xl rounded-lg px-4 py-3 bg-white border border-gray-200">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold text-sm">
                    AI
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-sm text-gray-500">Processing your request...</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Area */}
      {!isLoadingConversation && (
        <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about content strategy, video ideas, scheduling..."
              disabled={isProcessing || !isConnected}
              className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-500 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              rows={3}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isProcessing || !isConnected}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
            >
              {isProcessing ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Processing...</span>
                </>
              ) : !isConnected ? (
                <>
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
                  </svg>
                  <span>Connecting...</span>
                </>
              ) : (
                'Send'
              )}
            </button>
          </div>
          <div className="mt-3 flex gap-2 flex-wrap">
            <button
              onClick={() => setInput('Help me plan content for the next month')}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
            >
              📅 Plan next month
            </button>
            <button
              onClick={() => setInput('What are trending topics in my niche?')}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
            >
              📈 Trending topics
            </button>
            <button
              onClick={() => setInput('Suggest video ideas for beginners')}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
            >
              💡 Video ideas
            </button>
            <button
              onClick={() => setInput('Analyze my posting schedule')}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
            >
              ⏰ Schedule analysis
            </button>
          </div>
        </div>
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading chat...</p>
          </div>
        </div>
      </div>
    }>
      <ChatContent />
    </Suspense>
  );
}
