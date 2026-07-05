import { useState, useEffect } from 'react'
import {
  getTools, createTool, updateTool, deleteTool, submitReview,
  exportTool, previewToolImport, applyToolImport,
} from '../../api/api'
import {
  Wrench, Plus, Pencil, Trash2, X, Loader2, AlertCircle, Search, ChevronDown,
  Download, Upload,
} from 'lucide-react'
import PropertiesEditor from './PropertiesEditor'
import LibraryImportModal from './LibraryImportModal'

const TOOL_TYPES = [
  'api_call', 'data_transform', 'notification', 'database',
  'file_operation', 'ai_model', 'web_search'
]

const TYPE_COLORS = {
  api_call: 'bg-blue-500/20 text-blue-400',
  data_transform: 'bg-purple-500/20 text-purple-400',
  notification: 'bg-amber-500/20 text-amber-400',
  database: 'bg-emerald-500/20 text-emerald-400',
  file_operation: 'bg-cyan-500/20 text-cyan-400',
  ai_model: 'bg-indigo-500/20 text-indigo-400',
  web_search: 'bg-rose-500/20 text-rose-400',
}

const REVIEW_COLORS = {
  pending: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  approved: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  rejected: 'bg-red-500/20 text-red-400 border border-red-500/30',
}

const EMPTY_FORM = { name: '', description: '', type: 'api_call', properties: {} }

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-xl shadow-2xl flex flex-col max-h-[90vh]">
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

function ConfirmDelete({ tool, onConfirm, onClose, loading }) {
  return (
    <Modal title="Delete Tool" onClose={onClose}>
      <p className="text-slate-300 text-sm mb-4">
        Are you sure you want to delete <span className="text-white font-medium">"{tool.name}"</span>? This action cannot be undone.
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

function ToolForm({ initial, onSave, onClose, saving }) {
  const [form, setForm] = useState({
    ...EMPTY_FORM,
    ...(initial && { name: initial.name || '', description: initial.description || '', type: initial.type || 'api_call', properties: initial.properties || {} }),
  })

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  return (
    <form onSubmit={e => { e.preventDefault(); onSave(form) }}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Name <span className="text-red-400">*</span></label>
          <input
            required
            value={form.name}
            onChange={e => set('name', e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            placeholder="Tool name"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={e => set('description', e.target.value)}
            rows={3}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            placeholder="Describe what this tool does…"
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
              {TOOL_TYPES.map(t => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-2">Properties</label>
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
            <PropertiesEditor value={form.properties} onChange={v => set('properties', v)} />
          </div>
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
          {initial ? 'Save Changes' : 'Create Tool'}
        </button>
      </div>
    </form>
  )
}

export default function ToolsManager() {
  const [tools, setTools] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [reviewFilter, setReviewFilter] = useState('all')
  const [modalState, setModalState] = useState(null) // null | {type:'add'} | {type:'edit', tool} | {type:'delete', tool} | {type:'import'}
  const [saving, setSaving] = useState(false)
  const [exportingId, setExportingId] = useState(null)

  useEffect(() => { loadTools() }, [])

  async function loadTools() {
    try {
      setLoading(true)
      const data = await getTools()
      setTools(data)
    } catch {
      setError('Failed to load tools.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(form) {
    try {
      setSaving(true)
      if (modalState.type === 'add') {
        const created = await createTool(form)
        await submitReview({ type: 'tool', item_id: created.id, item_name: created.name, item_data: created })
      } else {
        await updateTool(modalState.tool.id, form)
      }
      setModalState(null)
      loadTools()
    } catch {
      /* silently ignore for now */
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    try {
      setSaving(true)
      await deleteTool(modalState.tool.id)
      setModalState(null)
      loadTools()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  async function handleExport(tool) {
    try {
      setExportingId(tool.id)
      const data = await exportTool(tool.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `tool_${tool.name.replace(/\s+/g, '_')}_${data.exportId.slice(0, 8)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch { /* silently ignore */ } finally { setExportingId(null) }
  }

  const REVIEW_TABS = ['all', 'approved', 'pending', 'rejected']

  const filtered = tools.filter(t => {
    const matchSearch = !search ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.description || '').toLowerCase().includes(search.toLowerCase())
    const matchReview = reviewFilter === 'all' || t.review_status === reviewFilter
    return matchSearch && matchReview
  })

  const counts = REVIEW_TABS.slice(1).reduce((acc, s) => {
    acc[s] = tools.filter(t => t.review_status === s).length
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Tools Library</h1>
          <p className="text-slate-400 text-sm mt-1">Manage reusable tools for your agents.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setModalState({ type: 'import' })}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Upload size={16} /> Import Tool
          </button>
          <button
            onClick={() => setModalState({ type: 'add' })}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Plus size={16} /> Add Tool
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
            placeholder="Search tools…"
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
          <Loader2 size={24} className="animate-spin mr-2" /> Loading tools…
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
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Review Status</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-slate-500 py-10">
                    <Wrench size={32} className="mx-auto mb-2 opacity-30" />
                    No tools found.
                  </td>
                </tr>
              ) : (
                filtered.map(tool => (
                  <tr key={tool.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-white">{tool.name}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[tool.type] || 'bg-slate-700 text-slate-300'}`}>
                        {tool.type?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate hidden md:table-cell">{tool.description || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${REVIEW_COLORS[tool.review_status] || REVIEW_COLORS.pending}`}>
                        {tool.review_status || 'pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleExport(tool)}
                          disabled={exportingId === tool.id}
                          className="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 rounded transition-colors disabled:opacity-50"
                          title="Export"
                        >
                          {exportingId === tool.id
                            ? <Loader2 size={14} className="animate-spin" />
                            : <Download size={14} />}
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'edit', tool })}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'delete', tool })}
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
        <Modal title="Add Tool" onClose={() => setModalState(null)}>
          <ToolForm onSave={handleSave} onClose={() => setModalState(null)} saving={saving} />
        </Modal>
      )}
      {modalState?.type === 'edit' && (
        <Modal title="Edit Tool" onClose={() => setModalState(null)}>
          <ToolForm
            initial={modalState.tool}
            onSave={handleSave}
            onClose={() => setModalState(null)}
            saving={saving}
          />
        </Modal>
      )}
      {modalState?.type === 'delete' && (
        <ConfirmDelete
          tool={modalState.tool}
          onConfirm={handleDelete}
          onClose={() => setModalState(null)}
          loading={saving}
        />
      )}
      {modalState?.type === 'import' && (
        <LibraryImportModal
          kind="tool"
          previewFn={previewToolImport}
          applyFn={applyToolImport}
          onClose={() => setModalState(null)}
          onImported={loadTools}
        />
      )}
    </div>
  )
}
