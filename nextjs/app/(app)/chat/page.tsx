'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const DEFAULT_MESSAGE: Message = {
  id: 1,
  role: 'assistant',
  content: 'Hello! I\'m your AI content strategy assistant. I can help you plan your content calendar, suggest video ideas, analyze trends, and optimize your posting schedule. How can I help you today?',
  timestamp: new Date(),
};

function ChatContent() {
  const searchParams = useSearchParams();
  const chatId = searchParams.get('chatid');
  console.log('Chat ID from query string:', chatId);
  const [messages, setMessages] = useState<Message[]>([DEFAULT_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load conversation if chatId is provided in query string
  useEffect(() => {
    setMounted(true);

    const loadConversation = async () => {
      if (!chatId) return;

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
        }));

        // If no messages, show default greeting
        if (loadedMessages.length === 0) {
          setMessages([DEFAULT_MESSAGE]);
        } else {
          setMessages(loadedMessages);
        }

        setConversationId(conversation.id);
        
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

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: messages.length + 1,
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Call the OpenAI API through our backend
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input,
          conversationId: conversationId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get response');
      }

      const data = await response.json();

      // Store conversationId if this is the first message
      if (!conversationId && data.conversationId) {
        setConversationId(data.conversationId);
      }

      const aiMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: data.content,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error: any) {
      console.error('Chat error:', error);
      
      const errorMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please make sure the OpenAI API key is configured.`,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
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
          {conversationId 
            ? `Conversation ID: ${conversationId}` 
            : 'Get personalized content suggestions and strategic advice'}
        </p>
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
                    <span className="text-sm text-gray-500">Thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          )}
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
