export interface DNSRecord {
  name: string;
  type: string;
  data: string;
  ttl: number;
  priority?: number;
}

export interface Domain {
  domain: string;
  status: string;
  expires?: string;
  created?: string;
  privacy: boolean;
  locked: boolean;
}

export interface ConfigStatus {
  config_file: string;
  profile: string;
  api_configured: boolean;
  profiles: string[];
}

export interface Template {
  name: string;
  description: string;
  version: string;
  file: string;
}

export interface ValidationResult {
  domain: string;
  valid: boolean;
  issues: string[];
  warnings: string[];
  suggestions: string[];
  record_count: number;
}

export interface BulkOperationResult {
  success: number;
  failed: number;
  errors: string[];
}

export interface WebSocketMessage {
  type: 'record_created' | 'record_updated' | 'record_deleted' | 'bulk_operation' | 'template_applied';
  domain: string;
  record?: DNSRecord;
  record_type?: string;
  record_name?: string;
  operation?: string;
  template?: string;
  result?: BulkOperationResult;
}

export interface APIError {
  detail: string;
  status_code?: number;
}

export interface CreateRecordRequest {
  name: string;
  type: string;
  data: string;
  ttl: number;
  priority?: number;
}

export interface UpdateRecordRequest {
  name: string;
  type: string;
  data: string;
  ttl: number;
  priority?: number;
}

export interface BulkOperationRequest {
  operation: 'create' | 'replace';
  records: CreateRecordRequest[];
}

export interface TemplateRequest {
  template_name: string;
  variables: Record<string, any>;
}