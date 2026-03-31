import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Plus, Pause, Play, Trash2 } from 'lucide-react';

interface ScheduledTask {
  id: number;
  name: string;
  description: string;
  agent_id: number;
  agent_name: string;
  cron_expression: string;
  next_run: string;
  last_run: string | null;
  status: 'active' | 'paused' | 'failed';
  created_at: string;
}

interface Agent {
  id: number;
  name: string;
}

const Scheduler: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newTask, setNewTask] = useState({
    name: '',
    description: '',
    agent_id: '',
    cron_expression: '0 9 * * *',
    status: 'active' as 'active' | 'paused',
  });

  useEffect(() => {
    fetchTasks();
    fetchAgents();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await apiClient.get('/tasks/');
      setTasks(response.data.tasks || response.data);
    } catch {
      setTasks([
        { id: 1, name: 'Daily SEO Report', description: 'Generates daily SEO performance report', agent_id: 1, agent_name: 'SEO Optimizer', cron_expression: '0 9 * * *', next_run: '2023-10-02 09:00:00', last_run: '2023-10-01 09:00:00', status: 'active', created_at: '2023-09-20' },
        { id: 2, name: 'Weekly Data Backup', description: 'Backs up agent data to cloud storage', agent_id: 3, agent_name: 'Data Analyzer', cron_expression: '0 2 * * 0', next_run: '2023-10-08 02:00:00', last_run: '2023-10-01 02:00:00', status: 'active', created_at: '2023-09-18' },
        { id: 3, name: 'Customer Support Check', description: 'Checks for unresolved support tickets', agent_id: 2, agent_name: 'Customer Support Agent', cron_expression: '*/30 * * * *', next_run: '2023-10-01 14:30:00', last_run: '2023-10-01 14:00:00', status: 'paused', created_at: '2023-09-25' },
        { id: 4, name: 'Monthly Billing Report', description: 'Generates monthly billing summary', agent_id: 5, agent_name: 'Email Responder', cron_expression: '0 0 1 * *', next_run: '2023-11-01 00:00:00', last_run: '2023-10-01 00:00:00', status: 'failed', created_at: '2023-09-15' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      const response = await apiClient.get('/agents/');
      setAgents(response.data.agents || response.data);
    } catch {
      setAgents([
        { id: 1, name: 'SEO Optimizer' },
        { id: 2, name: 'Customer Support Agent' },
        { id: 3, name: 'Data Analyzer' },
        { id: 4, name: 'Code Reviewer' },
        { id: 5, name: 'Email Responder' },
      ]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setNewTask(prev => ({ ...prev, [name]: value }));
  };

  const handleCreateTask = async () => {
    try {
      await apiClient.post('/tasks/', { ...newTask, agent_id: parseInt(newTask.agent_id) });
      setShowModal(false);
      setNewTask({ name: '', description: '', agent_id: '', cron_expression: '0 9 * * *', status: 'active' });
      fetchTasks();
    } catch {
      alert('Failed to create task. Please try again.');
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      await apiClient.delete(`/tasks/${taskId}`);
      fetchTasks();
    } catch {
      alert('Failed to delete task.');
    }
  };

  const handleToggleStatus = async (taskId: number, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';
    try {
      await apiClient.patch(`/tasks/${taskId}`, { status: newStatus });
      fetchTasks();
    } catch {
      console.error('Failed to update task status');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-700';
      case 'paused': return 'bg-yellow-100 text-yellow-700';
      case 'failed': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-600';
    }
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
          <h1 className="text-2xl font-bold text-gray-900">Task Scheduler</h1>
          <p className="text-gray-500 text-sm mt-1">Schedule automated agent runs with cron expressions</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition duration-200"
        >
          <Plus size={16} />
          New Task
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Task</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Agent</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Schedule</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Next Run</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-4 px-6">
                  <div className="text-sm font-medium text-gray-900">{task.name}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{task.description}</div>
                </td>
                <td className="py-4 px-6 text-sm text-gray-600">{task.agent_name}</td>
                <td className="py-4 px-6">
                  <code className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">{task.cron_expression}</code>
                </td>
                <td className="py-4 px-6 text-sm text-gray-500">{new Date(task.next_run).toLocaleString()}</td>
                <td className="py-4 px-6">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(task.status)}`}>
                    {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                  </span>
                </td>
                <td className="py-4 px-6">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleStatus(task.id, task.status)}
                      className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition"
                      title={task.status === 'active' ? 'Pause' : 'Activate'}
                    >
                      {task.status === 'active' ? <Pause size={15} /> : <Play size={15} />}
                    </button>
                    <button
                      onClick={() => handleDeleteTask(task.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition"
                      title="Delete"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* New Task Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl w-full max-w-lg p-6 shadow-xl">
            <h2 className="text-lg font-bold text-gray-900 mb-5">Schedule New Task</h2>

            <div className="space-y-4">
              <div>
                <label className={labelClass}>Task Name</label>
                <input type="text" name="name" value={newTask.name} onChange={handleInputChange} className={inputClass} placeholder="Daily Report" />
              </div>
              <div>
                <label className={labelClass}>Description</label>
                <textarea name="description" value={newTask.description} onChange={handleInputChange} rows={2} className={inputClass} placeholder="What does this task do?" />
              </div>
              <div>
                <label className={labelClass}>Agent</label>
                <select name="agent_id" value={newTask.agent_id} onChange={handleInputChange} className={inputClass}>
                  <option value="">Select an agent</option>
                  {agents.map(agent => (
                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>
                  Cron Expression
                  <span className="ml-2 text-gray-400 text-xs font-normal">(e.g., 0 9 * * * for daily at 9 AM)</span>
                </label>
                <input type="text" name="cron_expression" value={newTask.cron_expression} onChange={handleInputChange} className={inputClass} placeholder="0 9 * * *" />
              </div>
              <div>
                <label className={labelClass}>Initial Status</label>
                <select name="status" value={newTask.status} onChange={handleInputChange} className={inputClass}>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">
                Cancel
              </button>
              <button onClick={handleCreateTask} className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-lg transition">
                Create Task
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Scheduler;
