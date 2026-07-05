import { useState, useEffect } from 'react'
import { getWorkflows, cloneWorkflow } from '../../api/api'
import usePortalStore from '../../store/portalStore'
import useAuthStore from '../../store/authStore'
import { isVisible } from '../../config/pageConfig'
import {
  Workflow, Search, Copy, ExternalLink, Tag, Calendar,
  GitBranch, Layers, AlertCircle, Loader2, BookOpen, Play
} from 'lucide-react'

const STATUS_COLORS = {
  active: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  draft: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  archived: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
}

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] || STATUS_COLORS.draft}`}>
      {status}
    </span>
  )
}

function WorkflowCard({ wf, onClone, onOpen, onRun, showOpenInStudio, showClone }) {
  const [cloning, setCloning] = useState(false)
  const [running, setRunning] = useState(false)

  const handleClone = async () => {
    setCloning(true)
    await onClone(wf.id)
    setCloning(false)
  }

  const handleRun = () => {
    setRunning(true)
    onRun(wf)
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 flex flex-col gap-3 hover:border-indigo-500/50 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-semibold text-sm truncate">{wf.name}</h3>
          <p className="text-slate-400 text-xs mt-1 line-clamp-2 leading-relaxed">
            {wf.description || 'No description provided.'}
          </p>
        </div>
        <StatusBadge status={wf.status || 'draft'} />
      </div>

      {wf.tags && wf.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {wf.tags.map(tag => (
            <span key={tag} className="inline-flex items-center gap-1 bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full text-xs">
              <Tag size={10} />
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <Layers size={12} />
          {(wf.nodes || []).length} nodes
        </span>
        <span className="flex items-center gap-1">
          <GitBranch size={12} />
          {(wf.edges || []).length} edges
        </span>
        <span className="flex items-center gap-1 ml-auto">
          <Calendar size={12} />
          {wf.created_at ? new Date(wf.created_at).toLocaleDateString() : '—'}
        </span>
      </div>

      <div className="flex gap-2 pt-1 border-t border-slate-700">
        <button
          onClick={handleRun}
          disabled={running}
          className="flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium py-1.5 px-3 rounded-lg transition-colors disabled:opacity-60"
        >
          {running ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
          Run
        </button>
        {showOpenInStudio && (
          <button
            onClick={() => onOpen(wf.id)}
            className="flex-1 flex items-center justify-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium py-1.5 px-3 rounded-lg transition-colors"
          >
            <ExternalLink size={12} />
            Open in Studio
          </button>
        )}
        {showClone && (
          <button
            onClick={handleClone}
            disabled={cloning}
            className="flex items-center justify-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium py-1.5 px-3 rounded-lg transition-colors disabled:opacity-50"
          >
            {cloning ? <Loader2 size={12} className="animate-spin" /> : <Copy size={12} />}
            Clone
          </button>
        )}
      </div>
    </div>
  )
}

function TemplateCard({ wf, onClone }) {
  const [cloning, setCloning] = useState(false)

  const handleClone = async () => {
    setCloning(true)
    await onClone(wf.id)
    setCloning(false)
  }

  return (
    <div className="bg-slate-800 border border-indigo-500/30 rounded-xl p-5 flex flex-col gap-3 hover:border-indigo-500/60 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-white font-semibold text-sm truncate">{wf.name}</h3>
            <span className="bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full text-xs">template</span>
          </div>
          <p className="text-slate-400 text-xs mt-1 line-clamp-2 leading-relaxed">
            {wf.description || 'No description provided.'}
          </p>
        </div>
      </div>

      {wf.tags && wf.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {wf.tags.map(tag => (
            <span key={tag} className="inline-flex items-center gap-1 bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full text-xs">
              <Tag size={10} />
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="pt-1 border-t border-slate-700">
        <button
          onClick={handleClone}
          disabled={cloning}
          className="w-full flex items-center justify-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium py-1.5 px-3 rounded-lg transition-colors disabled:opacity-50"
        >
          {cloning ? <Loader2 size={12} className="animate-spin" /> : <Copy size={12} />}
          Clone Template
        </button>
      </div>
    </div>
  )
}

export default function ProcessList() {
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const { launchStudio, notify, navigateToRuns } = usePortalStore()
  const { user } = useAuthStore()
  const showOpenInStudio = isVisible(user?.role, 'process/workflows', 'openInStudio')
  const showClone        = isVisible(user?.role, 'process/workflows', 'clone')

  useEffect(() => {
    loadWorkflows()
  }, [])

  async function loadWorkflows() {
    try {
      setLoading(true)
      const data = await getWorkflows()
      setWorkflows(data)
    } catch {
      setError('Failed to load workflows.')
    } finally {
      setLoading(false)
    }
  }

  async function handleClone(id) {
    try {
      await cloneWorkflow(id)
      notify('Workflow cloned successfully.')
      loadWorkflows()
    } catch {
      notify('Failed to clone workflow.', 'error')
    }
  }

  function handleOpenInStudio(id) {
    localStorage.setItem('wf-open-workflow', JSON.stringify({ workflowId: id }))
    launchStudio()
  }

  const myWorkflows = workflows.filter(w => !w.is_template)
  const templates = workflows.filter(w => w.is_template)

  const filteredMy = myWorkflows.filter(w => {
    const matchSearch = !search ||
      w.name.toLowerCase().includes(search.toLowerCase()) ||
      (w.description || '').toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || w.status === statusFilter
    return matchSearch && matchStatus
  })

  const STATUS_TABS = ['all', 'active', 'draft', 'archived']

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Process — My Workflows</h1>
        <p className="text-slate-400 text-sm mt-1">Select a workflow to open in the Studio or clone.</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search workflows…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded-lg p-1">
          {STATUS_TABS.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors ${
                statusFilter === s
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {s === 'all' ? 'All' : s}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading workflows…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10">
          <AlertCircle size={18} /> {error}
        </div>
      ) : (
        <>
          {/* My Workflows */}
          {filteredMy.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-500">
              <Workflow size={48} className="mb-4 opacity-30" />
              <p className="text-lg font-medium">No workflows found</p>
              <p className="text-sm mt-1">Try adjusting your search or filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-10">
              {filteredMy.map(wf => (
                <WorkflowCard
                  key={wf.id}
                  wf={wf}
                  onClone={handleClone}
                  onOpen={handleOpenInStudio}
                  onRun={wf => navigateToRuns({ id: wf.id, name: wf.name })}
                  showOpenInStudio={showOpenInStudio}
                  showClone={showClone}
                />
              ))}
            </div>
          )}

          {/* Library Templates Section */}
          {templates.length > 0 && (
            <>
              <div className="flex items-center gap-2 mb-4">
                <BookOpen size={16} className="text-indigo-400" />
                <h2 className="text-lg font-semibold text-white">Library Templates</h2>
                <span className="bg-slate-700 text-slate-400 text-xs px-2 py-0.5 rounded-full">{templates.length}</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {templates.map(wf => (
                  <TemplateCard key={wf.id} wf={wf} onClone={handleClone} />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
