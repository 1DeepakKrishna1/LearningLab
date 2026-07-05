import axios from 'axios'
import { trackEvent, log as obsLog } from './obs'

export const BASE_URL = 'http://localhost:8000'

const http = axios.create({ baseURL: BASE_URL, headers: { 'Content-Type': 'application/json' } })

// Inject auth token from localStorage on every request and stamp timing.
http.interceptors.request.use(cfg => {
  const token = localStorage.getItem('wf-token')
  if (token) cfg.headers['Authorization'] = `Bearer ${token}`
  cfg.metadata = { startedAt: performance.now() }
  return cfg
})

// Auto-track every API call as a frontend "api" event + correlate trace id.
http.interceptors.response.use(
  (res) => {
    const dur = res.config.metadata ? performance.now() - res.config.metadata.startedAt : null
    trackEvent('api', `${res.config.method?.toUpperCase()} ${res.config.url}`, {
      duration_ms: dur ? Math.round(dur) : null,
      status: 'ok',
      attributes: { status_code: res.status, trace_id: res.headers?.['x-trace-id'] || null },
    })
    return res
  },
  (err) => {
    const cfg = err.config || {}
    const dur = cfg.metadata ? performance.now() - cfg.metadata.startedAt : null
    const status = err.response?.status ?? 0
    trackEvent('api', `${cfg.method?.toUpperCase?.() || 'REQ'} ${cfg.url || ''}`, {
      duration_ms: dur ? Math.round(dur) : null,
      status: status >= 500 ? 'error' : 'client_error',
      attributes: { status_code: status, message: err.message },
    })
    if (status >= 500) {
      obsLog('error', `API error ${status} on ${cfg.url}`, { logger: 'http', extra: { message: err.message } })
    }
    return Promise.reject(err)
  },
)

// ── Org config (branding) ──────────────────────────────────
export const getOrgConfig  = ()           => http.get('/config').then(r => r.data)

// ── Tools ──────────────────────────────────────────────────
export const getTools      = ()           => http.get('/tools').then(r => r.data)
export const createTool    = (data)       => http.post('/tools', data).then(r => r.data)
export const updateTool    = (id, data)   => http.put(`/tools/${id}`, data).then(r => r.data)
export const deleteTool    = (id)         => http.delete(`/tools/${id}`).then(r => r.data)
export const exportTool        = (id)                       => http.get(`/tools/${id}/export`).then(r => r.data)
export const previewToolImport = (exportData)               => http.post('/tools/import/preview', exportData).then(r => r.data)
export const applyToolImport   = (exportData, decisions)    => http.post('/tools/import/apply', { export_data: exportData, decisions }).then(r => r.data)

// ── Agents ─────────────────────────────────────────────────
export const getAgents     = ()           => http.get('/agents').then(r => r.data)
export const createAgent   = (data)       => http.post('/agents', data).then(r => r.data)
export const updateAgent   = (id, data)   => http.put(`/agents/${id}`, data).then(r => r.data)
export const deleteAgent   = (id)         => http.delete(`/agents/${id}`).then(r => r.data)
export const exportAgent        = (id)                       => http.get(`/agents/${id}/export`).then(r => r.data)
export const previewAgentImport = (exportData)               => http.post('/agents/import/preview', exportData).then(r => r.data)
export const applyAgentImport   = (exportData, decisions)    => http.post('/agents/import/apply', { export_data: exportData, decisions }).then(r => r.data)

export const getAgentTools      = (agentId)             => http.get(`/agents/${agentId}/tools`).then(r => r.data)
export const setAgentTools      = (agentId, toolIds)    => http.put(`/agents/${agentId}/tools`, { tool_ids: toolIds }).then(r => r.data)
export const addAgentTool       = (agentId, toolId)     => http.post(`/agents/${agentId}/tools/${toolId}`).then(r => r.data)
export const removeAgentTool    = (agentId, toolId)     => http.delete(`/agents/${agentId}/tools/${toolId}`).then(r => r.data)
export const setAgentToolConfig = (agentId, toolId, cfg) => http.put(`/agents/${agentId}/tools/${toolId}/config`, { config: cfg }).then(r => r.data)

