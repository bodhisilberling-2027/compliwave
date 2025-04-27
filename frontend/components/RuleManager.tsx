import React, { useState, useEffect } from 'react';
import { useUser } from '@clerk/nextjs';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { secureApiRequest } from '../utils/security';
import { ComplianceRule } from '../types';

export default function RuleManager() {
  const { user } = useUser();
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState<string | null>(null);
  const [formData, setFormData] = useState<Omit<ComplianceRule, 'id' | 'created_at' | 'updated_at' | 'created_by' | 'organization_id'>>({
    name: '',
    description: '',
    pattern: '',
    severity: 'medium',
    is_active: true
  });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const response = await secureApiRequest(
        `${process.env.NEXT_PUBLIC_API_URL}/rules`,
        {
          headers: {
            'Authorization': `Bearer ${await user?.getToken()}`
          }
        }
      );
      const data = await response.json();
      setRules(data);
    } catch (err) {
      setError('Failed to fetch rules');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const url = isEditing
        ? `${process.env.NEXT_PUBLIC_API_URL}/rules/${isEditing}`
        : `${process.env.NEXT_PUBLIC_API_URL}/rules`;
      
      const response = await secureApiRequest(url, {
        method: isEditing ? 'PUT' : 'POST',
        headers: {
          'Authorization': `Bearer ${await user?.getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        await fetchRules();
        resetForm();
      }
    } catch (err) {
      setError('Failed to save rule');
      console.error('Save error:', err);
    }
  };

  const handleDelete = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    try {
      const response = await secureApiRequest(
        `${process.env.NEXT_PUBLIC_API_URL}/rules/${ruleId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${await user?.getToken()}`
          }
        }
      );

      if (response.ok) {
        await fetchRules();
      }
    } catch (err) {
      setError('Failed to delete rule');
      console.error('Delete error:', err);
    }
  };

  const handleEdit = (rule: ComplianceRule) => {
    setIsEditing(rule.id);
    setFormData({
      name: rule.name,
      description: rule.description,
      pattern: rule.pattern,
      severity: rule.severity,
      is_active: rule.is_active
    });
  };

  const resetForm = () => {
    setIsCreating(false);
    setIsEditing(null);
    setFormData({
      name: '',
      description: '',
      pattern: '',
      severity: 'medium',
      is_active: true
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Compliance Rules</h2>
        <button
          onClick={() => setIsCreating(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          New Rule
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {(isCreating || isEditing) && (
        <form onSubmit={handleSubmit} className="space-y-4 bg-white p-6 rounded-lg shadow">
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
              rows={3}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Pattern (Regex)</label>
            <input
              type="text"
              value={formData.pattern}
              onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Severity</label>
            <select
              value={formData.severity}
              onChange={(e) => setFormData({ ...formData, severity: e.target.value as 'low' | 'medium' | 'high' })}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="h-4 w-4 text-blue-600 border-gray-300 rounded"
            />
            <label className="ml-2 block text-sm text-gray-700">Active</label>
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={resetForm}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              {isEditing ? 'Update' : 'Create'} Rule
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {rules.map((rule) => (
            <li key={rule.id} className="px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{rule.name}</h3>
                  <p className="mt-1 text-sm text-gray-500">{rule.description}</p>
                  <div className="mt-2 flex items-center space-x-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                      ${rule.severity === 'high' ? 'bg-red-100 text-red-800' :
                        rule.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'}`}>
                      {rule.severity}
                    </span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                      ${rule.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {rule.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleEdit(rule)}
                    className="p-2 text-gray-400 hover:text-gray-500"
                  >
                    <PencilIcon className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    className="p-2 text-gray-400 hover:text-red-500"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
} 