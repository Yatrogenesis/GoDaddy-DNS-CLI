import React, { useState } from 'react';
import { Pencil, Trash2, Plus, RefreshCw } from 'lucide-react';
import type { DNSRecord } from '@/types/api';
import { formatDistanceToNow } from 'date-fns';

interface DNSRecordTableProps {
  records: DNSRecord[];
  loading: boolean;
  onEdit: (record: DNSRecord) => void;
  onDelete: (record: DNSRecord) => void;
  onAdd: () => void;
  onRefresh: () => void;
}

const getRecordTypeColor = (type: string): string => {
  const colors: Record<string, string> = {
    A: 'bg-blue-100 text-blue-800',
    AAAA: 'bg-indigo-100 text-indigo-800',
    CNAME: 'bg-green-100 text-green-800',
    MX: 'bg-purple-100 text-purple-800',
    TXT: 'bg-yellow-100 text-yellow-800',
    SRV: 'bg-pink-100 text-pink-800',
    NS: 'bg-gray-100 text-gray-800',
    CAA: 'bg-red-100 text-red-800',
  };
  return colors[type] || 'bg-gray-100 text-gray-800';
};

const formatTTL = (ttl: number): string => {
  if (ttl < 60) return `${ttl}s`;
  if (ttl < 3600) return `${Math.floor(ttl / 60)}m`;
  if (ttl < 86400) return `${Math.floor(ttl / 3600)}h`;
  return `${Math.floor(ttl / 86400)}d`;
};

export const DNSRecordTable: React.FC<DNSRecordTableProps> = ({
  records,
  loading,
  onEdit,
  onDelete,
  onAdd,
  onRefresh,
}) => {
  const [sortField, setSortField] = useState<keyof DNSRecord>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filterType, setFilterType] = useState<string>('');

  const handleSort = (field: keyof DNSRecord) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredRecords = records.filter(record =>
    filterType === '' || record.type === filterType
  );

  const sortedRecords = [...filteredRecords].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortDirection === 'asc'
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }

    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
    }

    return 0;
  });

  const recordTypes = [...new Set(records.map(r => r.type))].sort();

  return (
    <div className="bg-white shadow-lg rounded-lg overflow-hidden">
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-medium text-gray-900">DNS Records</h3>
            <span className="text-sm text-gray-500">
              {filteredRecords.length} of {records.length} records
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Types</option>
              {recordTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onAdd}
              className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Record
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-500">Loading records...</p>
        </div>
      ) : sortedRecords.length === 0 ? (
        <div className="p-8 text-center">
          <p className="text-gray-500">
            {filterType ? `No ${filterType} records found` : 'No DNS records found'}
          </p>
          <button
            onClick={onAdd}
            className="mt-2 text-blue-600 hover:text-blue-800"
          >
            Add your first record
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[
                  { key: 'name', label: 'Name' },
                  { key: 'type', label: 'Type' },
                  { key: 'data', label: 'Value' },
                  { key: 'ttl', label: 'TTL' },
                ].map(({ key, label }) => (
                  <th
                    key={key}
                    onClick={() => handleSort(key as keyof DNSRecord)}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    <div className="flex items-center space-x-1">
                      <span>{label}</span>
                      {sortField === key && (
                        <span className="text-blue-600">
                          {sortDirection === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Priority
                </th>
                <th className="relative px-6 py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedRecords.map((record, index) => (
                <tr key={`${record.name}-${record.type}-${index}`} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className="font-mono">{record.name || '@'}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRecordTypeColor(record.type)}`}>
                      {record.type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    <div className="max-w-xs truncate font-mono" title={record.data}>
                      {record.data}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span className="font-mono">{formatTTL(record.ttl)}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {record.priority || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => onEdit(record)}
                        className="text-blue-600 hover:text-blue-900 p-1"
                        title="Edit record"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => onDelete(record)}
                        className="text-red-600 hover:text-red-900 p-1"
                        title="Delete record"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};