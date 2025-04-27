export interface User {
  id: string;
  email: string;
  role: 'user' | 'admin' | 'compliance_officer';
  organization_id: string;
}

export interface Organization {
  id: string;
  name: string;
  settings: Record<string, any>;
}

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  user_id: string;
  organization_id: string;
  metadata: Record<string, any>;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  created_at: string;
  created_by: string;
  changes: string;
}

export interface ComplianceRule {
  id: string;
  name: string;
  description: string;
  pattern: string;
  severity: 'low' | 'medium' | 'high';
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  organization_id: string;
}

export interface ComplianceCheck {
  id: string;
  document_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  violations: ComplianceViolation[];
  created_at: string;
  updated_at: string;
  checked_by: string;
}

export interface ComplianceViolation {
  rule_id: string;
  rule_name: string;
  description: string;
  text: string;
  suggestion: string;
  severity: 'low' | 'medium' | 'high';
}

export interface AuditLog {
  id: string;
  user_id: string;
  document_id: string;
  action: 'upload' | 'download' | 'check' | 'approve' | 'reject' | 'version' | 'delete';
  details: Record<string, any>;
  created_at: string;
  ip_address: string;
} 