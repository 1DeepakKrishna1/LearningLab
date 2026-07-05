import { useState, useEffect, useRef } from 'react'
import {
  getProjects, createProject, updateProject, deleteProject,
  addProjectWorkflow, removeProjectWorkflow,
  addProjectUser, removeProjectUser,
  getWorkflows, getUsers,
  exportCustomer, previewCustomerImport, applyCustomerImport,
} from '../../api/api'
import {
  FolderOpen, Plus, Pencil, Trash2, X, Loader2, AlertCircle, Search,
  Workflow, Users, Settings, ChevronDown, ExternalLink,
  Download, Upload, CheckCircle2, Database, Link,
} from 'lucide-react'

function Modal({ title, onClose, children, size = 'max-w-lg' }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className={`bg-slate-800 border border-slate-700 rounded-xl w-full ${size} shadow-2xl max-h-[90vh] flex flex-col`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 flex-shrink-0">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-5 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  )
}

function makeLaunchUrl(name) {
  return `https://www.bing.com/search?q=${encodeURIComponent(name)}`
}

function ProjectForm({ initial, onSave, onClose, saving }) {
  const [form, setForm] = useState({
    name: initial?.name || '',
    description: initial?.description || '',
    launchurl: initial?.launchurl || (initial?.name ? makeLaunchUrl(initial.name) : ''),
  })
  const [urlTouched, setUrlTouched] = useState(!!initial?.launchurl)

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  function handleNameChange(v) {
    setForm(f => ({
      ...f,
      name: v,
      launchurl: urlTouched ? f.launchurl : makeLaunchUrl(v),
    }))
  }

  return (
    <form onSubmit={e => { e.preventDefault(); onSave(form) }}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Name <span className="text-red-400">*</span></label>
          <input
            required
            value={form.name}
            onChange={e => handleNameChange(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            placeholder="Customer name"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={e => set('description', e.target.value)}
            rows={3}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            placeholder="Describe this customer…"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Launch URL</label>
          <input
            value={form.launchurl}
            onChange={e => { setUrlTouched(true); set('launchurl', e.target.value) }}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            placeholder="https://…"
          />
          <p className="text-xs text-slate-500 mt-1">Auto-generated from name. Edit to override.</p>
        </div>
      </div>
      <div className="flex gap-3 justify-end mt-6">
        <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {saving && <Loader2 size={14} className="animate-spin" />}
          {initial ? 'Save Changes' : 'Create Customer'}
        </button>
      </div>
    </form>
  )
}

function ManageProjectModal({ project, allWorkflows, allUsers, onClose, onChanged }) {
  const [tab, setTab] = useState('workflows')
  const [wfIds, setWfIds] = useState(project.workflow_ids || [])
  const [userIds, setUserIds] = useState(project.user_ids || [])
  const [actionId, setActionId] = useState(null)
  const [selectedWf, setSelectedWf] = useState('')
  const [selectedUser, setSelectedUser] = useState('')

  const currentWorkflows = allWorkflows.filter(w => wfIds.includes(w.id))
  const availableWorkflows = allWorkflows.filter(w => !wfIds.includes(w.id))
  const currentUsers = allUsers.filter(u => userIds.includes(u.id))
  const availableUsers = allUsers.filter(u => !userIds.includes(u.id))

  async function removeWf(wid) {
    try {
      setActionId(wid)
      await removeProjectWorkflow(project.id, wid)
      setWfIds(prev => prev.filter(id => id !== wid))
      onChanged()
    } catch { /* silently ignore */ } finally { setActionId(null) }
  }

  async function addWf() {
    if (!selectedWf) return
    try {
      setActionId('add-wf')
      await addProjectWorkflow(project.id, selectedWf)
      setWfIds(prev => [...prev, selectedWf])
      setSelectedWf('')
      onChanged()
    } catch { /* silently ignore */ } finally { setActionId(null) }
  }

  async function removeUser(uid) {
    try {
      setActionId(uid)
      await removeProjectUser(project.id, uid)
      setUserIds(prev => prev.filter(id => id !== uid))
      onChanged()
    } catch { /* silently ignore */ } finally { setActionId(null) }
  }

  async function addUser() {
    if (!selectedUser) return
    try {
      setActionId('add-user')
      await addProjectUser(project.id, selectedUser)
      setUserIds(prev => [...prev, selectedUser])
      setSelectedUser('')
      onChanged()
    } catch { /* silently ignore */ } finally { setActionId(null) }
  }

  return (
    <Modal title={`Manage — ${project.name}`} onClose={onClose} size="max-w-2xl">
      <div className="flex gap-1 bg-slate-900 border border-slate-700 rounded-lg p-1 mb-4 w-fit">
        {['workflows', 'users'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-xs font-medium capitalize transition-colors flex items-center gap-1.5 ${
              tab === t ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {t === 'workflows' ? <Workflow size={12} /> : <Users size={12} />}
            {t === 'workflows' ? `Workflows (${wfIds.length})` : `Users (${userIds.length})`}
          </button>
        ))}
      </div>

      {tab === 'workflows' && (
        <div>
          <div className="flex gap-2 mb-3">
            <div className="relative flex-1">
              <select
                value={selectedWf}
                onChange={e => setSelectedWf(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 appearance-none"
              >
                <option value="">Select a workflow to add…</option>
                {availableWorkflows.map(w => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
              <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
            <button
              onClick={addWf}
              disabled={!selectedWf || actionId === 'add-wf'}
              className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-40 flex items-center gap-1"
            >
              {actionId === 'add-wf' ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />}
              Add
            </button>
          </div>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {currentWorkflows.length === 0 ? (
              <p className="text-slate-500 text-sm py-4 text-center">No workflows assigned to this project.</p>
            ) : currentWorkflows.map(w => (
              <div key={w.id} className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2.5">
                <div>
                  <p className="text-sm text-white font-medium">{w.name}</p>
                  <p className="text-xs text-slate-500">{w.status || 'draft'}</p>
                </div>
                <button
                  onClick={() => removeWf(w.id)}
                  disabled={actionId === w.id}
                  className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
                >
                  {actionId === w.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'users' && (
        <div>
          <div className="flex gap-2 mb-3">
            <div className="relative flex-1">
              <select
                value={selectedUser}
                onChange={e => setSelectedUser(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 appearance-none"
              >
                <option value="">Select a user to add…</option>
                {availableUsers.map(u => (
                  <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
                ))}
              </select>
              <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
            <button
              onClick={addUser}
              disabled={!selectedUser || actionId === 'add-user'}
              className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-40 flex items-center gap-1"
            >
              {actionId === 'add-user' ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />}
              Add
            </button>
          </div>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {currentUsers.length === 0 ? (
              <p className="text-slate-500 text-sm py-4 text-center">No users assigned to this project.</p>
            ) : currentUsers.map(u => (
              <div key={u.id} className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2.5">
                <div>
                  <p className="text-sm text-white font-medium">{u.name}</p>
                  <p className="text-xs text-slate-500">{u.email}</p>
                </div>
                <button
                  onClick={() => removeUser(u.id)}
                  disabled={actionId === u.id}
                  className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
                >
                  {actionId === u.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-end mt-4 pt-3 border-t border-slate-700">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Done
        </button>
      </div>
    </Modal>
  )
}

// ── Entity-level action selector ───────────────────────────────────────────

const ACTION_LABELS = { add: 'Add', update: 'Update', skip: 'Skip' }
const ALLOWED_ACTIONS = { new: ['add', 'skip'], exists: ['update', 'skip'] }

function ActionSelector({ value, onChange, status }) {
  const options = ALLOWED_ACTIONS[status] || ['add', 'update', 'skip']
  return (
    <div className="flex gap-1">
      {options.map(opt => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
            value === opt
              ? opt === 'skip'
                ? 'bg-slate-600 text-slate-200'
                : opt === 'update'
                  ? 'bg-amber-600 text-white'
                  : 'bg-emerald-600 text-white'
              : 'bg-slate-700 text-slate-400 hover:text-white'
          }`}
        >
          {ACTION_LABELS[opt]}
        </button>
      ))}
    </div>
  )
}

function StatusBadge({ status }) {
  return status === 'exists'
    ? <span className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">Exists</span>
    : <span className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">New</span>
}

// ── Entity group inside the import decisions view ──────────────────────────

function EntityGroup({ title, icon: Icon, color, entities, decisions, onActionChange, onBulkAction }) {
  if (entities.length === 0) return null

  function handleBulk(action) {
    const map = Object.fromEntries(entities.map(e => {
      if (action === 'skip') return [e.id, 'skip']
      if (action === 'add' && e._status === 'new') return [e.id, 'add']
      if (action === 'update' && e._status === 'exists') return [e.id, 'update']
      return [e.id, decisions[e.id]]
    }))
    onBulkAction(map)
  }

  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={14} className={color} />
          <span className="text-sm font-medium text-white">{title} ({entities.length})</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-500 mr-1">All:</span>
          {['add', 'update', 'skip'].map(opt => (
            <button
              key={opt}
              onClick={() => handleBulk(opt)}
              className="px-2 py-0.5 rounded text-xs text-slate-400 hover:text-white bg-slate-700 hover:bg-slate-600 transition-colors"
            >
              {ACTION_LABELS[opt]}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-1">
        {entities.map(entity => (
          <div key={entity.id} className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2">
            <div className="flex items-center gap-2 min-w-0">
              <StatusBadge status={entity._status} />
              <span className="text-sm text-slate-200 truncate">{entity.name}</span>
            </div>
            <ActionSelector
              value={decisions[entity.id] || 'skip'}
              onChange={v => onActionChange(entity.id, v)}
              status={entity._status}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Import Customer Modal ──────────────────────────────────────────────────

function initDecisions(preview) {
  const decide = s => s === 'exists' ? 'update' : 'add'
  return {
    customer:              decide(preview.customer._status),
    workflows:             Object.fromEntries(preview.workflows.map(w => [w.id, decide(w._status)])),
    users:                 Object.fromEntries(preview.users.map(u => [u.id, decide(u._status)])),
    agents:                Object.fromEntries(preview.agents.map(a => [a.id, decide(a._status)])),
    tools:                 Object.fromEntries(preview.tools.map(t => [t.id, decide(t._status)])),
    data_models:           Object.fromEntries((preview.data_models || []).map(dm => [dm.id, decide(dm._status)])),
    workflow_associations: Object.fromEntries((preview.workflow_associations || []).map(a => [a.id, decide(a._status)])),
  }
}

function ImportCustomerModal({ onClose, onImported }) {
  const fileRef = useRef(null)
  const [step, setStep] = useState('upload')   // upload | decisions | applying | done
  const [exportData, setExportData] = useState(null)
  const [preview, setPreview] = useState(null)
  const [decisions, setDecisions] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  async function handleFile(file) {
    if (!file) return
    setError(null)
    try {
      const text = await file.text()
      const parsed = JSON.parse(text)
      // Basic validation
      for (const key of ['exportId', 'customer', 'workflows', 'users', 'agents', 'tools', 'data_models', 'workflow_associations']) {
        if (!(key in parsed)) throw new Error(`Missing key: "${key}" — not a valid customer export file.`)
      }
      setLoading(true)
      const prev = await previewCustomerImport(parsed)
      setExportData(parsed)
      setPreview(prev)
      setDecisions(initDecisions(prev))
      setStep('decisions')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to parse file.')
    } finally {
      setLoading(false)
    }
  }

  function onFilePick(e) { handleFile(e.target.files?.[0]) }
  function onDrop(e) {
    e.preventDefault(); setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  function setEntityAction(group, id, action) {
    setDecisions(d => ({ ...d, [group]: { ...d[group], [id]: action } }))
  }

  function setBulkAction(group, newMap) {
    setDecisions(d => ({ ...d, [group]: newMap }))
  }

  async function handleApply() {
    setStep('applying')
    setError(null)
    try {
      const res = await applyCustomerImport(exportData, decisions)
      setResult(res)
      setStep('done')
      onImported()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Import failed.')
      setStep('decisions')
    }
  }

  const totalEntities = preview
    ? 1 + preview.workflows.length + preview.users.length + preview.agents.length + preview.tools.length + (preview.data_models || []).length + (preview.workflow_associations || []).length
    : 0

  return (
    <Modal title="Import Customer" onClose={onClose} size="max-w-2xl">
      {/* ── Step: Upload ── */}
      {step === 'upload' && (
        <div>
          <p className="text-sm text-slate-400 mb-4">
            Select a customer export JSON file to import. The system will show you what will be added or updated before applying changes.
          </p>
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center cursor-pointer transition-colors ${
              dragOver ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-600 hover:border-slate-500 hover:bg-slate-700/30'
            }`}
          >
            <Upload size={32} className="text-slate-400 mb-3" />
            <p className="text-sm text-slate-300 font-medium">Drop your export file here</p>
            <p className="text-xs text-slate-500 mt-1">or click to browse</p>
            <p className="text-xs text-slate-600 mt-2">Accepts .json export files only</p>
          </div>
          <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={onFilePick} />
          {loading && (
            <div className="flex items-center gap-2 justify-center mt-4 text-slate-400 text-sm">
              <Loader2 size={16} className="animate-spin" /> Validating file…
            </div>
          )}
          {error && (
            <div className="flex items-start gap-2 mt-4 text-red-400 text-sm bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
              <AlertCircle size={15} className="mt-0.5 flex-shrink-0" /> {error}
            </div>
          )}
          <div className="flex justify-end mt-5">
            <button onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ── Step: Decisions ── */}
      {step === 'decisions' && preview && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-slate-300">
                <span className="text-white font-medium">{preview.customer.name}</span>
                <span className="text-slate-500 ml-2 text-xs">Export ID: {preview.exportId}</span>
              </p>
              <p className="text-xs text-slate-500 mt-0.5">{totalEntities} entities found — choose an action for each.</p>
            </div>
          </div>

          {/* Customer row */}
          <div className="mb-5">
            <div className="flex items-center gap-2 mb-2">
              <FolderOpen size={14} className="text-indigo-400" />
              <span className="text-sm font-medium text-white">Customer</span>
            </div>
            <div className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2">
              <div className="flex items-center gap-2">
                <StatusBadge status={preview.customer._status} />
                <span className="text-sm text-slate-200">{preview.customer.name}</span>
              </div>
              <ActionSelector
                value={decisions.customer}
                onChange={v => setDecisions(d => ({ ...d, customer: v }))}
                status={preview.customer._status}
              />
            </div>
          </div>

          <EntityGroup
            title="Workflows" icon={Workflow} color="text-indigo-400"
            entities={preview.workflows} decisions={decisions.workflows || {}}
            onActionChange={(id, v) => setEntityAction('workflows', id, v)}
            onBulkAction={v => setBulkAction('workflows', v)}
          />
          <EntityGroup
            title="Users" icon={Users} color="text-sky-400"
            entities={preview.users} decisions={decisions.users || {}}
            onActionChange={(id, v) => setEntityAction('users', id, v)}
            onBulkAction={v => setBulkAction('users', v)}
          />
          <EntityGroup
            title="Agents" icon={Settings} color="text-purple-400"
            entities={preview.agents} decisions={decisions.agents || {}}
            onActionChange={(id, v) => setEntityAction('agents', id, v)}
            onBulkAction={v => setBulkAction('agents', v)}
          />
          <EntityGroup
            title="Tools" icon={Settings} color="text-emerald-400"
            entities={preview.tools} decisions={decisions.tools || {}}
            onActionChange={(id, v) => setEntityAction('tools', id, v)}
            onBulkAction={v => setBulkAction('tools', v)}
          />
          <EntityGroup
            title="Data Models" icon={Database} color="text-cyan-400"
            entities={preview.data_models || []} decisions={decisions.data_models || {}}
            onActionChange={(id, v) => setEntityAction('data_models', id, v)}
            onBulkAction={v => setBulkAction('data_models', v)}
          />
          <EntityGroup
            title="Workflow Associations" icon={Link} color="text-violet-400"
            entities={preview.workflow_associations || []} decisions={decisions.workflow_associations || {}}
            onActionChange={(id, v) => setEntityAction('workflow_associations', id, v)}
            onBulkAction={v => setBulkAction('workflow_associations', v)}
          />

          {error && (
            <div className="flex items-start gap-2 mb-3 text-red-400 text-sm bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
              <AlertCircle size={15} className="mt-0.5 flex-shrink-0" /> {error}
            </div>
          )}

          <div className="flex gap-3 justify-end pt-3 border-t border-slate-700">
            <button
              onClick={() => { setStep('upload'); setPreview(null); setExportData(null) }}
              className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleApply}
              className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors flex items-center gap-2"
            >
              <CheckCircle2 size={14} /> Apply Import
            </button>
          </div>
        </div>
      )}

      {/* ── Step: Applying ── */}
      {step === 'applying' && (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-indigo-400 mb-3" />
          <p className="text-slate-300 text-sm">Applying import…</p>
        </div>
      )}

      {/* ── Step: Done ── */}
      {step === 'done' && result && (
        <div>
          <div className="flex items-center gap-2 mb-5">
            <CheckCircle2 size={20} className="text-emerald-400" />
            <span className="text-white font-medium">Import Complete</span>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-5 sm:grid-cols-4">
            {[
              { label: 'Added', count: result.added.length, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
              { label: 'Updated', count: result.updated.length, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
              { label: 'Skipped', count: result.skipped.length, color: 'text-slate-400', bg: 'bg-slate-700/50 border-slate-600' },
              { label: 'Errors', count: result.errors.length, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
            ].map(s => (
              <div key={s.label} className={`rounded-lg border px-3 py-2.5 text-center ${s.bg}`}>
                <div className={`text-xl font-bold ${s.color}`}>{s.count}</div>
                <div className="text-xs text-slate-400 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {result.errors.length > 0 && (
            <div className="mb-4 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              <p className="text-xs font-medium text-red-400 mb-1">Errors</p>
              {result.errors.map((e, i) => (
                <p key={i} className="text-xs text-red-300">{e.type}: {e.name} — {e.error}</p>
              ))}
            </div>
          )}

          <div className="flex justify-end">
            <button onClick={onClose} className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors">
              Done
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function ProjectsManager() {
  const [projects, setProjects] = useState([])
  const [allWorkflows, setAllWorkflows] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [modalState, setModalState] = useState(null)
  const [saving, setSaving] = useState(false)
  const [exportingId, setExportingId] = useState(null)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      setLoading(true)
      const [p, w, u] = await Promise.all([getProjects(), getWorkflows(), getUsers()])
      setProjects(p)
      setAllWorkflows(w)
      setAllUsers(u)
    } catch {
      setError('Failed to load projects.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(form) {
    try {
      setSaving(true)
      if (modalState.type === 'add') {
        await createProject(form)
      } else {
        await updateProject(modalState.project.id, form)
      }
      setModalState(null)
      loadData()
    } catch { /* silently ignore */ } finally { setSaving(false) }
  }

  async function handleDelete() {
    try {
      setSaving(true)
      await deleteProject(modalState.project.id)
      setModalState(null)
      loadData()
    } catch { /* silently ignore */ } finally { setSaving(false) }
  }

  async function handleExport(project) {
    try {
      setExportingId(project.id)
      const data = await exportCustomer(project.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `customer_${project.name.replace(/\s+/g, '_')}_${data.exportId.slice(0, 8)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch { /* silently ignore */ } finally { setExportingId(null) }
  }

  const filtered = projects.filter(p =>
    !search ||
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.description || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Customers</h1>
          <p className="text-slate-400 text-sm mt-1">Manage customers, workflows, and team access.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setModalState({ type: 'import' })}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Upload size={16} /> Import Customer
          </button>
          <button
            onClick={() => setModalState({ type: 'add' })}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Plus size={16} /> Add Customer
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="mb-5">
        <div className="relative max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search customers…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading customers…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10"><AlertCircle size={18} /> {error}</div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Description</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Workflows</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Users</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Status</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center text-slate-500 py-10">
                    <FolderOpen size={32} className="mx-auto mb-2 opacity-30" />
                    No customers found.
                  </td>
                </tr>
              ) : (
                filtered.map(project => (
                  <tr key={project.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-white">
                      <div className="flex items-center gap-2">
                        {project.name}
                        {project.launchurl && (
                          <a
                            href={project.launchurl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-500 hover:text-indigo-400 transition-colors flex-shrink-0"
                            title={project.launchurl}
                            onClick={e => e.stopPropagation()}
                          >
                            <ExternalLink size={13} />
                          </a>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate hidden md:table-cell">{project.description || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-slate-300 text-xs">
                        <Workflow size={12} />
                        {(project.workflow_ids || []).length}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-slate-300 text-xs">
                        <Users size={12} />
                        {(project.user_ids || []).length}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {project.is_active !== false
                        ? <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Active</span>
                        : <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-slate-500/20 text-slate-400 border border-slate-500/30">Inactive</span>
                      }
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setModalState({ type: 'manage', project })}
                          className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition-colors"
                          title="Manage"
                        >
                          <Settings size={14} />
                        </button>
                        <button
                          onClick={() => handleExport(project)}
                          disabled={exportingId === project.id}
                          className="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 rounded transition-colors disabled:opacity-50"
                          title="Export"
                        >
                          {exportingId === project.id
                            ? <Loader2 size={14} className="animate-spin" />
                            : <Download size={14} />
                          }
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'edit', project })}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'delete', project })}
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
      {modalState?.type === 'import' && (
        <ImportCustomerModal
          onClose={() => setModalState(null)}
          onImported={loadData}
        />
      )}
      {modalState?.type === 'add' && (
        <Modal title="Add Customer" onClose={() => setModalState(null)}>
          <ProjectForm onSave={handleSave} onClose={() => setModalState(null)} saving={saving} />
        </Modal>
      )}
      {modalState?.type === 'edit' && (
        <Modal title="Edit Customer" onClose={() => setModalState(null)}>
          <ProjectForm
            initial={modalState.project}
            onSave={handleSave}
            onClose={() => setModalState(null)}
            saving={saving}
          />
        </Modal>
      )}
      {modalState?.type === 'manage' && (
        <ManageProjectModal
          project={modalState.project}
          allWorkflows={allWorkflows}
          allUsers={allUsers}
          onClose={() => setModalState(null)}
          onChanged={loadData}
        />
      )}
      {modalState?.type === 'delete' && (
        <Modal title="Delete Customer" onClose={() => setModalState(null)}>
          <p className="text-slate-300 text-sm mb-4">
            Are you sure you want to delete <span className="text-white font-medium">"{modalState.project.name}"</span>?
          </p>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setModalState(null)} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={saving}
              className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              Delete
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
