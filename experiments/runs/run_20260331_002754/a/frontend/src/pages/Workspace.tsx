import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { UserX } from 'lucide-react';

interface WorkspaceMember {
  id: number;
  email: string;
  role: 'admin' | 'member' | 'viewer';
  joined_at: string;
  is_active: boolean;
}

const Workspace: React.FC = () => {
  const [workspaceName, setWorkspaceName] = useState('My Workspace');
  const [members, setMembers] = useState<WorkspaceMember[]>([
    { id: 1, email: 'admin@example.com', role: 'admin', joined_at: '2023-09-01', is_active: true },
    { id: 2, email: 'member1@example.com', role: 'member', joined_at: '2023-09-05', is_active: true },
    { id: 3, email: 'member2@example.com', role: 'member', joined_at: '2023-09-10', is_active: true },
    { id: 4, email: 'viewer@example.com', role: 'viewer', joined_at: '2023-09-15', is_active: false },
  ]);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState<'admin' | 'member' | 'viewer'>('member');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { fetchWorkspaceData(); }, []);

  const fetchWorkspaceData = async () => {
    try {
      const response = await apiClient.get('/workspace/');
      setWorkspaceName(response.data.name || 'My Workspace');
      setMembers(response.data.members || []);
    } catch {
      // use mock data
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemberEmail.trim()) return;
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/workspace/invite', { email: newMemberEmail, role: newMemberRole });
      const newMember: WorkspaceMember = {
        id: members.length + 1,
        email: newMemberEmail,
        role: newMemberRole,
        joined_at: new Date().toISOString().split('T')[0],
        is_active: false,
      };
      setMembers([...members, newMember]);
      setNewMemberEmail('');
      setNewMemberRole('member');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to invite member.');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    if (!confirm('Remove this member?')) return;
    try {
      await apiClient.delete(`/workspace/members/${memberId}`);
      setMembers(members.filter(m => m.id !== memberId));
    } catch {
      alert('Failed to remove member.');
    }
  };

  const handleUpdateRole = async (memberId: number, newRole: string) => {
    try {
      await apiClient.patch(`/workspace/members/${memberId}`, { role: newRole });
      setMembers(members.map(m => m.id === memberId ? { ...m, role: newRole as any } : m));
    } catch {
      console.error('Failed to update role');
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-sky-100 text-sky-700';
      case 'member': return 'bg-green-100 text-green-700';
      case 'viewer': return 'bg-gray-100 text-gray-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const inputClass = "w-full px-4 py-2.5 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition text-sm";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1.5";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Workspace</h1>
        <p className="text-gray-500 text-sm mt-1">Manage your organization and team members</p>
      </div>

      {/* Workspace Info */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">{workspaceName}</h2>
            <p className="text-sm text-gray-400 mt-0.5">{members.length} members</p>
          </div>
          <button
            onClick={() => {
              const newName = prompt('Enter new workspace name:', workspaceName);
              if (newName) setWorkspaceName(newName);
            }}
            className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
          >
            Rename
          </button>
        </div>
      </div>

      {/* Invite Form */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Invite Team Member</h2>
        <form onSubmit={handleInviteMember} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Email Address</label>
              <input type="email" value={newMemberEmail} onChange={(e) => setNewMemberEmail(e.target.value)} className={inputClass} placeholder="colleague@example.com" required />
            </div>
            <div>
              <label className={labelClass}>Role</label>
              <select value={newMemberRole} onChange={(e) => setNewMemberRole(e.target.value as any)} className={inputClass}>
                <option value="admin">Admin</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <div className="flex items-end">
              <button type="submit" disabled={loading} className="w-full py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white text-sm font-semibold rounded-lg transition">
                {loading ? 'Sending...' : 'Send Invitation'}
              </button>
            </div>
          </div>
          <div className="text-xs text-gray-400 space-y-0.5">
            <p><span className="font-medium text-gray-600">Admin:</span> Full access to all features and billing.</p>
            <p><span className="font-medium text-gray-600">Member:</span> Can create and manage agents, but not billing.</p>
            <p><span className="font-medium text-gray-600">Viewer:</span> Read-only access to agents and analytics.</p>
          </div>
        </form>
      </div>

      {/* Members Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Team Members</h2>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Email</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Role</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Joined</th>
              <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-3.5 px-6 text-sm text-gray-900">{member.email}</td>
                <td className="py-3.5 px-6">
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getRoleBadge(member.role)}`}>
                      {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                    </span>
                    <select
                      value={member.role}
                      onChange={(e) => handleUpdateRole(member.id, e.target.value)}
                      className="bg-gray-50 border border-gray-200 text-gray-600 text-xs rounded-md px-2 py-1 focus:ring-1 focus:ring-orange-500"
                    >
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  </div>
                </td>
                <td className="py-3.5 px-6">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${member.is_active ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                    {member.is_active ? 'Active' : 'Pending'}
                  </span>
                </td>
                <td className="py-3.5 px-6 text-sm text-gray-500">{member.joined_at}</td>
                <td className="py-3.5 px-6">
                  <button
                    onClick={() => handleRemoveMember(member.id)}
                    className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition"
                    title="Remove member"
                  >
                    <UserX size={15} />
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

export default Workspace;
