'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getStoredUser } from '@/lib/auth/client';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

function ChatContent() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    // Get user's name and personalize the greeting
    const user = getStoredUser();
    const userName = user?.name || user?.email?.split('@')[0] || 'there';
    
    const defaultMessage: Message = {
      id: 1,
      role: 'assistant',
      content: `Hello ${userName}! I'm your AI content strategy assistant. I can help you plan your content calendar, suggest video ideas, analyze trends, and optimize your posting schedule. How can I help you today?`,
      timestamp: new Date(),
    };
    
    setMessages([defaultMessage]);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: messages.length + 1,
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    const messageToSend = input;
    setInput('');
    setIsLoading(true);

    try {
      // Call the chat API (no conversationId for new chat)
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageToSend,
          conversationId: null, // First message, no ID yet
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get response');
      }

      const data = await response.json();

      // Redirect to the conversation-specific page
      if (data.conversationId) {
        router.push(`/chat/${data.conversationId}`);
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      
      const errorMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please make sure the OpenAI API key is configured.`,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    }
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
        <h1 className="text-2xl font-bold text-gray-900">AI Content Strategy Assistant</h1>
        <p className="text-sm text-gray-600 mt-1">
          Get personalized content suggestions and strategic advice
        </p>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">{messages.map((message) => (
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
                      {mounted ? message.timestamp.toLocaleTimeString() : ''}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
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
                    <span className="text-sm text-gray-500">Starting new conversation...</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">{<div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about content strategy, video ideas, scheduling..."
              disabled={isLoading}
              className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-500 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              rows={3}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Sending...</span>
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
        </div>}
      </div>
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
