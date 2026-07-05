// Shared API types mirroring the backend Pydantic schemas.

export type Channel = 'email' | 'sms' | 'push';
export type CampaignType = 'one_time' | 'recurring' | 'drip' | 'multi_channel';
export type CampaignStatus =
  | 'draft' | 'pending_approval' | 'approved' | 'scheduled' | 'sending'
  | 'completed' | 'failed' | 'paused' | 'cancelled' | 'archived';

export interface Role { id: number; name: string; description: string }
export interface User {
  id: number; email: string; full_name: string; is_active: boolean;
  roles: Role[]; last_login_at?: string | null; created_at: string;
}
export interface TokenResponse {
  access_token: string; refresh_token: string; token_type: string; expires_in: number;
}

export interface Template {
  id: number; name: string; channel: Channel; category: string; status: string;
  version: number; subject?: string | null; preheader?: string | null;
  html_content?: string | null; text_content?: string | null; title?: string | null;
  body?: string | null; image_url?: string | null; deep_link?: string | null;
  buttons?: { label: string; action: string }[] | null; variables: string[];
  created_at: string; updated_at: string;
}

export interface Contact {
  id: number; email?: string | null; phone?: string | null; first_name?: string | null;
  last_name?: string | null; country?: string | null; timezone?: string | null;
  tags: string[]; attributes: Record<string, unknown>; is_active: boolean; created_at: string;
}

export interface Condition { field: string; operator: string; value: unknown }
export interface RuleGroup { op: 'AND' | 'OR'; rules: (RuleGroup | Condition)[] }
export interface Segment {
  id: number; name: string; description: string; is_dynamic: boolean;
  definition: RuleGroup; cached_count?: number | null; created_at: string; updated_at: string;
}

export interface CampaignStep {
  id?: number; step_order: number; channel: Channel; template_id?: number | null; delay_hours: number;
}
export interface Campaign {
  id: number; name: string; description: string; type: CampaignType; status: CampaignStatus;
  channel?: Channel | null; template_id?: number | null; segment_id?: number | null;
  scheduled_at?: string | null; timezone: string; recurrence?: Record<string, unknown> | null;
  next_run_at?: string | null; started_at?: string | null; completed_at?: string | null;
  approved_at?: string | null; rejection_reason?: string | null; steps: CampaignStep[];
  created_at: string; updated_at: string;
}

export interface ProviderConfig {
  id: number; name: string; channel: Channel; provider_type: string; config: Record<string, unknown>;
  mode: string; is_default: boolean; is_active: boolean;
  last_health_status?: string | null; last_health_checked_at?: string | null; created_at: string;
}

export interface CampaignMetrics {
  campaign_id: number; campaign_name: string; channel?: string | null;
  sent: number; delivered: number; opened: number; clicked: number; bounced: number;
  failed: number; unsubscribed: number; converted: number; replied: number;
  delivery_rate: number; open_rate: number; click_rate: number; bounce_rate: number;
  failure_rate: number; reply_rate: number; conversion_rate: number;
}
export interface OverviewMetrics {
  total_campaigns: number; active_campaigns: number; total_contacts: number;
  sent: number; delivered: number; opened: number; clicked: number;
}
export interface TimeseriesPoint { date: string; sent: number; delivered: number; opened: number; clicked: number }

export interface AuditLog {
  id: number; user_email?: string | null; action: string; entity_type?: string | null;
  entity_id?: string | null; ip_address?: string | null; created_at: string;
}

export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
