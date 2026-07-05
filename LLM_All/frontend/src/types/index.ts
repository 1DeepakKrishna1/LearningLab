export interface User {
  id: string;
  username: string;
  role: "user" | "admin";
}

export interface AuthState {
  token: string;
  conversationId: string;
  username: string;
  role: "user" | "admin";
}

export interface FollowUp {
  text: string;
  query: string;
}

export interface TokensConsumed {
  input: number;
  output: number;
  total: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  follow_ups?: FollowUp[];
  tokens_consumed?: TokensConsumed;
  time_taken?: number;
  guardrail_triggered?: boolean;
  timestamp: string;
}

export interface ConversationOut {
  id: string;
  user_id: string;
  username: string;
  title: string;
  llm_provider: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface MessageOut {
  id: string;
  role: string;
  content: string;
  tokens_in: number;
  tokens_out: number;
  time_taken: number;
  guardrail_triggered: boolean;
  created_at: string;
}

export interface ConversationDetail extends ConversationOut {
  messages: MessageOut[];
  summary: string | null;
}

export interface ApiKeys {
  openai: string;
  anthropic: string;
  google: string;
  groq: string;
}

export interface SystemConfig {
  active_llm: string;
  models: Record<string, string>;
  system_prompt: string;
  context_window: number;
}

export interface GuardrailRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  type: string;
  keywords: string[];
  response: string;
}

export interface Guardrails {
  enabled: boolean;
  rules: GuardrailRule[];
}

export interface AnalyticsOut {
  conversation_id: string;
  username: string;
  total_messages: number;
  user_messages: number;
  assistant_messages: number;
  total_tokens: number;
  avg_tokens_per_response: number;
  avg_response_time: number;
  total_time: number;
  guardrail_triggers: number;
  session_duration_minutes: number;
  llm_provider: string | null;
  created_at: string;
}

export interface SummaryOut {
  conversation_id: string;
  summary: string;
  generated_at: string;
}

export interface InsightsOut {
  conversation_id: string;
  insights: string[];
  sentiment: string;
  topics: string[];
  generated_at: string;
}
