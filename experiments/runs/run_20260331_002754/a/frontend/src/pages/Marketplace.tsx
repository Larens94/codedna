import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Star } from 'lucide-react';

interface Agent {
  id: number;
  name: string;
  description: string;
  category: string;
  pricing_tier: 'free' | 'basic' | 'pro' | 'enterprise';
  monthly_price: number;
  rating: number;
  is_public: boolean;
  created_at: string;
}

const Marketplace: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  const categories = ['All', 'SEO', 'Support', 'Data', 'Code', 'Email', 'Research'];

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/agents/?is_public=true');
      setAgents(response.data.agents || response.data);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      setError('Failed to load marketplace. Showing demo agents.');
      setAgents([
        { id: 1, name: 'SEO Optimizer Pro', description: 'Automatically optimizes your website for search engines, suggests keywords, and analyzes competitors.', category: 'SEO', pricing_tier: 'pro', monthly_price: 49, rating: 4.8, is_public: true, created_at: '2023-09-01' },
        { id: 2, name: 'Customer Support Agent', description: 'Handles customer inquiries, provides instant responses, and escalates complex issues.', category: 'Support', pricing_tier: 'basic', monthly_price: 29, rating: 4.5, is_public: true, created_at: '2023-09-05' },
        { id: 3, name: 'Data Analyzer', description: 'Processes large datasets, generates insights, and creates visual reports.', category: 'Data', pricing_tier: 'pro', monthly_price: 79, rating: 4.9, is_public: true, created_at: '2023-08-20' },
        { id: 4, name: 'Code Reviewer', description: 'Reviews your code for bugs, security vulnerabilities, and best practices.', category: 'Code', pricing_tier: 'enterprise', monthly_price: 199, rating: 4.7, is_public: true, created_at: '2023-09-10' },
        { id: 5, name: 'Email Responder', description: 'Automatically drafts and sends personalized email responses.', category: 'Email', pricing_tier: 'free', monthly_price: 0, rating: 4.2, is_public: true, created_at: '2023-08-15' },
        { id: 6, name: 'Research Assistant', description: 'Gathers information from the web, summarizes articles, and provides citations.', category: 'Research', pricing_tier: 'basic', monthly_price: 35, rating: 4.6, is_public: true, created_at: '2023-09-12' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const filteredAgents = selectedCategory === 'All'
    ? agents
    : agents.filter(agent => agent.category === selectedCategory);

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'free': return 'bg-green-100 text-green-700';
      case 'basic': return 'bg-sky-100 text-sky-700';
      case 'pro': return 'bg-amber-100 text-amber-700';
      case 'enterprise': return 'bg-violet-100 text-violet-700';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const handleRentAgent = (agentId: number) => {
    alert(`Renting agent ${agentId} - this would trigger a rental workflow.`);
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
        <h1 className="text-2xl font-bold text-gray-900">Agent Marketplace</h1>
        <p className="text-gray-500 text-sm mt-1">Browse and rent AI agents for your needs</p>
      </div>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800 text-sm">
          {error}
        </div>
      )}

      {/* Category Filters */}
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              selectedCategory === cat
                ? 'bg-orange-500 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:border-orange-300 hover:text-orange-600'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredAgents.map((agent) => (
          <div key={agent.id} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 flex flex-col">
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="font-semibold text-gray-900">{agent.name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTierBadge(agent.pricing_tier)}`}>
                    {agent.pricing_tier.toUpperCase()}
                  </span>
                  <span className="text-xs text-gray-400">{agent.category}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xl font-bold text-gray-900">
                  {agent.monthly_price === 0 ? 'Free' : `$${agent.monthly_price}`}
                </div>
                {agent.monthly_price > 0 && <div className="text-xs text-gray-400">/month</div>}
              </div>
            </div>

            <p className="text-sm text-gray-500 flex-grow">{agent.description}</p>

            <div className="flex items-center justify-between mt-5 pt-4 border-t border-gray-100">
              <div className="flex items-center gap-1">
                <Star size={14} className="text-amber-400 fill-amber-400" />
                <span className="text-sm font-medium text-gray-700">{agent.rating}</span>
                <span className="text-xs text-gray-400">/5</span>
              </div>
              <button
                onClick={() => handleRentAgent(agent.id)}
                className="px-4 py-1.5 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition duration-200"
              >
                Rent Agent
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredAgents.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-400">No agents found in this category.</p>
        </div>
      )}
    </div>
  );
};

export default Marketplace;
