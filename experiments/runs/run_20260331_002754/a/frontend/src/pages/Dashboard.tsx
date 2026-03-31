import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Bot, Zap, DollarSign, CreditCard } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface UsageData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    borderColor: string;
    backgroundColor: string;
  }[];
}

interface StatCard {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
}

interface AgentRun {
  id: number;
  agent_name: string;
  status: 'completed' | 'failed' | 'running';
  tokens_used: number;
  duration: number;
  created_at: string;
}

const Dashboard: React.FC = () => {
  const [usageData, setUsageData] = useState<UsageData | null>(null);
  const [stats, setStats] = useState<StatCard[]>([
    { title: 'Total Agents', value: 0, icon: Bot, color: 'bg-sky-100 text-sky-600' },
    { title: 'Active Sessions', value: 0, icon: Zap, color: 'bg-green-100 text-green-600' },
    { title: 'Credits Used', value: 0, icon: DollarSign, color: 'bg-yellow-100 text-yellow-600' },
    { title: 'Monthly Cost', value: '$0.00', icon: CreditCard, color: 'bg-amber-100 text-amber-600' },
  ]);
  const [recentRuns, setRecentRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const usageResponse = await apiClient.get('/usage');
      const usage = usageResponse.data;
      const labels = usage.dates || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      const data = usage.tokens || [120, 190, 300, 500, 200, 300, 450];
      setUsageData({
        labels,
        datasets: [
          {
            label: 'Tokens Used',
            data,
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.08)',
          },
        ],
      });
      setStats([
        { title: 'Total Agents', value: usage.total_agents || 12, icon: Bot, color: 'bg-sky-100 text-sky-600' },
        { title: 'Active Sessions', value: usage.active_sessions || 3, icon: Zap, color: 'bg-green-100 text-green-600' },
        { title: 'Credits Used', value: usage.credits_used || 4500, icon: DollarSign, color: 'bg-yellow-100 text-yellow-600' },
        { title: 'Monthly Cost', value: `$${usage.monthly_cost || '45.00'}`, icon: CreditCard, color: 'bg-amber-100 text-amber-600' },
      ]);
      const runsResponse = await apiClient.get('/agent-runs?limit=10');
      setRecentRuns(runsResponse.data.runs || []);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setUsageData({
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
          {
            label: 'Tokens Used',
            data: [120, 190, 300, 500, 200, 300, 450],
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.08)',
          },
        ],
      });
      setRecentRuns([
        { id: 1, agent_name: 'SEO Optimizer', status: 'completed', tokens_used: 1200, duration: 45, created_at: '2023-10-01 14:30' },
        { id: 2, agent_name: 'Customer Support', status: 'running', tokens_used: 800, duration: 20, created_at: '2023-10-01 13:15' },
        { id: 3, agent_name: 'Data Analyzer', status: 'failed', tokens_used: 500, duration: 60, created_at: '2023-10-01 12:00' },
        { id: 4, agent_name: 'Code Reviewer', status: 'completed', tokens_used: 3200, duration: 120, created_at: '2023-09-30 16:45' },
        { id: 5, agent_name: 'Email Responder', status: 'completed', tokens_used: 600, duration: 30, created_at: '2023-09-30 10:20' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { color: '#374151' },
      },
      title: {
        display: true,
        text: 'Token Usage (Last 7 Days)',
        color: '#111827',
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: { color: '#6b7280' },
      },
      y: {
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: { color: '#6b7280' },
      },
    },
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-700';
      case 'running': return 'bg-sky-100 text-sky-700';
      case 'failed': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Overview of your AI agents and usage</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div key={idx} className="bg-white rounded-xl p-5 shadow-sm border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{stat.title}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.color}`}>
                  <Icon size={20} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Token Usage Chart */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Token Usage</h2>
        <div className="h-72">
          {usageData && <Line options={options} data={usageData} />}
        </div>
      </div>

      {/* Recent Agent Runs */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Recent Agent Runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Agent</th>
                <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Tokens</th>
                <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Duration</th>
                <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Time</th>
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run) => (
                <tr key={run.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-3 px-6 text-sm font-medium text-gray-900">{run.agent_name}</td>
                  <td className="py-3 px-6">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(run.status)}`}>
                      {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                    </span>
                  </td>
                  <td className="py-3 px-6 text-sm text-gray-600">{run.tokens_used.toLocaleString()}</td>
                  <td className="py-3 px-6 text-sm text-gray-600">{run.duration}s</td>
                  <td className="py-3 px-6 text-sm text-gray-400">{run.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
