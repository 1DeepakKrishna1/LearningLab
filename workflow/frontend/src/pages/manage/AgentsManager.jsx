import { useState, useEffect } from 'react'
import {
  getAgents, createAgent, updateAgent, deleteAgent, submitReview,
  exportAgent, previewAgentImport, applyAgentImport,
} from '../../api/api'
import {
  Bot, Plus, Pencil, Trash2, X, Loader2, AlertCircle, Search, ChevronDown, Wrench,
  Download, Upload,
} from 'lucide-react'
import PropertiesEditor from './PropertiesEditor'
import LibraryImportModal from './LibraryImportModal'

// ── Invoke parameter editor (standalone, no workflow context) ──
const WF_VAR_OPTIONS = [
  { value: '{{wf.status}}',      label: 'wf.status' },
  { value: '{{wf.token_limit}}', label: 'wf.token_limit' },
  { value: '{{wf.timetaken}}',   label: 'wf.timetaken' },
]
const VALUE_TYPE_LABELS = {
  constant:   'Constant',
  workflow:   'Workflow',
  tool:       'Tool Output',
  data_model: 'Data Model',
}

function InvokeValueInput({ param, onChange }) {
  const { value_type, value } = param
  if (value_type === 'constant') {
    return (
      <input
        type="text"
        value={value}
        onChange={e => onChange({ value: e.target.value })}
        placeholder='e.g. 123 or "Approved"'
        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
      />
    )
  }
  if (value_type === 'workflow') {
    return (
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={e => onChange({ value: e.target.value })}
          placeholder="{{wf.status}}"
          className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
        />
        <select
          defaultValue=""
          onChange={e => { if (e.target.value) { onChange({ value: e.target.value }); e.target.value = '' } }}
          className="bg-slate-800 border border-slate-600 rounded-lg px-2 py-1.5 text-xs text-slate-400 focus:outline-none focus:border-indigo-500"
          title="Insert variable"
        >
          <option value="">↗</option>
          {WF_VAR_OPTIONS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
        </select>
      </div>
    )
  }
  // tool / data_model — free text with format hint
  const placeholder = value_type === 'tool'
    ? '{{tool.AgentName.output}}'
    : '{{EntityName.field_name}}'
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange({ value: e.target.value })}
      placeholder={placeholder}
      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
    />
  )
}

