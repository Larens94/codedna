import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard,
  Store,
  Wand2,
  Calendar,
  Users,
  Brain,
  Bot,
  Zap,
  DollarSign,
  ArrowRight,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

const Home: React.FC = () => {
  const { user } = useAuth();

  const quickActions = [
    { title: 'Dashboard', description: 'View usage analytics and agent performance', icon: LayoutDashboard, link: '/dashboard', color: 'bg-sky-100 text-sky-600' },
    { title: 'Marketplace', description: 'Browse and rent new AI agents', icon: Store, link: '/marketplace', color: 'bg-green-100 text-green-600' },
    { title: 'Studio', description: 'Configure and chat with your agents', icon: Wand2, link: '/studio', color: 'bg-amber-100 text-amber-600' },
    { title: 'Scheduler', description: 'Schedule automated agent runs', icon: Calendar, link: '/scheduler', color: 'bg-violet-100 text-violet-600' },
    { title: 'Workspace', description: 'Manage team members and permissions', icon: Users, link: '/workspace', color: 'bg-pink-100 text-pink-600' },
    { title: 'Memories', description: 'View and edit agent memory storage', icon: Brain, link: '/memories', color: 'bg-orange-100 text-orange-600' },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12 px-4 bg-white rounded-2xl border border-gray-200 shadow-sm">
        <h1 className="text-4xl font-bold text-gray-900">
          Welcome back, <span className="text-orange-500">{user?.email?.split('@')[0] || 'User'}</span>
        </h1>
        <p className="text-lg text-gray-500 mt-4 max-w-2xl mx-auto">
          Deploy, manage, and scale AI agents with AgentHub. Everything you need to automate workflows and boost productivity.
        </p>
        <div className="mt-8">
          <Link
            to="/marketplace"
            className="inline-flex items-center gap-2 px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-lg transition duration-200"
          >
            Explore Marketplace
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-sky-100 rounded-lg">
              <Bot size={20} className="text-sky-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">12</div>
              <div className="text-sm text-gray-500">Active Agents</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <Zap size={20} className="text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">3</div>
              <div className="text-sm text-gray-500">Running Sessions</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-amber-100 rounded-lg">
              <DollarSign size={20} className="text-amber-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">$45.00</div>
              <div className="text-sm text-gray-500">Monthly Cost</div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {quickActions.map((action, idx) => {
            const Icon = action.icon;
            return (
              <Link
                key={idx}
                to={action.link}
                className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 hover:border-orange-200 hover:shadow-md transition-all duration-200 group"
              >
                <div className="flex items-start gap-4">
                  <div className={`p-2.5 rounded-lg ${action.color} flex-shrink-0`}>
                    <Icon size={18} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 group-hover:text-orange-600 transition">
                      {action.title}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">{action.description}</p>
                  </div>
                </div>
                <div className="mt-4 flex items-center gap-1 text-sm text-orange-500 font-medium">
                  Go to {action.title}
                  <ArrowRight size={14} />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <div className="space-y-1">
          {[
            { agent: 'SEO Optimizer', action: 'Completed daily report', time: '2 hours ago', status: 'success' },
            { agent: 'Customer Support', action: 'Responded to 15 tickets', time: '4 hours ago', status: 'success' },
            { agent: 'Data Analyzer', action: 'Failed to process dataset', time: '6 hours ago', status: 'error' },
            { agent: 'Code Reviewer', action: 'Reviewed PR #124', time: '1 day ago', status: 'success' },
          ].map((activity, idx) => (
            <div key={idx} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
              <div className="flex items-center gap-3">
                {activity.status === 'success'
                  ? <CheckCircle2 size={16} className="text-green-500 flex-shrink-0" />
                  : <XCircle size={16} className="text-red-400 flex-shrink-0" />
                }
                <div>
                  <div className="text-sm font-medium text-gray-900">{activity.agent}</div>
                  <div className="text-xs text-gray-500">{activity.action}</div>
                </div>
              </div>
              <div className="text-xs text-gray-400">{activity.time}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Home;