// ── Workflows ──────────────────────────────────────────────
export const getWorkflows   = ()         => http.get('/workflows').then(r => r.data)
export const getWorkflow    = (id)       => http.get(`/workflows/${id}`).then(r => r.data)
export const createWorkflow = (data)     => http.post('/workflows', data).then(r => r.data)
export const updateWorkflow = (id, data) => http.put(`/workflows/${id}`, data).then(r => r.data)
export const deleteWorkflow = (id)       => http.delete(`/workflows/${id}`).then(r => r.data)

// ── Library ────────────────────────────────────────────────
export const getLibraryWorkflows = () => http.get('/library/workflows').then(r => r.data)
export const getLibraryAgents    = () => http.get('/library/agents').then(r => r.data)
export const cloneWorkflow = (id)      => http.post(`/library/workflows/${id}/clone`).then(r => r.data)
export const exportTemplate        = (id)                    => http.get(`/library/workflows/${id}/export`).then(r => r.data)
export const previewTemplateImport = (exportData)            => http.post('/library/workflows/import/preview', exportData).then(r => r.data)
export const applyTemplateImport   = (exportData, decisions) => http.post('/library/workflows/import/apply', { export_data: exportData, decisions }).then(r => r.data)

// ── Execution ──────────────────────────────────────────────
export const getExecutions = (params = {}) => http.get('/execution', { params }).then(r => r.data)
export const runExecution  = (workflowId, trigger = null) =>
  http.post(`/execution/${workflowId}/run`, trigger).then(r => r.data)
export const getExecution  = (execId)      => http.get(`/execution/${execId}`).then(r => r.data)

// ── Triggers ───────────────────────────────────────────────
export const listWorkflowTriggers = (workflowId) =>
  http.get(`/triggers/workflow/${workflowId}`).then(r => r.data)
export const simulateTrigger = (workflowId, body) =>
  http.post(`/triggers/simulate/${workflowId}`, body).then(r => r.data)
export const triggerBaseUrl = () => BASE_URL

// ── AI Chat ────────────────────────────────────────────────
export const sendAIMessage = (message, workflowContext, history) =>
  http.post('/ai/chat', { message, workflow_context: workflowContext, history: history.slice(-10) }).then(r => r.data)

// ── Data Models ────────────────────────────────────────────
export const getDataModels    = ()           => http.get('/data-models').then(r => r.data)
export const getDataModel     = (id)         => http.get(`/data-models/${id}`).then(r => r.data)
export const createDataModel  = (data)       => http.post('/data-models', data).then(r => r.data)
export const updateDataModel  = (id, data)   => http.put(`/data-models/${id}`, data).then(r => r.data)
export const deleteDataModel  = (id)         => http.delete(`/data-models/${id}`).then(r => r.data)
export const importDataModel  = (jsonSchema) => http.post('/data-models/import', { json_schema: jsonSchema }).then(r => r.data)
export const suggestDataModel = (name, desc) => http.post('/data-models/ai-suggest', { workflow_name: name, workflow_description: desc }).then(r => r.data)

// ── Workflow Associations ──────────────────────────────────
export const getWorkflowAssociation    = (workflowId) => http.get(`/associations/workflow/${workflowId}`).then(r => r.data)
export const upsertAssociation         = (data)        => http.post('/associations', data).then(r => r.data)
export const deleteWorkflowAssociation = (workflowId)  => http.delete(`/associations/workflow/${workflowId}`).then(r => r.data)

