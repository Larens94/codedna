import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Download } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface Invoice {
  id: string;
  date: string;
  amount: number;
  status: 'paid' | 'pending' | 'overdue';
  download_url: string;
}

interface BillingData {
  plan: string;
  credits_used: number;
  credits_total: number;
  monthly_cost: number;
  next_billing_date: string;
  usage: { date: string; tokens: number; cost: number }[];
  invoices: Invoice[];
}

const Billing: React.FC = () => {
  const [billingData, setBillingData] = useState<BillingData>({
    plan: 'Pro',
    credits_used: 4500,
    credits_total: 10000,
    monthly_cost: 45.00,
    next_billing_date: '2023-11-01',
    usage: [
      { date: '2023-10-01', tokens: 1200, cost: 5.40 },
      { date: '2023-10-02', tokens: 1900, cost: 8.55 },
      { date: '2023-10-03', tokens: 3000, cost: 13.50 },
      { date: '2023-10-04', tokens: 2500, cost: 11.25 },
      { date: '2023-10-05', tokens: 1800, cost: 8.10 },
      { date: '2023-10-06', tokens: 2200, cost: 9.90 },
      { date: '2023-10-07', tokens: 3200, cost: 14.40 },
    ],
    invoices: [
      { id: 'INV-2023-10', date: '2023-10-01', amount: 45.00, status: 'paid', download_url: '#' },
      { id: 'INV-2023-09', date: '2023-09-01', amount: 45.00, status: 'paid', download_url: '#' },
      { id: 'INV-2023-08', date: '2023-08-01', amount: 45.00, status: 'paid', download_url: '#' },
      { id: 'INV-2023-07', date: '2023-07-01', amount: 45.00, status: 'paid', download_url: '#' },
    ],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchBillingData(); }, []);

  const fetchBillingData = async () => {
    try {
      const response = await apiClient.get('/billing/');
      setBillingData(response.data);
    } catch {
      // use mock data
    } finally {
      setLoading(false);
    }
  };

  const creditsPercentage = (billingData.credits_used / billingData.credits_total) * 100;

  const chartData = {
    labels: billingData.usage.map(u => u.date.split('-').slice(1).join('/')),
    datasets: [
      {
        label: 'Tokens Used',
        data: billingData.usage.map(u => u.tokens),
        backgroundColor: 'rgba(249, 115, 22, 0.7)',
        borderColor: '#f97316',
        borderWidth: 1,
      },
      {
        label: 'Cost ($)',
        data: billingData.usage.map(u => u.cost),
        backgroundColor: 'rgba(59, 130, 246, 0.6)',
        borderColor: '#3b82f6',
        borderWidth: 1,
        yAxisID: 'y1',
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#374151' } },
      title: { display: true, text: 'Daily Usage & Cost (Last 7 Days)', color: '#111827' },
    },
    scales: {
      x: {
        grid: { color: 'rgba(0,0,0,0.05)' },
        ticks: { color: '#6b7280' },
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        grid: { color: 'rgba(0,0,0,0.05)' },
        ticks: { color: '#6b7280' },
        title: { display: true, text: 'Tokens', color: '#6b7280' },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: { drawOnChartArea: false },
        ticks: { color: '#6b7280' },
        title: { display: true, text: 'Cost ($)', color: '#6b7280' },
      },
    },
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'paid': return 'bg-green-100 text-green-700';
      case 'pending': return 'bg-yellow-100 text-yellow-700';
      case 'overdue': return 'bg-red-100 text-red-700';
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
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="text-gray-500 text-sm mt-1">Manage your subscription and view usage</p>
      </div>

      {/* Current Plan + Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Current Plan</h2>
          <div className="flex items-center justify-between mb-5">
            <div>
              <div className="text-2xl font-bold text-gray-900">{billingData.plan} Plan</div>
              <div className="text-sm text-gray-500 mt-0.5">${billingData.monthly_cost}/month</div>
            </div>
            <button className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition">
              Upgrade Plan
            </button>
          </div>

          <div className="mb-3">
            <div className="flex justify-between text-sm text-gray-600 mb-1.5">
              <span>Credits Used</span>
              <span>{billingData.credits_used.toLocaleString()} / {billingData.credits_total.toLocaleString()} ({creditsPercentage.toFixed(1)}%)</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2.5">
              <div className="bg-orange-500 h-2.5 rounded-full transition-all duration-500" style={{ width: `${Math.min(creditsPercentage, 100)}%` }}></div>
            </div>
          </div>

          <p className="text-sm text-gray-400">
            Next billing: <span className="text-gray-700 font-medium">{new Date(billingData.next_billing_date).toLocaleDateString()}</span>
          </p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Summary</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Monthly Plan</span>
              <span className="font-medium text-gray-900">${billingData.monthly_cost}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Overage</span>
              <span className="font-medium text-gray-900">$0.00</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Tax</span>
              <span className="font-medium text-gray-900">$0.00</span>
            </div>
            <div className="border-t border-gray-100 pt-3 flex justify-between text-base font-semibold">
              <span className="text-gray-900">Total</span>
              <span className="text-gray-900">${billingData.monthly_cost}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Usage Chart */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Usage Overview</h2>
        <div className="h-72">
          <Bar options={chartOptions} data={chartData} />
        </div>
      </div>

      {/* Invoices */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Invoice History</h2>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Invoice</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Date</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Amount</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">PDF</th>
            </tr>
          </thead>
          <tbody>
            {billingData.invoices.map((invoice) => (
              <tr key={invoice.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-3.5 px-6 text-sm font-mono text-gray-700">{invoice.id}</td>
                <td className="py-3.5 px-6 text-sm text-gray-600">{invoice.date}</td>
                <td className="py-3.5 px-6 text-sm font-medium text-gray-900">${invoice.amount.toFixed(2)}</td>
                <td className="py-3.5 px-6">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(invoice.status)}`}>
                    {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                  </span>
                </td>
                <td className="py-3.5 px-6">
                  <button
                    onClick={() => window.open(invoice.download_url, '_blank')}
                    className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-orange-600 transition"
                  >
                    <Download size={14} />
                    Download
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Billing;
