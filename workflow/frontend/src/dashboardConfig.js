// Keys used in localStorage
const WK = 'wf-dashboard-widgets'
const RT = 'wf-report-tabs'

// Available metric paths (used when creating custom widgets)
export const METRIC_KEYS = [
  { key: 'workflows.total',                  label: 'Total Workflows' },
  { key: 'workflows.active',                 label: 'Active Workflows' },
  { key: 'workflows.draft',                  label: 'Draft Workflows' },
  { key: 'executions.total',                 label: 'Total Executions' },
  { key: 'executions.completed',             label: 'Completed Executions' },
  { key: 'executions.failed',                label: 'Failed Executions' },
  { key: 'executions.success_rate',          label: 'Success Rate (%)' },
  { key: 'performance.avg_duration_ms',      label: 'Avg Duration (ms)' },
  { key: 'performance.sla_compliance_pct',   label: 'SLA Compliance (%)' },
  { key: 'tokens.usage_pct',                 label: 'Token Usage (%)' },
  { key: 'tokens.today',                     label: 'Tokens Today' },
  { key: 'library.tools',                    label: 'Tools Count' },
  { key: 'library.agents',                   label: 'Agents Count' },
  { key: 'users.total',                      label: 'Total Users' },
  { key: 'users.active',                     label: 'Active Users' },
]

// Available report link targets
export const REPORT_OPTIONS = [
  { id: 'workflow_usage',    label: 'Workflow Usage' },
  { id: 'agent_performance', label: 'Agent Performance' },
  { id: 'user_activity',     label: 'User Activity' },
  { id: 'token_consumption', label: 'Token Consumption' },
]

export const ACCENT_OPTIONS = ['indigo','emerald','amber','red','purple','cyan','slate','orange']

// icon strings map to lucide icon names; Dashboard.jsx resolves them
export const DEFAULT_WIDGETS = [
  { id:'total_workflows',   title:'Total Workflows',   icon:'GitBranch',   accent:'indigo',  group:'Workflows',   row:1, order:0,  report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'active_workflows',  title:'Active Workflows',  icon:'Activity',    accent:'emerald', group:'Workflows',   row:1, order:1,  report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'draft_workflows',   title:'Draft Workflows',   icon:'FileEdit',    accent:'amber',   group:'Workflows',   row:1, order:2,  report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'total_executions',  title:'Total Executions',  icon:'Zap',         accent:'slate',   group:'Executions',  row:2, order:3,  report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'completed',         title:'Completed',         icon:'CheckCircle2',accent:'emerald', group:'Executions',  row:2, order:4,  report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'failed',            title:'Failed',            icon:'XCircle',     accent:'red',     group:'Executions',  row:2, order:5,  report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'success_rate',      title:'Success Rate',      icon:'TrendingUp',  accent:'slate',   group:'Executions',  row:2, order:6,  report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'avg_duration',      title:'Avg Duration',      icon:'Timer',       accent:'indigo',  group:'Performance', row:3, order:7,  report_link:'agent_performance', enabled:true,  custom:false },
  { id:'sla_compliance',    title:'SLA Compliance',    icon:'ShieldCheck', accent:'emerald', group:'Performance', row:3, order:8,  report_link:'agent_performance', enabled:true,  custom:false },
  { id:'token_usage',       title:'Token Usage',       icon:'Coins',       accent:'amber',   group:'Tokens',      row:3, order:9,  report_link:'token_consumption', enabled:true,  custom:false },
  { id:'exec_trend',        title:'Executions 7-Day',  icon:'BarChart2',   accent:'indigo',  group:'Trends',      row:4, order:10, report_link:'workflow_usage',    enabled:true,  custom:false },
  { id:'token_trend',       title:'Token Trend',       icon:'BarChart2',   accent:'emerald', group:'Trends',      row:4, order:11, report_link:'token_consumption', enabled:true,  custom:false },
  { id:'component_library', title:'Component Library', icon:'GitBranch',   accent:'purple',  group:'Library',     row:5, order:12, report_link:'agent_performance', enabled:true,  custom:false },
  { id:'platform_users',    title:'Platform Users',    icon:'Users',       accent:'cyan',    group:'Users',       row:5, order:13, report_link:'user_activity',     enabled:true,  custom:false },
]

export const DEFAULT_REPORT_TABS = [
  { id:'workflow_usage',    label:'Workflow Usage',    icon:'GitBranch', data_type:'workflow_usage',    enabled:true, order:0, custom:false },
  { id:'agent_performance', label:'Agent Performance', icon:'Bot',       data_type:'agent_performance', enabled:true, order:1, custom:false },
  { id:'user_activity',     label:'User Activity',     icon:'Users',     data_type:'user_activity',     enabled:true, order:2, custom:false },
  { id:'token_consumption', label:'Token Consumption', icon:'Coins',     data_type:'token_consumption', enabled:true, order:3, custom:false },
]

function mergeWithDefaults(saved, defaults) {
  const savedIds = new Set(saved.map(x => x.id))
  const merged = [...saved]
  for (const d of defaults) {
    if (!savedIds.has(d.id)) merged.push({ ...d })
  }
  return merged.sort((a, b) => a.order - b.order)
}

export function loadWidgets() {
  try {
    const raw = localStorage.getItem(WK)
    if (!raw) return [...DEFAULT_WIDGETS]
    return mergeWithDefaults(JSON.parse(raw), DEFAULT_WIDGETS)
  } catch {
    return [...DEFAULT_WIDGETS]
  }
}

export function saveWidgets(widgets) {
  // re-assign order by array index before saving
  const normalised = widgets.map((w, i) => ({ ...w, order: i }))
  localStorage.setItem(WK, JSON.stringify(normalised))
  return normalised
}

export function loadReportTabs() {
  try {
    const raw = localStorage.getItem(RT)
    if (!raw) return [...DEFAULT_REPORT_TABS]
    return mergeWithDefaults(JSON.parse(raw), DEFAULT_REPORT_TABS)
  } catch {
    return [...DEFAULT_REPORT_TABS]
  }
}

export function saveReportTabs(tabs) {
  const normalised = tabs.map((t, i) => ({ ...t, order: i }))
  localStorage.setItem(RT, JSON.stringify(normalised))
  return normalised
}

// Resolve a dot-path like 'executions.total' into a metrics object
export function getMetricValue(metrics, key) {
  if (!metrics || !key) return null
  return key.split('.').reduce((obj, k) => obj?.[k], metrics)
}
