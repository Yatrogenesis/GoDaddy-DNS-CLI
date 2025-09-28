import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { Globe, Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import apiClient from '@/utils/api';
import { DNSRecordTable } from '@/components/DNSRecordTable';
import { DNSRecordForm } from '@/components/DNSRecordForm';
import type { DNSRecord, Domain, CreateRecordRequest, ValidationResult } from '@/types/api';

export const Dashboard: React.FC = () => {
  const [selectedDomain, setSelectedDomain] = useState<string>('');
  const [showRecordForm, setShowRecordForm] = useState(false);
  const [editingRecord, setEditingRecord] = useState<DNSRecord | undefined>();
  const queryClient = useQueryClient();

  // Fetch domains
  const { data: domains = [], isLoading: domainsLoading } = useQuery({
    queryKey: ['domains'],
    queryFn: () => apiClient.getDomains().then(res => res.data),
  });

  // Fetch DNS records for selected domain
  const { data: records = [], isLoading: recordsLoading, refetch: refetchRecords } = useQuery({
    queryKey: ['dns-records', selectedDomain],
    queryFn: () => selectedDomain ? apiClient.getDNSRecords(selectedDomain).then(res => res.data) : Promise.resolve([]),
    enabled: !!selectedDomain,
  });

  // Fetch validation for selected domain
  const { data: validation } = useQuery({
    queryKey: ['domain-validation', selectedDomain],
    queryFn: () => selectedDomain ? apiClient.validateDomain(selectedDomain).then(res => res.data) : Promise.resolve(null),
    enabled: !!selectedDomain,
  });

  // Create DNS record mutation
  const createRecordMutation = useMutation({
    mutationFn: (data: CreateRecordRequest) => apiClient.createDNSRecord(selectedDomain, data),
    onSuccess: () => {
      toast.success('DNS record created successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] });
      queryClient.invalidateQueries({ queryKey: ['domain-validation', selectedDomain] });
      setShowRecordForm(false);
      setEditingRecord(undefined);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create DNS record');
    },
  });

  // Update DNS record mutation
  const updateRecordMutation = useMutation({
    mutationFn: ({ record, data }: { record: DNSRecord; data: CreateRecordRequest }) =>
      apiClient.updateDNSRecord(selectedDomain, record.type, record.name, data),
    onSuccess: () => {
      toast.success('DNS record updated successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] });
      queryClient.invalidateQueries({ queryKey: ['domain-validation', selectedDomain] });
      setShowRecordForm(false);
      setEditingRecord(undefined);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update DNS record');
    },
  });

  // Delete DNS record mutation
  const deleteRecordMutation = useMutation({
    mutationFn: (record: DNSRecord) => apiClient.deleteDNSRecord(selectedDomain, record.type, record.name),
    onSuccess: () => {
      toast.success('DNS record deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] });
      queryClient.invalidateQueries({ queryKey: ['domain-validation', selectedDomain] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete DNS record');
    },
  });

  // Set first domain as default
  useEffect(() => {
    if (domains.length > 0 && !selectedDomain) {
      setSelectedDomain(domains[0].domain);
    }
  }, [domains, selectedDomain]);

  const handleCreateRecord = (data: CreateRecordRequest) => {
    if (editingRecord) {
      updateRecordMutation.mutate({ record: editingRecord, data });
    } else {
      createRecordMutation.mutate(data);
    }
  };

  const handleEditRecord = (record: DNSRecord) => {
    setEditingRecord(record);
    setShowRecordForm(true);
  };

  const handleDeleteRecord = (record: DNSRecord) => {
    if (window.confirm(`Are you sure you want to delete the ${record.type} record for ${record.name}?`)) {
      deleteRecordMutation.mutate(record);
    }
  };

  const handleAddRecord = () => {
    setEditingRecord(undefined);
    setShowRecordForm(true);
  };

  const getValidationIcon = (validation: ValidationResult | null) => {
    if (!validation) return null;

    if (validation.issues.length > 0) {
      return <AlertTriangle className="h-5 w-5 text-red-500" />;
    }
    if (validation.warnings.length > 0) {
      return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
    }
    return <CheckCircle className="h-5 w-5 text-green-500" />;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Globe className="h-8 w-8 text-blue-600" />
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">GoDaddy DNS CLI</h1>
                  <p className="text-gray-500">Manage your DNS records</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <Shield className="h-5 w-5 text-green-500" />
                <span className="text-sm text-gray-600">Connected</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <label className="block text-sm font-medium text-gray-700">
                Select Domain:
              </label>
              <select
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value)}
                disabled={domainsLoading}
                className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {domainsLoading ? (
                  <option>Loading domains...</option>
                ) : (
                  domains.map((domain) => (
                    <option key={domain.domain} value={domain.domain}>
                      {domain.domain}
                    </option>
                  ))
                )}
              </select>
            </div>

            {selectedDomain && validation && (
              <div className="flex items-center space-x-2">
                {getValidationIcon(validation)}
                <span className="text-sm text-gray-600">
                  {validation.issues.length > 0
                    ? `${validation.issues.length} issues found`
                    : validation.warnings.length > 0
                    ? `${validation.warnings.length} warnings`
                    : 'Configuration looks good'}
                </span>
              </div>
            )}
          </div>
        </div>

        {selectedDomain && validation && (validation.issues.length > 0 || validation.warnings.length > 0) && (
          <div className="mb-6 bg-white border border-yellow-200 rounded-lg p-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">DNS Validation Results</h3>

            {validation.issues.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-red-800 mb-2">Issues:</h4>
                <ul className="text-sm text-red-700 space-y-1">
                  {validation.issues.map((issue, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {validation.warnings.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-yellow-800 mb-2">Warnings:</h4>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {validation.warnings.map((warning, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {selectedDomain ? (
          <DNSRecordTable
            records={records}
            loading={recordsLoading}
            onEdit={handleEditRecord}
            onDelete={handleDeleteRecord}
            onAdd={handleAddRecord}
            onRefresh={refetchRecords}
          />
        ) : (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <Globe className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Domain Selected</h3>
            <p className="text-gray-500">
              {domainsLoading
                ? 'Loading your domains...'
                : domains.length === 0
                ? 'No domains found in your account'
                : 'Select a domain to manage its DNS records'}
            </p>
          </div>
        )}

        <DNSRecordForm
          isOpen={showRecordForm}
          onClose={() => {
            setShowRecordForm(false);
            setEditingRecord(undefined);
          }}
          onSubmit={handleCreateRecord}
          editRecord={editingRecord}
          domain={selectedDomain}
        />
      </div>
    </div>
  );
};