'use client';

import { useState } from 'react';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: 'assistant',
      content: 'Hello! I\'m your AI content strategy assistant. I can help you plan your content calendar, suggest video ideas, analyze trends, and optimize your posting schedule. How can I help you today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: messages.length + 1,
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    setInput('');

    // Simulate AI response after a short delay
    setTimeout(() => {
      const aiMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: 'This is a dummy response. The AI functionality will be implemented soon!',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    }, 1000);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
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
        <p className="text-sm text-gray-600 mt-1">Get personalized content suggestions and strategic advice</p>
      </div>

      {/* Messages Container */}
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
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className={`text-xs mt-2 ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about content strategy, video ideas, scheduling..."
              className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              Send
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
    </div>
  );
}
