import { useState, useEffect } from 'react'
import {
  getLibraryWorkflows, cloneWorkflow, deleteWorkflow,
  exportTemplate, previewTemplateImport, applyTemplateImport,
} from '../../api/api'
import usePortalStore from '../../store/portalStore'
import {
  BookOpen, Search, Copy, ExternalLink, Trash2, Loader2, AlertCircle,
  Tag, Layers, GitBranch, Calendar, X, Download, Upload,
} from 'lucide-react'
import LibraryImportModal from './LibraryImportModal'

const STATUS_COLORS = {
  active: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  draft: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  archived: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export default function TemplatesManager() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [showImport, setShowImport] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [exportingId, setExportingId] = useState(null)
  const { launchStudio, notify } = usePortalStore()

  useEffect(() => { loadTemplates() }, [])

  async function loadTemplates() {
    try {
      setLoading(true)
      const data = await getLibraryWorkflows()
      setTemplates(data)
    } catch {
      setError('Failed to load templates.')
    } finally {
      setLoading(false)
    }
  }

  async function handleClone(id) {
    try {
      setActionLoading(id)
      await cloneWorkflow(id)
      notify?.('Template cloned successfully.')
      loadTemplates()
    } catch {
      notify?.('Failed to clone template.', 'error')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleDelete() {
    try {
      setActionLoading(true)
      await deleteWorkflow(confirmDelete.id)
      setConfirmDelete(null)
      loadTemplates()
    } catch {
      /* silently ignore */
    } finally {
      setActionLoading(false)
    }
  }

  async function handleExport(template) {
    try {
      setExportingId(template.id)
      const data = await exportTemplate(template.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `template_${template.name.replace(/\s+/g, '_')}_${data.exportId.slice(0, 8)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch { /* silently ignore */ } finally { setExportingId(null) }
  }

  function openInStudio(id) {
    localStorage.setItem('wf-open-workflow', JSON.stringify({ workflowId: id }))
    launchStudio()
  }

  const STATUS_TABS = ['all', 'active', 'draft', 'archived']

  const filtered = templates.filter(t => {
    const matchSearch = !search ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.description || '').toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || t.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">Workflow Templates</h1>
            {!loading && (
              <span className="bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full text-sm font-medium">
                {templates.length} {templates.length === 1 ? 'template' : 'templates'}
              </span>
            )}
          </div>
          <p className="text-slate-400 text-sm mt-1">Browse and manage reusable workflow templates.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Upload size={16} /> Import Template
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
            placeholder="Search templates…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded-lg p-1">
          {STATUS_TABS.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors ${
                statusFilter === s ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {s === 'all' ? 'All' : s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading templates…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10"><AlertCircle size={18} /> {error}</div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Status</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden lg:table-cell">Tags</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Nodes</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Edges</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Created</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-slate-500 py-10">
                    <BookOpen size={32} className="mx-auto mb-2 opacity-30" />
                    No templates found.
                  </td>
                </tr>
              ) : (
                filtered.map(t => (
                  <tr key={t.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-white">{t.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5 max-w-xs truncate">{t.description || '—'}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[t.status] || STATUS_COLORS.draft}`}>
                        {t.status || 'draft'}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {(t.tags || []).slice(0, 3).map(tag => (
                          <span key={tag} className="inline-flex items-center gap-1 bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded-full text-xs">
                            <Tag size={9} />{tag}
                          </span>
                        ))}
                        {(t.tags || []).length > 3 && (
                          <span className="text-slate-500 text-xs">+{t.tags.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      <span className="flex items-center gap-1 text-xs">
                        <Layers size={12} />{(t.nodes || []).length}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      <span className="flex items-center gap-1 text-xs">
                        <GitBranch size={12} />{(t.edges || []).length}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs hidden md:table-cell">
                      <span className="flex items-center gap-1">
                        <Calendar size={12} />
                        {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openInStudio(t.id)}
                          className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition-colors"
                          title="View in Studio"
                        >
                          <ExternalLink size={14} />
                        </button>
                        <button
                          onClick={() => handleExport(t)}
                          disabled={exportingId === t.id}
                          className="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 rounded transition-colors disabled:opacity-50"
                          title="Export"
                        >
                          {exportingId === t.id
                            ? <Loader2 size={14} className="animate-spin" />
                            : <Download size={14} />}
                        </button>
                        <button
                          onClick={() => handleClone(t.id)}
                          disabled={actionLoading === t.id}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition-colors disabled:opacity-50"
                          title="Clone"
                        >
                          {actionLoading === t.id
                            ? <Loader2 size={14} className="animate-spin" />
                            : <Copy size={14} />}
                        </button>
                        <button
                          onClick={() => setConfirmDelete(t)}
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

      {/* Import Modal */}
      {showImport && (
        <LibraryImportModal
          kind="template"
          previewFn={previewTemplateImport}
          applyFn={applyTemplateImport}
          onClose={() => setShowImport(false)}
          onImported={loadTemplates}
        />
      )}

      {/* Delete Confirm */}
      {confirmDelete && (
        <Modal title="Delete Template" onClose={() => setConfirmDelete(null)}>
          <p className="text-slate-300 text-sm mb-4">
            Are you sure you want to delete <span className="text-white font-medium">"{confirmDelete.name}"</span>? This action cannot be undone.
          </p>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setConfirmDelete(null)} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={actionLoading === true}
              className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {actionLoading === true && <Loader2 size={14} className="animate-spin" />}
              Delete
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
