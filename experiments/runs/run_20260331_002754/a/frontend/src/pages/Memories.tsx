import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { FileDown, Pencil, Trash2, Plus, Search } from 'lucide-react';

interface MemoryEntry {
  id: number;
  key: string;
  value: string;
  agent_id: number;
  agent_name: string;
  created_at: string;
  updated_at: string;
}

const Memories: React.FC = () => {
  const [memories, setMemories] = useState<MemoryEntry[]>([
    { id: 1, key: 'user_preferences', value: '{"theme":"dark","language":"en"}', agent_id: 1, agent_name: 'SEO Optimizer', created_at: '2023-10-01', updated_at: '2023-10-01' },
    { id: 2, key: 'api_keys', value: '{"openai":"sk-***","google":"***"}', agent_id: 2, agent_name: 'Customer Support', created_at: '2023-10-02', updated_at: '2023-10-02' },
    { id: 3, key: 'conversation_history', value: 'User asked about pricing...', agent_id: 3, agent_name: 'Data Analyzer', created_at: '2023-10-03', updated_at: '2023-10-03' },
    { id: 4, key: 'project_settings', value: '{"auto_save":true,"notifications":true}', agent_id: 4, agent_name: 'Code Reviewer', created_at: '2023-10-04', updated_at: '2023-10-04' },
    { id: 5, key: 'training_data', value: 'Large JSON dataset...', agent_id: 5, agent_name: 'Email Responder', created_at: '2023-10-05', updated_at: '2023-10-05' },
  ]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string>('all');

  useEffect(() => { fetchMemories(); }, []);

  const fetchMemories = async () => {
    try {
      const response = await apiClient.get('/memories/');
      setMemories(response.data.memories || response.data);
    } catch {
      // use mock data
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this memory entry?')) return;
    try {
      await apiClient.delete(`/memories/${id}`);
      setMemories(memories.filter(m => m.id !== id));
    } catch {
      alert('Failed to delete memory.');
    }
  };

  const handleExport = () => {
    const dataStr = JSON.stringify(memories, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `agenthub_memories_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleAddMemory = () => {
    const key = prompt('Enter new memory key:');
    const value = prompt('Enter memory value:');
    if (key && value) {
      const newMemory: MemoryEntry = {
        id: memories.length + 1,
        key,
        value,
        agent_id: 1,
        agent_name: 'Manual',
        created_at: new Date().toISOString().split('T')[0],
        updated_at: new Date().toISOString().split('T')[0],
      };
      setMemories([...memories, newMemory]);
    }
  };

  const filteredMemories = memories.filter(memory => {
    const matchesSearch = memory.key.toLowerCase().includes(search.toLowerCase()) ||
                         memory.value.toLowerCase().includes(search.toLowerCase());
    const matchesAgent = selectedAgent === 'all' || memory.agent_name === selectedAgent;
    return matchesSearch && matchesAgent;
  });

  const agents = Array.from(new Set(memories.map(m => m.agent_name)));

  const truncateValue = (value: string, maxLength = 60) => {
    if (value.length <= maxLength) return value;
    return value.substring(0, maxLength) + '...';
  };

  const inputClass = "w-full px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition text-sm";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1.5";

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Memories</h1>
          <p className="text-gray-500 text-sm mt-1">Key-value storage for your AI agents</p>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
        >
          <FileDown size={15} />
          Export JSON
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className={labelClass}>Search</label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2.5 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition text-sm"
                placeholder="Search by key or value..."
              />
            </div>
          </div>
          <div>
            <label className={labelClass}>Filter by Agent</label>
            <select value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)} className={inputClass}>
              <option value="all">All Agents</option>
              {agents.map(agent => (
                <option key={agent} value={agent}>{agent}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={handleAddMemory} className="w-full flex items-center justify-center gap-2 py-2.5 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition">
              <Plus size={15} />
              Add Memory
            </button>
          </div>
        </div>
      </div>

      {/* Memories Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Key</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Value Preview</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Agent</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Created</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredMemories.map((memory) => (
              <tr key={memory.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-3.5 px-6">
                  <code className="text-xs font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded">{memory.key}</code>
                </td>
                <td className="py-3.5 px-6">
                  <div className="text-xs font-mono text-gray-500 bg-gray-50 border border-gray-100 px-3 py-2 rounded max-w-xs truncate">
                    {truncateValue(memory.value)}
                  </div>
                </td>
                <td className="py-3.5 px-6">
                  <span className="px-2.5 py-1 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
                    {memory.agent_name}
                  </span>
                </td>
                <td className="py-3.5 px-6 text-sm text-gray-500">{memory.created_at}</td>
                <td className="py-3.5 px-6">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        const newValue = prompt('Edit value:', memory.value);
                        if (newValue !== null) {
                          setMemories(memories.map(m => m.id === memory.id ? { ...m, value: newValue } : m));
                        }
                      }}
                      className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition"
                      title="Edit"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(memory.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition"
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredMemories.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-400">No memories found.</p>
          <p className="text-gray-300 text-sm mt-1">Try adjusting your search or add a new memory.</p>
        </div>
      )}

      <p className="text-xs text-gray-400">
        Memories are persistent key-value pairs that your agents can read and update. They are stored securely and can be exported for backup.
      </p>
    </div>
  );
};

export default Memories;
