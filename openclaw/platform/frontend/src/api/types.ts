// Shared API types mirroring the backend domain models.

export type Role = "admin" | "designer" | "operator" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ToolParameter {
  name: string;
  type: string;
  required: boolean;
  default: unknown;
  description: string;
}

export interface ToolManifest {
  id: string;
  name: string;
  display_name: string;
  category: string;
  description: string;
  impl_path: string;
  class_name: string | null;
  parameters: ToolParameter[];
  input_schema: Record<string, unknown>;
  tags: string[];
  icon: string;
  color: string;
}

export interface NodeData {
  label: string;
  config: Record<string, unknown>;
  agent_id?: string | null;
  tool_id?: string | null;
}

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: NodeData;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  label?: string | null;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  version: number;
  status: "draft" | "published" | "archived";
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables: Record<string, unknown>;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface NodeRun {
  node_id: string;
  node_type: string;
  label: string;
  status: string;
  attempts: number;
  output: Record<string, unknown> | null;
  error: string | null;
}

export interface Execution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: string;
  node_runs: NodeRun[];
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  role: string;
  tools: string[];
  model: string | null;
  provider: string | null;
  temperature: number;
  capabilities: string[];
  limits: {
    max_iterations: number;
    timeout_seconds: number;
    tool_allow_list: string[];
    sandboxed: boolean;
  };
}

export interface Approval {
  id: string;
  execution_id: string;
  workflow_id: string;
  node_id: string;
  title: string;
  description: string;
  channel: string;
  status: string;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  result: string;
  workflow: string | null;
  agent: string | null;
  detail: Record<string, unknown>;
}

export interface NodeCatalog {
  static: Record<string, { type: string; label: string; icon: string }[]>;
  tools: Record<
    string,
    { type: string; label: string; icon: string; color: string; tool_id: string; description: string }[]
  >;
}

export interface Dashboard {
  executions: {
    total: number;
    running: number;
    completed: number;
    failed: number;
    waiting_approval: number;
    by_status: Record<string, number>;
  };
  queue_depth: number;
  active_agents: number;
  tools: { registered: number; categories: number };
  tool_usage: [string, number][];
}
