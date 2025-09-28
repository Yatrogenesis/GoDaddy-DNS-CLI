import axios from 'axios';
import type {
  DNSRecord,
  Domain,
  ConfigStatus,
  Template,
  ValidationResult,
  CreateRecordRequest,
  UpdateRecordRequest,
  BulkOperationRequest,
  TemplateRequest,
  BulkOperationResult,
} from '@/types/api';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const apiClient = {
  // Health and config
  health: () => api.get('/health'),
  getConfigStatus: (): Promise<{ data: ConfigStatus }> => api.get('/config/status'),

  // Domains
  getDomains: (): Promise<{ data: Domain[] }> => api.get('/domains'),

  // DNS Records
  getDNSRecords: (domain: string, recordType?: string): Promise<{ data: DNSRecord[] }> =>
    api.get(`/domains/${domain}/records`, { params: { record_type: recordType } }),

  createDNSRecord: (domain: string, record: CreateRecordRequest) =>
    api.post(`/domains/${domain}/records`, record),

  updateDNSRecord: (domain: string, recordType: string, recordName: string, record: UpdateRecordRequest) =>
    api.put(`/domains/${domain}/records/${recordType}/${recordName}`, record),

  deleteDNSRecord: (domain: string, recordType: string, recordName: string) =>
    api.delete(`/domains/${domain}/records/${recordType}/${recordName}`),

  // Bulk operations
  bulkOperation: (domain: string, operation: BulkOperationRequest): Promise<{ data: { result: BulkOperationResult } }> =>
    api.post(`/domains/${domain}/bulk`, operation),

  bulkImportRecords: (domain: string, records: DNSRecord[]): Promise<{ data: BulkOperationResult }> =>
    api.post(`/domains/${domain}/bulk/import`, { records }),

  bulkExportRecords: (domain: string, format: 'csv' | 'json' | 'yaml' = 'json'): Promise<{ data: any }> =>
    api.get(`/domains/${domain}/export`, { params: { format } }),

  // Templates
  getTemplates: (): Promise<{ data: Template[] }> => api.get('/templates'),

  applyTemplate: (domain: string, templateRequest: TemplateRequest): Promise<{ data: { result: BulkOperationResult } }> =>
    api.post(`/domains/${domain}/template`, templateRequest),

  // Validation
  validateDomain: (domain: string): Promise<{ data: ValidationResult }> =>
    api.get(`/domains/${domain}/validate`),
};

export default apiClient;