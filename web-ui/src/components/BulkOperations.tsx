import React, { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { Upload, Download, FileText, AlertCircle, CheckCircle, X } from 'lucide-react';
import apiClient from '@/utils/api';
import type { DNSRecord, BulkOperationResult } from '@/types/api';

interface BulkOperationsProps {
  domain: string;
  records: DNSRecord[];
  onClose: () => void;
}

export const BulkOperations: React.FC<BulkOperationsProps> = ({
  domain,
  records,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'import' | 'export' | 'template'>('import');
  const [csvContent, setCsvContent] = useState('');
  const [importResults, setImportResults] = useState<BulkOperationResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  // Bulk import mutation
  const bulkImportMutation = useMutation({
    mutationFn: (data: { domain: string; records: DNSRecord[] }) =>
      apiClient.bulkImportRecords(data.domain, data.records),
    onSuccess: (result) => {
      setImportResults(result.data);
      queryClient.invalidateQueries({ queryKey: ['dns-records', domain] });
      if (result.data.failed === 0) {
        toast.success(`Successfully imported ${result.data.success} records`);
      } else {
        toast.warning(`Imported ${result.data.success} records with ${result.data.failed} failures`);
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Bulk import failed');
    },
  });

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setCsvContent(content);
      parseAndPreviewCSV(content);
    };
    reader.readAsText(file);
  };

  const parseAndPreviewCSV = (content: string) => {
    try {
      const lines = content.split('\n').filter(line => line.trim());
      const headers = lines[0].split(',').map(h => h.trim());

      if (!headers.includes('name') || !headers.includes('type') || !headers.includes('data')) {
        toast.error('CSV must contain at least: name, type, data columns');
        return;
      }

      const parsedRecords = lines.slice(1).map(line => {
        const values = line.split(',').map(v => v.trim());
        const record: any = {};
        headers.forEach((header, index) => {
          record[header] = values[index] || '';
        });
        return record;
      });

      console.log('Parsed records:', parsedRecords);
    } catch (error) {
      toast.error('Failed to parse CSV file');
    }
  };

  const handleBulkImport = () => {
    if (!csvContent) {
      toast.error('Please upload a CSV file first');
      return;
    }

    try {
      const lines = csvContent.split('\n').filter(line => line.trim());
      const headers = lines[0].split(',').map(h => h.trim());

      const records: DNSRecord[] = lines.slice(1).map(line => {
        const values = line.split(',').map(v => v.trim());
        const record: any = {};
        headers.forEach((header, index) => {
          record[header] = values[index] || '';
        });

        return {
          name: record.name,
          type: record.type,
          data: record.data,
          ttl: parseInt(record.ttl) || 3600,
          priority: record.priority ? parseInt(record.priority) : undefined,
          weight: record.weight ? parseInt(record.weight) : undefined,
          port: record.port ? parseInt(record.port) : undefined,
        };
      });

      bulkImportMutation.mutate({ domain, records });
    } catch (error) {
      toast.error('Failed to parse CSV content');
    }
  };

  const handleExportCSV = () => {
    const csvHeaders = ['name', 'type', 'data', 'ttl', 'priority', 'weight', 'port'];
    const csvRows = records.map(record => [
      record.name,
      record.type,
      record.data,
      record.ttl,
      record.priority || '',
      record.weight || '',
      record.port || ''
    ]);

    const csvContent = [
      csvHeaders.join(','),
      ...csvRows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${domain}-dns-records.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('DNS records exported to CSV');
  };

  const handleExportJSON = () => {
    const jsonContent = JSON.stringify(records, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${domain}-dns-records.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('DNS records exported to JSON');
  };

  const generateSampleCSV = () => {
    const sampleContent = `name,type,data,ttl,priority,weight,port
@,A,192.168.1.1,3600,,,
www,CNAME,${domain},3600,,,
mail,MX,mail.${domain},3600,10,,
api,A,192.168.1.2,7200,,,
_dmarc,TXT,"v=DMARC1; p=none; rua=mailto:dmarc@${domain}",3600,,,`;

    setCsvContent(sampleContent);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Bulk Operations</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6">
          <div className="flex space-x-1 mb-6">
            {(['import', 'export', 'template'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium rounded-lg capitalize ${
                  activeTab === tab
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === 'import' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Import DNS Records</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Upload CSV File
                    </label>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv"
                      onChange={handleFileUpload}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      CSV should contain: name, type, data, ttl (optional: priority, weight, port)
                    </p>
                  </div>
                  <div className="flex flex-col">
                    <button
                      onClick={generateSampleCSV}
                      className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 mb-2"
                    >
                      Generate Sample CSV
                    </button>
                    <button
                      onClick={handleBulkImport}
                      disabled={!csvContent || bulkImportMutation.isPending}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {bulkImportMutation.isPending ? 'Importing...' : 'Import Records'}
                    </button>
                  </div>
                </div>

                {csvContent && (
                  <div className="mt-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      CSV Preview
                    </label>
                    <textarea
                      value={csvContent}
                      onChange={(e) => setCsvContent(e.target.value)}
                      rows={8}
                      className="w-full border border-gray-300 rounded-lg p-3 font-mono text-sm"
                      placeholder="Paste CSV content or upload a file..."
                    />
                  </div>
                )}

                {importResults && (
                  <div className="mt-6 bg-gray-50 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Import Results</h4>
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">{importResults.success}</div>
                        <div className="text-sm text-gray-500">Successful</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">{importResults.failed}</div>
                        <div className="text-sm text-gray-500">Failed</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900">
                          {importResults.success + importResults.failed}
                        </div>
                        <div className="text-sm text-gray-500">Total</div>
                      </div>
                    </div>

                    {importResults.errors && importResults.errors.length > 0 && (
                      <div>
                        <h5 className="text-sm font-medium text-red-800 mb-2">Errors:</h5>
                        <ul className="text-sm text-red-700 space-y-1">
                          {importResults.errors.map((error, index) => (
                            <li key={index} className="flex items-start space-x-2">
                              <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                              <span>{error}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'export' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Export DNS Records</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button
                    onClick={handleExportCSV}
                    className="flex items-center justify-center px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50"
                  >
                    <div className="text-center">
                      <FileText className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                      <div className="text-sm font-medium text-gray-900">Export as CSV</div>
                      <div className="text-xs text-gray-500">Spreadsheet compatible</div>
                    </div>
                  </button>

                  <button
                    onClick={handleExportJSON}
                    className="flex items-center justify-center px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50"
                  >
                    <div className="text-center">
                      <FileText className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                      <div className="text-sm font-medium text-gray-900">Export as JSON</div>
                      <div className="text-xs text-gray-500">API compatible</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      const yamlContent = records.map(record => ({
                        name: record.name,
                        type: record.type,
                        data: record.data,
                        ttl: record.ttl,
                        ...(record.priority && { priority: record.priority }),
                        ...(record.weight && { weight: record.weight }),
                        ...(record.port && { port: record.port }),
                      }));

                      const yamlString = yamlContent.map(record =>
                        Object.entries(record).map(([key, value]) => `${key}: ${value}`).join('\n')
                      ).join('\n---\n');

                      const blob = new Blob([yamlString], { type: 'text/yaml' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${domain}-dns-records.yaml`;
                      a.click();
                      URL.revokeObjectURL(url);
                      toast.success('DNS records exported to YAML');
                    }}
                    className="flex items-center justify-center px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50"
                  >
                    <div className="text-center">
                      <FileText className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                      <div className="text-sm font-medium text-gray-900">Export as YAML</div>
                      <div className="text-xs text-gray-500">Human readable</div>
                    </div>
                  </button>
                </div>

                <div className="mt-6 bg-blue-50 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="h-5 w-5 text-blue-500 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-medium text-blue-800">Current Records Summary</h4>
                      <p className="text-sm text-blue-700 mt-1">
                        {records.length} records ready for export from {domain}
                      </p>
                      <div className="mt-2">
                        {Object.entries(
                          records.reduce((acc, record) => {
                            acc[record.type] = (acc[record.type] || 0) + 1;
                            return acc;
                          }, {} as Record<string, number>)
                        ).map(([type, count]) => (
                          <span key={type} className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded mr-2 mb-1">
                            {type}: {count}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'template' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">DNS Templates</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Web Application Template */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Web Application</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Standard setup for web applications with www redirect and API subdomain
                    </p>
                    <button
                      onClick={() => {
                        const template = [
                          { name: '@', type: 'A', data: '192.168.1.1', ttl: 3600 },
                          { name: 'www', type: 'CNAME', data: domain, ttl: 3600 },
                          { name: 'api', type: 'A', data: '192.168.1.2', ttl: 3600 },
                        ];
                        const csv = 'name,type,data,ttl\n' +
                          template.map(r => `${r.name},${r.type},${r.data},${r.ttl}`).join('\n');
                        setCsvContent(csv);
                        setActiveTab('import');
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Use Template
                    </button>
                  </div>

                  {/* Email Server Template */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Email Server</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Complete email server setup with MX, SPF, and DMARC records
                    </p>
                    <button
                      onClick={() => {
                        const template = [
                          { name: '@', type: 'MX', data: `mail.${domain}`, ttl: 3600, priority: 10 },
                          { name: 'mail', type: 'A', data: '192.168.1.10', ttl: 3600 },
                          { name: '@', type: 'TXT', data: 'v=spf1 mx ~all', ttl: 3600 },
                          { name: '_dmarc', type: 'TXT', data: `v=DMARC1; p=none; rua=mailto:dmarc@${domain}`, ttl: 3600 },
                        ];
                        const csv = 'name,type,data,ttl,priority\n' +
                          template.map(r => `${r.name},${r.type},${r.data},${r.ttl},${r.priority || ''}`).join('\n');
                        setCsvContent(csv);
                        setActiveTab('import');
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Use Template
                    </button>
                  </div>

                  {/* CDN Template */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">CDN Setup</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Cloudflare/CDN integration with multiple geographic endpoints
                    </p>
                    <button
                      onClick={() => {
                        const template = [
                          { name: '@', type: 'A', data: '104.16.1.1', ttl: 300 },
                          { name: '@', type: 'A', data: '104.16.2.1', ttl: 300 },
                          { name: 'www', type: 'CNAME', data: domain, ttl: 300 },
                          { name: 'cdn', type: 'CNAME', data: `${domain}.cdn.cloudflare.net`, ttl: 300 },
                        ];
                        const csv = 'name,type,data,ttl\n' +
                          template.map(r => `${r.name},${r.type},${r.data},${r.ttl}`).join('\n');
                        setCsvContent(csv);
                        setActiveTab('import');
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Use Template
                    </button>
                  </div>

                  {/* Development Template */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Development Environment</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Development setup with staging, test, and dev subdomains
                    </p>
                    <button
                      onClick={() => {
                        const template = [
                          { name: 'dev', type: 'A', data: '192.168.1.100', ttl: 300 },
                          { name: 'staging', type: 'A', data: '192.168.1.101', ttl: 300 },
                          { name: 'test', type: 'A', data: '192.168.1.102', ttl: 300 },
                          { name: 'api-dev', type: 'A', data: '192.168.1.103', ttl: 300 },
                        ];
                        const csv = 'name,type,data,ttl\n' +
                          template.map(r => `${r.name},${r.type},${r.data},${r.ttl}`).join('\n');
                        setCsvContent(csv);
                        setActiveTab('import');
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Use Template
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'export' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Export Options</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Export all {records.length} DNS records for {domain} in your preferred format.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button
                    onClick={handleExportCSV}
                    className="flex items-center justify-center px-6 py-8 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50"
                  >
                    <div className="text-center">
                      <Download className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                      <div className="text-sm font-medium text-gray-900">CSV Format</div>
                      <div className="text-xs text-gray-500">Excel/Spreadsheet</div>
                    </div>
                  </button>

                  <button
                    onClick={handleExportJSON}
                    className="flex items-center justify-center px-6 py-8 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50"
                  >
                    <div className="text-center">
                      <Download className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                      <div className="text-sm font-medium text-gray-900">JSON Format</div>
                      <div className="text-xs text-gray-500">API/Programming</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(records, null, 2));
                      toast.success('Records copied to clipboard');
                    }}
                    className="flex items-center justify-center px-6 py-8 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50"
                  >
                    <div className="text-center">
                      <FileText className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                      <div className="text-sm font-medium text-gray-900">Copy to Clipboard</div>
                      <div className="text-xs text-gray-500">Quick sharing</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleFileUpload}
        className="hidden"
      />
    </div>
  );
};