function InvokeParamList({ section, params, onChange }) {
  function add() {
    onChange([...params, { name: '', value_type: 'constant', value: '' }])
  }
  function update(idx, patch) {
    const list = [...params]
    list[idx] = { ...list[idx], ...patch }
    onChange(list)
  }
  function remove(idx) {
    const list = [...params]
    list.splice(idx, 1)
    onChange(list)
  }
  return (
    <div className="space-y-3">
      {params.map((param, idx) => (
        <div key={idx} className="bg-slate-900 border border-slate-700 rounded-lg p-3 space-y-2">
          <div className="flex gap-2 items-start">
            <div className="flex-1">
              <label className="block text-xs text-slate-400 mb-1">Name</label>
              <input
                type="text"
                value={param.name}
                onChange={e => update(idx, { name: e.target.value })}
                placeholder="parameter_name"
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-slate-400 mb-1">
                {section === 'input' ? 'Source' : 'Target'}
              </label>
              <select
                value={param.value_type}
                onChange={e => update(idx, { value_type: e.target.value, value: '' })}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                {Object.entries(VALUE_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => remove(idx)}
              className="mt-6 p-1.5 text-slate-500 hover:text-red-400 transition-colors"
            >
              <X size={14} />
            </button>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Value</label>
            <InvokeValueInput param={param} onChange={patch => update(idx, patch)} />
          </div>
          {param.name && (
            <p className="text-[11px] text-indigo-400/60 font-mono">
              Reference: {'{{'}wf.{param.name}{'}}'}
            </p>
          )}
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="w-full flex items-center justify-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300 border border-dashed border-indigo-700/40 hover:border-indigo-500/60 rounded-lg py-2 transition-colors"
      >
        <Plus size={14} />
        Add {section === 'input' ? 'Input' : 'Output'} Parameter
      </button>
    </div>
  )
}

const AGENT_TYPES = [
  'automatic', 'role_based', 'human_in_the_loop', 'human_review', 'conditional', 'parallel',
  'prompt_agent', 'react_agent', 'reflection_agent', 'guardrails', 'orchestrator',
  'supervisor', 'ai_agent'
]

const TYPE_COLORS = {
  automatic: 'bg-indigo-500/20 text-indigo-400',
  role_based: 'bg-emerald-500/20 text-emerald-400',
  human_in_the_loop: 'bg-amber-500/20 text-amber-400',
  human_review: 'bg-sky-500/20 text-sky-400',
  conditional: 'bg-orange-500/20 text-orange-400',
  parallel: 'bg-purple-500/20 text-purple-400',
  prompt_agent: 'bg-cyan-500/20 text-cyan-400',
  react_agent: 'bg-blue-500/20 text-blue-400',
  reflection_agent: 'bg-rose-500/20 text-rose-400',
  guardrails: 'bg-red-500/20 text-red-400',
  orchestrator: 'bg-violet-500/20 text-violet-400',
  supervisor: 'bg-teal-500/20 text-teal-400',
  ai_agent: 'bg-sky-500/20 text-sky-400',
}

const REVIEW_COLORS = {
  pending: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  approved: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  rejected: 'bg-red-500/20 text-red-400 border border-red-500/30',
}

const COLOR_SWATCHES = [
  { label: 'Indigo', value: '#6366f1', bg: 'bg-indigo-500' },
  { label: 'Emerald', value: '#10b981', bg: 'bg-emerald-500' },
  { label: 'Amber', value: '#f59e0b', bg: 'bg-amber-500' },
  { label: 'Orange', value: '#f97316', bg: 'bg-orange-500' },
  { label: 'Purple', value: '#a855f7', bg: 'bg-purple-500' },
]

const EMPTY_INVOKE = { input_parameters: [], output_parameters: [] }
const EMPTY_FORM = { name: '', description: '', type: 'automatic', color: '#6366f1', properties: {}, invoke: EMPTY_INVOKE }

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 shrink-0">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

function ConfirmDelete({ agent, onConfirm, onClose, loading }) {
  return (
    <Modal title="Delete Agent" onClose={onClose}>
      <p className="text-slate-300 text-sm mb-4">
        Are you sure you want to delete <span className="text-white font-medium">"{agent.name}"</span>? This action cannot be undone.
      </p>
      <div className="flex gap-3 justify-end">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Cancel
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {loading && <Loader2 size={14} className="animate-spin" />}
          Delete
        </button>
      </div>
    </Modal>
  )
}

function AgentForm({ initial, onSave, onClose, saving }) {
  const [form, setForm] = useState({
    ...EMPTY_FORM,
    ...(initial && {
      name: initial.name || '',
      description: initial.description || '',
      type: initial.type || 'automatic',
      color: initial.color || '#6366f1',
      properties: initial.properties || {},
      invoke: initial.invoke || EMPTY_INVOKE,
    }),
  })
  const [activeTab, setActiveTab] = useState('details')

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  const invokeCount = (form.invoke?.input_parameters?.length || 0) + (form.invoke?.output_parameters?.length || 0)

  return (
    <form onSubmit={e => { e.preventDefault(); onSave(form) }}>
      {/* Tab navigation */}
      <div className="flex border-b border-slate-700 mb-5 -mt-1">
        {['details', 'invoke'].map(t => (
          <button
            key={t}
            type="button"
            onClick={() => setActiveTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors flex items-center gap-1.5 ${
              activeTab === t
                ? 'text-indigo-300 border-b-2 border-indigo-500'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t}
            {t === 'invoke' && invokeCount > 0 && (
              <span className="text-[10px] bg-violet-600/40 text-violet-300 rounded-full px-1.5 py-0.5">
                {invokeCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Details tab */}
      {activeTab === 'details' && (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Name <span className="text-red-400">*</span></label>
            <input
              required
              value={form.name}
              onChange={e => set('name', e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              placeholder="Agent name"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={e => set('description', e.target.value)}
              rows={3}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
              placeholder="Describe this agent's purpose…"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Type</label>
            <div className="relative">
              <select
                value={form.type}
                onChange={e => set('type', e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 appearance-none"
              >
                {AGENT_TYPES.map(t => (
                  <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Color</label>
            <div className="flex gap-2">
              {COLOR_SWATCHES.map(sw => (
                <button
                  key={sw.value}
                  type="button"
                  onClick={() => set('color', sw.value)}
                  title={sw.label}
                  className={`w-8 h-8 rounded-full ${sw.bg} transition-transform ${
                    form.color === sw.value ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110' : 'hover:scale-105'
                  }`}
                />
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Properties</label>
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
              <PropertiesEditor value={form.properties} onChange={v => set('properties', v)} />
            </div>
          </div>
        </div>
      )}

      {/* Invoke tab */}
      {activeTab === 'invoke' && (
        <div className="space-y-5">
          <div className="text-xs text-slate-400 bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 leading-relaxed">
            Define the input and output parameters for this agent's invocation contract.
            When placed in a workflow, parameter values are resolved at runtime from the configured sources.
            Reference any parameter by name using <span className="font-mono text-indigo-400">{'{{'}wf.name{'}}'}</span>.
          </div>

          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-3">
              Input Parameters
              <span className="ml-2 text-xs text-slate-500 font-normal">
                ({form.invoke?.input_parameters?.length || 0})
              </span>
            </h3>
            <InvokeParamList
              section="input"
              params={form.invoke?.input_parameters || []}
              onChange={list => set('invoke', { ...form.invoke, input_parameters: list })}
            />
          </div>

          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-3">
              Output Parameters
              <span className="ml-2 text-xs text-slate-500 font-normal">
                ({form.invoke?.output_parameters?.length || 0})
              </span>
            </h3>
            <InvokeParamList
              section="output"
              params={form.invoke?.output_parameters || []}
              onChange={list => set('invoke', { ...form.invoke, output_parameters: list })}
            />
          </div>
        </div>
      )}

      <div className="flex gap-3 justify-end mt-6 pt-4 border-t border-slate-700">
        <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {saving && <Loader2 size={14} className="animate-spin" />}
          {initial ? 'Save Changes' : 'Create Agent'}
        </button>
      </div>
    </form>
  )
}

export default function AgentsManager() {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [reviewFilter, setReviewFilter] = useState('all')
  const [modalState, setModalState] = useState(null)
  const [saving, setSaving] = useState(false)
  const [exportingId, setExportingId] = useState(null)

  useEffect(() => { loadAgents() }, [])

  async function loadAgents() {
    try {
      setLoading(true)
      const data = await getAgents()
      setAgents(data)
    } catch {
      setError('Failed to load agents.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(form) {
    try {
      setSaving(true)
      if (modalState.type === 'add') {
        const created = await createAgent(form)
        await submitReview({ type: 'agent', item_id: created.id, item_name: created.name, item_data: created })
      } else {
        await updateAgent(modalState.agent.id, form)
      }
      setModalState(null)
      loadAgents()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    try {
      setSaving(true)
      await deleteAgent(modalState.agent.id)
      setModalState(null)
      loadAgents()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  async function handleExport(agent) {
    try {
      setExportingId(agent.id)
      const data = await exportAgent(agent.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `agent_${agent.name.replace(/\s+/g, '_')}_${data.exportId.slice(0, 8)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch { /* silently ignore */ } finally { setExportingId(null) }
  }

  const REVIEW_TABS = ['all', 'approved', 'pending', 'rejected']

  const filtered = agents.filter(a => {
    const matchSearch = !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      (a.description || '').toLowerCase().includes(search.toLowerCase())
    const matchReview = reviewFilter === 'all' || a.review_status === reviewFilter
    return matchSearch && matchReview
  })

  const counts = REVIEW_TABS.slice(1).reduce((acc, s) => {
    acc[s] = agents.filter(a => a.review_status === s).length
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Agents Library</h1>
          <p className="text-slate-400 text-sm mt-1">Manage AI agents for your workflows.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setModalState({ type: 'import' })}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Upload size={16} /> Import Agent
          </button>
          <button
            onClick={() => setModalState({ type: 'add' })}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Plus size={16} /> Add Agent
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search agents…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded-lg p-1">
          {REVIEW_TABS.map(s => (
            <button
              key={s}
              onClick={() => setReviewFilter(s)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors flex items-center gap-1.5 ${
                reviewFilter === s ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {s === 'all' ? 'All' : s}
              {s !== 'all' && counts[s] > 0 && (
                <span className="bg-slate-600 text-slate-300 rounded-full px-1.5 py-0 text-[10px]">{counts[s]}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading agents…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10"><AlertCircle size={18} /> {error}</div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Type</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Description</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Tools</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Review Status</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center text-slate-500 py-10">
                    <Bot size={32} className="mx-auto mb-2 opacity-30" />
                    No agents found.
                  </td>
                </tr>
              ) : (
                filtered.map(agent => (
                  <tr key={agent.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: agent.color || '#6366f1' }}
                        />
                        <span className="font-medium text-white">{agent.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[agent.type] || 'bg-slate-700 text-slate-300'}`}>
                        {agent.type?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate hidden md:table-cell">{agent.description || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-slate-400 text-xs">
                        <Wrench size={12} />
                        {(agent.tools || []).length}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${REVIEW_COLORS[agent.review_status] || REVIEW_COLORS.pending}`}>
                        {agent.review_status || 'pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleExport(agent)}
                          disabled={exportingId === agent.id}
                          className="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 rounded transition-colors disabled:opacity-50"
                          title="Export"
                        >
                          {exportingId === agent.id
                            ? <Loader2 size={14} className="animate-spin" />
                            : <Download size={14} />}
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'edit', agent })}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'delete', agent })}
                          className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      {modalState?.type === 'add' && (
        <Modal title="Add Agent" onClose={() => setModalState(null)}>
          <AgentForm onSave={handleSave} onClose={() => setModalState(null)} saving={saving} />
        </Modal>
      )}
      {modalState?.type === 'edit' && (
        <Modal title="Edit Agent" onClose={() => setModalState(null)}>
          <AgentForm
            initial={modalState.agent}
            onSave={handleSave}
            onClose={() => setModalState(null)}
            saving={saving}
          />
        </Modal>
      )}
      {modalState?.type === 'delete' && (
        <ConfirmDelete
          agent={modalState.agent}
          onConfirm={handleDelete}
          onClose={() => setModalState(null)}
          loading={saving}
        />
      )}
      {modalState?.type === 'import' && (
        <LibraryImportModal
          kind="agent"
          previewFn={previewAgentImport}
          applyFn={applyAgentImport}
          onClose={() => setModalState(null)}
          onImported={loadAgents}
        />
      )}
    </div>
  )
}
