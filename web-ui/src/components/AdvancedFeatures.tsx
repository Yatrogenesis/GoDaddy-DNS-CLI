import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  Monitor,
  Template,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Settings,
  X
} from 'lucide-react';
import apiClient from '@/utils/api';
import type { Template as TemplateType, ValidationResult, BulkOperationResult } from '@/types/api';

interface AdvancedFeaturesProps {
  domain: string;
  onClose: () => void;
}

interface MonitoringStatus {
  domain: string;
  status: 'healthy' | 'warning' | 'error';
  last_check: string;
  interval: number;
  checks: {
    dns_resolution: boolean;
    record_consistency: boolean;
    ttl_compliance: boolean;
    security_records: boolean;
  };
}

export const AdvancedFeatures: React.FC<AdvancedFeaturesProps> = ({
  domain,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'monitoring' | 'templates' | 'validation'>('monitoring');
  const [monitoringEnabled, setMonitoringEnabled] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [templateVariables, setTemplateVariables] = useState<Record<string, string>>({});
  const queryClient = useQueryClient();

  // Fetch templates
  const { data: templates = [] } = useQuery({
    queryKey: ['templates'],
    queryFn: () => apiClient.getTemplates().then(res => res.data),
  });

  // Fetch monitoring status
  const { data: monitoringStatus } = useQuery({
    queryKey: ['monitoring', domain],
    queryFn: async (): Promise<MonitoringStatus> => {
      // Mock data for demonstration
      return {
        domain,
        status: 'healthy',
        last_check: new Date().toISOString(),
        interval: 300,
        checks: {
          dns_resolution: true,
          record_consistency: true,
          ttl_compliance: true,
          security_records: false,
        }
      };
    },
    enabled: !!domain,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch validation results
  const { data: validation, refetch: refetchValidation } = useQuery({
    queryKey: ['domain-validation', domain],
    queryFn: () => apiClient.validateDomain(domain).then(res => res.data),
    enabled: !!domain,
  });

  // Apply template mutation
  const applyTemplateMutation = useMutation({
    mutationFn: ({ template, variables }: { template: string; variables: Record<string, any> }) =>
      apiClient.applyTemplate(domain, { template_name: template, variables }),
    onSuccess: (result) => {
      toast.success(`Template applied successfully`);
      queryClient.invalidateQueries({ queryKey: ['dns-records', domain] });
      setSelectedTemplate('');
      setTemplateVariables({});
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to apply template');
    },
  });

  const handleApplyTemplate = () => {
    if (!selectedTemplate) {
      toast.error('Please select a template');
      return;
    }

    const template = templates.find(t => t.name === selectedTemplate);
    if (!template) {
      toast.error('Template not found');
      return;
    }

    applyTemplateMutation.mutate({
      template: selectedTemplate,
      variables: templateVariables,
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'error':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const formatLastCheck = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes} minutes ago`;
    if (minutes < 1440) return `${Math.floor(minutes / 60)} hours ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Advanced Features - {domain}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6">
          <div className="flex space-x-1 mb-6">
            {(['monitoring', 'templates', 'validation'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium rounded-lg capitalize flex items-center space-x-2 ${
                  activeTab === tab
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'monitoring' && <Monitor className="h-4 w-4" />}
                {tab === 'templates' && <Template className="h-4 w-4" />}
                {tab === 'validation' && <Settings className="h-4 w-4" />}
                <span>{tab}</span>
              </button>
            ))}
          </div>

          {activeTab === 'monitoring' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">DNS Monitoring</h3>
                <div className="flex items-center space-x-4">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={monitoringEnabled}
                      onChange={(e) => setMonitoringEnabled(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Enable monitoring</span>
                  </label>
                  {monitoringEnabled ? (
                    <Pause className="h-5 w-5 text-orange-500" />
                  ) : (
                    <Play className="h-5 w-5 text-green-500" />
                  )}
                </div>
              </div>

              {monitoringStatus && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium text-gray-900">Status Overview</h4>
                      {getStatusIcon(monitoringStatus.status)}
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Last Check:</span>
                        <span className="text-gray-900">{formatLastCheck(monitoringStatus.last_check)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Check Interval:</span>
                        <span className="text-gray-900">{monitoringStatus.interval}s</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Overall Status:</span>
                        <span className={`capitalize font-medium ${
                          monitoringStatus.status === 'healthy' ? 'text-green-600' :
                          monitoringStatus.status === 'warning' ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {monitoringStatus.status}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-4">Health Checks</h4>
                    <div className="space-y-3">
                      {Object.entries(monitoringStatus.checks).map(([check, status]) => (
                        <div key={check} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600 capitalize">
                            {check.replace(/_/g, ' ')}
                          </span>
                          {status ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-red-500" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <Monitor className="h-5 w-5 text-blue-500 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-medium text-blue-800">Monitoring Features</h4>
                    <ul className="text-sm text-blue-700 mt-2 space-y-1">
                      <li>• Real-time DNS resolution monitoring</li>
                      <li>• Record consistency validation</li>
                      <li>• TTL compliance checking</li>
                      <li>• Security record verification (SPF, DKIM, DMARC)</li>
                      <li>• Alert notifications via email/webhook</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'templates' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">DNS Templates</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Apply pre-configured DNS setups for common use cases.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  {templates.map((template) => (
                    <div
                      key={template.name}
                      className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                        selectedTemplate === template.name
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => setSelectedTemplate(template.name)}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium text-gray-900">{template.name}</h4>
                          <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                          <span className="inline-block mt-2 text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                            v{template.version}
                          </span>
                        </div>
                        <FileText className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>
                  ))}
                </div>

                {selectedTemplate && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-4">Template Variables</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Application IP
                        </label>
                        <input
                          type="text"
                          placeholder="192.168.1.1"
                          value={templateVariables.app_ip || ''}
                          onChange={(e) => setTemplateVariables(prev => ({ ...prev, app_ip: e.target.value }))}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Backup IP (optional)
                        </label>
                        <input
                          type="text"
                          placeholder="192.168.1.2"
                          value={templateVariables.backup_ip || ''}
                          onChange={(e) => setTemplateVariables(prev => ({ ...prev, backup_ip: e.target.value }))}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                        />
                      </div>
                    </div>
                    <button
                      onClick={handleApplyTemplate}
                      disabled={applyTemplateMutation.isPending}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {applyTemplateMutation.isPending ? 'Applying...' : 'Apply Template'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'validation' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">DNS Validation</h3>
                <button
                  onClick={() => refetchValidation()}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Re-validate
                </button>
              </div>

              {validation && (
                <div className="space-y-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium text-gray-900">Overall Status</h4>
                      {validation.valid ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold text-blue-600">{validation.record_count}</div>
                        <div className="text-sm text-gray-500">Total Records</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-red-600">{validation.issues.length}</div>
                        <div className="text-sm text-gray-500">Issues</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-yellow-600">{validation.warnings.length}</div>
                        <div className="text-sm text-gray-500">Warnings</div>
                      </div>
                    </div>
                  </div>

                  {validation.issues.length > 0 && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-red-800 mb-3">Issues Found</h4>
                      <ul className="text-sm text-red-700 space-y-2">
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
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-yellow-800 mb-3">Warnings</h4>
                      <ul className="text-sm text-yellow-700 space-y-2">
                        {validation.warnings.map((warning, index) => (
                          <li key={index} className="flex items-start space-x-2">
                            <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                            <span>{warning}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {validation.suggestions.length > 0 && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-blue-800 mb-3">Suggestions</h4>
                      <ul className="text-sm text-blue-700 space-y-2">
                        {validation.suggestions.map((suggestion, index) => (
                          <li key={index} className="flex items-start space-x-2">
                            <CheckCircle className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                            <span>{suggestion}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};