// ── Users ──────────────────────────────────────────────────
export const getUsers      = (params = {}) => http.get('/users', { params }).then(r => r.data)
export const getUser       = (id)          => http.get(`/users/${id}`).then(r => r.data)
export const createUser    = (data)        => http.post('/users', data).then(r => r.data)
export const updateUser    = (id, data)    => http.put(`/users/${id}`, data).then(r => r.data)
export const deleteUser    = (id)          => http.delete(`/users/${id}`).then(r => r.data)
export const toggleUserStatus = (id, is_active) => http.patch(`/users/${id}/status`, null, { params: { is_active } }).then(r => r.data)
export const changePassword   = (id, newPassword) => http.patch(`/users/${id}/password`, null, { params: { new_password: newPassword } }).then(r => r.data)

// ── Groups ─────────────────────────────────────────────────
export const getGroups     = (params = {}) => http.get('/groups', { params }).then(r => r.data)
export const getGroup      = (id)          => http.get(`/groups/${id}`).then(r => r.data)
export const createGroup   = (data)        => http.post('/groups', data).then(r => r.data)
export const updateGroup   = (id, data)    => http.put(`/groups/${id}`, data).then(r => r.data)
export const deleteGroup   = (id)          => http.delete(`/groups/${id}`).then(r => r.data)
export const addGroupMember    = (gid, uid) => http.post(`/groups/${gid}/members/${uid}`).then(r => r.data)
export const removeGroupMember = (gid, uid) => http.delete(`/groups/${gid}/members/${uid}`).then(r => r.data)

// ── Projects ───────────────────────────────────────────────
export const getProjects   = (params = {}) => http.get('/projects', { params }).then(r => r.data)
export const getProject    = (id)          => http.get(`/projects/${id}`).then(r => r.data)
export const createProject = (data)        => http.post('/projects', data).then(r => r.data)
export const updateProject = (id, data)    => http.put(`/projects/${id}`, data).then(r => r.data)
export const deleteProject = (id)          => http.delete(`/projects/${id}`).then(r => r.data)
export const addProjectWorkflow    = (pid, wid) => http.post(`/projects/${pid}/workflows/${wid}`).then(r => r.data)
export const removeProjectWorkflow = (pid, wid) => http.delete(`/projects/${pid}/workflows/${wid}`).then(r => r.data)
export const addProjectUser        = (pid, uid) => http.post(`/projects/${pid}/users/${uid}`).then(r => r.data)
export const removeProjectUser     = (pid, uid) => http.delete(`/projects/${pid}/users/${uid}`).then(r => r.data)
export const exportCustomer        = (pid)      => http.get(`/projects/${pid}/export`).then(r => r.data)
export const previewCustomerImport = (exportData) => http.post('/projects/import/preview', exportData).then(r => r.data)
export const applyCustomerImport   = (exportData, decisions) => http.post('/projects/import/apply', { export_data: exportData, decisions }).then(r => r.data)

// ── Metrics ────────────────────────────────────────────────
export const getDashboardMetrics = (days, workflowId) => {
  const params = days && days !== 'all' ? { days: parseInt(days) } : {}
  if (workflowId) params.workflow_id = workflowId
  return http.get('/metrics/dashboard', { params }).then(r => r.data)
}
export const getDashboardDetail  = (params = {}) => http.get('/metrics/dashboard/detail', { params }).then(r => r.data)
export const getReport           = (report_type, params = {}) => http.get('/metrics/reports', { params: { report_type, ...params } }).then(r => r.data)

// ── Audit Logs ─────────────────────────────────────────────
export const getAuditLogs   = (params = {}) => http.get('/audit-logs', { params }).then(r => r.data)
export const getAuditSummary = ()           => http.get('/audit-logs/summary').then(r => r.data)

// ── Reviews ────────────────────────────────────────────────
export const getReviews     = (params = {}) => http.get('/reviews', { params }).then(r => r.data)
export const submitReview   = (data)        => http.post('/reviews', data).then(r => r.data)
export const approveReview  = (id, notes)   => http.put(`/reviews/${id}/approve`, { notes }).then(r => r.data)
export const rejectReview   = (id, notes)   => http.put(`/reviews/${id}/reject`, { notes }).then(r => r.data)
export const deleteReview   = (id)          => http.delete(`/reviews/${id}`).then(r => r.data)
