import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { Send, Settings2 } from 'lucide-react';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface AgentConfig {
  name: string;
  systemPrompt: string;
  model: string;
  tools: string[];
  temperature: number;
}

const Studio: React.FC = () => {
  const [config, setConfig] = useState<AgentConfig>({
    name: 'My Agent',
    systemPrompt: 'You are a helpful AI assistant.',
    model: 'gpt-4',
    tools: ['web_search', 'calculator', 'file_reader'],
    temperature: 0.7,
  });
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, role: 'assistant', content: 'Hello! I am your AI agent. How can I help you today?', timestamp: new Date() },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [agentId, setAgentId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const models = ['gpt-4', 'gpt-3.5-turbo', 'claude-3', 'llama-3', 'gemini-pro'];
  const availableTools = ['web_search', 'calculator', 'file_reader', 'code_executor', 'database', 'email_sender'];

  useEffect(() => { createAgentSession(); }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const createAgentSession = async () => {
    try {
      const response = await apiClient.post('/agents/', {
        name: config.name,
        system_prompt: config.systemPrompt,
        model: config.model,
      });
      setAgentId(response.data.id);
    } catch {
      setAgentId(123);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMessage: Message = { id: messages.length + 1, role: 'user', content: input, timestamp: new Date() };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);
    setStreaming(true);

    const assistantMessage: Message = { id: messages.length + 2, role: 'assistant', content: '', timestamp: new Date() };
    setMessages(prev => [...prev, assistantMessage]);

    const responses = [
      "I'm processing your request...",
      "Let me think about that...",
      "Here's what I found: Based on your query, I can provide the following information...",
    ];
    let accumulated = '';
    for (const chunk of responses) {
      await new Promise(resolve => setTimeout(resolve, 200));
      accumulated += chunk + ' ';
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessage.id ? { ...msg, content: accumulated } : msg
      ));
    }
    setLoading(false);
    setStreaming(false);
  };

  const handleConfigChange = (field: keyof AgentConfig, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  const handleToolToggle = (tool: string) => {
    setConfig(prev => ({
      ...prev,
      tools: prev.tools.includes(tool)
        ? prev.tools.filter(t => t !== tool)
        : [...prev.tools, tool],
    }));
  };

  const handleSaveAgent = async () => {
    try {
      await apiClient.put(`/agents/${agentId}`, config);
      alert('Agent configuration saved!');
    } catch {
      alert('Failed to save agent.');
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition text-sm";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1.5";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agent Studio</h1>
        <p className="text-gray-500 text-sm mt-1">Configure and interact with your AI agent</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration panel */}
        <div className="lg:col-span-1 bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="flex items-center gap-2 mb-5">
            <Settings2 size={16} className="text-gray-500" />
            <h2 className="text-base font-semibold text-gray-900">Configuration</h2>
          </div>

          <div className="space-y-5">
            <div>
              <label className={labelClass}>Agent Name</label>
              <input type="text" value={config.name} onChange={(e) => handleConfigChange('name', e.target.value)} className={inputClass} placeholder="My Agent" />
            </div>

            <div>
              <label className={labelClass}>System Prompt</label>
              <textarea value={config.systemPrompt} onChange={(e) => handleConfigChange('systemPrompt', e.target.value)} rows={5} className={inputClass} placeholder="Define the agent's personality and capabilities..." />
            </div>

            <div>
              <label className={labelClass}>Model</label>
              <select value={config.model} onChange={(e) => handleConfigChange('model', e.target.value)} className={inputClass}>
                {models.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Temperature: {config.temperature}</label>
              <input type="range" min="0" max="1" step="0.1" value={config.temperature} onChange={(e) => handleConfigChange('temperature', parseFloat(e.target.value))} className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500" />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Precise</span><span>Creative</span>
              </div>
            </div>

            <div>
              <label className={labelClass}>Enabled Tools</label>
              <div className="space-y-2">
                {availableTools.map(tool => (
                  <label key={tool} className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={config.tools.includes(tool)} onChange={() => handleToolToggle(tool)} className="w-4 h-4 text-orange-500 border-gray-300 rounded focus:ring-orange-500" />
                    <span className="text-sm text-gray-600 capitalize">{tool.replace('_', ' ')}</span>
                  </label>
                ))}
              </div>
            </div>

            <button onClick={handleSaveAgent} className="w-full py-2.5 px-4 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-lg transition duration-200 text-sm">
              Save Configuration
            </button>
          </div>
        </div>

        {/* Chat panel */}
        <div className="lg:col-span-2 bg-white rounded-xl p-6 shadow-sm border border-gray-200 flex flex-col">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Chat Console</h2>

          <div className="flex-1 overflow-y-auto mb-4 space-y-3 max-h-[500px] px-1">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                  message.role === 'user'
                    ? 'bg-orange-500 text-white'
                    : message.role === 'assistant'
                    ? 'bg-gray-100 text-gray-900'
                    : 'bg-gray-50 text-gray-600 border border-gray-200'
                }`}>
                  <div className="font-medium text-xs mb-1 opacity-70">
                    {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'Agent' : 'System'}
                  </div>
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <div className="text-xs opacity-50 mt-1.5">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}
            {streaming && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-xl px-4 py-3">
                  <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse"></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse delay-150"></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse delay-300"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={loading}
              placeholder="Type your message..."
              className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition disabled:opacity-50 text-sm"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-200 text-white rounded-lg transition duration-200"
            >
              <Send size={16} />
            </button>
          </div>

          <div className="mt-3 text-xs text-gray-400">
            Agent ID: {agentId || 'Creating...'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Studio;
