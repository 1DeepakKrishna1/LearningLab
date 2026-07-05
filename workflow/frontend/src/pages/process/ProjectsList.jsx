import { useState, useEffect } from 'react'
import { getProjects, getWorkflows, exportCustomer } from '../../api/api'
import usePortalStore from '../../store/portalStore'
import useAuthStore from '../../store/authStore'
import { isVisible } from '../../config/pageConfig'
import {
  FolderOpen, Search, ExternalLink, Workflow, Users,
  AlertCircle, Loader2, ChevronDown, ChevronRight, Play, Download
} from 'lucide-react'

function StatusBadge({ active }) {
  return active !== false
    ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Active</span>
    : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-500/20 text-slate-400 border border-slate-500/30">Inactive</span>
}

function ProjectCard({ project, workflowMap, onRun, onExport, showExport }) {
  const [expanded, setExpanded] = useState(false)
  const [exporting, setExporting] = useState(false)
  const projectWorkflows = (project.workflow_ids || []).map(id => workflowMap[id]).filter(Boolean)

  const handleExport = async () => {
    setExporting(true)
    await onExport(project)
    setExporting(false)
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 flex flex-col gap-3 hover:border-indigo-500/50 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-semibold text-sm truncate">{project.name}</h3>
          <p className="text-slate-400 text-xs mt-1 line-clamp-2 leading-relaxed">
            {project.description || 'No description provided.'}
          </p>
        </div>
        <StatusBadge active={project.is_active} />
      </div>

      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <Workflow size={12} />
          {(project.workflow_ids || []).length} workflows
        </span>
        <span className="flex items-center gap-1">
          <Users size={12} />
          {(project.user_ids || []).length} users
        </span>
      </div>

      {/* Expandable workflows list */}
      {projectWorkflows.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors mb-2"
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {expanded ? 'Hide' : 'Show'} workflows
          </button>
          {expanded && (
            <div className="space-y-1.5">
              {projectWorkflows.map(wf => (
                <div key={wf.id} className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2 gap-2">
                  <span className="text-xs text-slate-300 truncate flex-1">{wf.name}</span>
                  <button
                    onClick={() => onRun(wf)}
                    className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 px-2 py-1 rounded-md transition-colors shrink-0"
                  >
                    <Play size={10} />
                    Run
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="pt-1 border-t border-slate-700 flex gap-2">
        {project.launchurl ? (
          <a
            href={project.launchurl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium py-1.5 px-3 rounded-lg transition-colors"
          >
            <ExternalLink size={12} />
            Launch
          </a>
        ) : (
          <button
            disabled
            className="flex-1 flex items-center justify-center gap-1.5 bg-slate-700 text-slate-500 text-xs font-medium py-1.5 px-3 rounded-lg cursor-not-allowed opacity-50"
          >
            <ExternalLink size={12} />
            No Launch URL
          </button>
        )}
        {showExport && (
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center justify-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium py-1.5 px-3 rounded-lg transition-colors disabled:opacity-50"
            title="Export customer"
          >
            {exporting ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
            Export
          </button>
        )}
      </div>
    </div>
  )
}

export default function ProjectsList() {
  const [projects, setProjects]     = useState([])
  const [workflowMap, setWorkflowMap] = useState({})
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [search, setSearch]         = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const { navigateToRuns, notify } = usePortalStore()
  const { user } = useAuthStore()
  const showExport = isVisible(user?.role, 'process/projects', 'export')

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      setLoading(true)
      const [projectsData, wfData] = await Promise.all([getProjects(), getWorkflows()])
      setProjects(projectsData)
      const map = {}
      wfData.forEach(w => { map[w.id] = w })
      setWorkflowMap(map)
    } catch {
      setError('Failed to load projects.')
    } finally {
      setLoading(false)
    }
  }

  async function handleExport(project) {
    try {
      const data = await exportCustomer(project.id)
      const slug = project.name.trim().replace(/\s+/g, '_')
      const shortId = (data.exportId || '').split('-')[0]
      const filename = `customer_${slug}_${shortId}.json`
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      notify(`Exported "${project.name}" successfully.`)
    } catch {
      notify(`Failed to export "${project.name}".`, 'error')
    }
  }

  const filtered = projects.filter(p => {
    const matchSearch = !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.description || '').toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' ||
      (statusFilter === 'active' && p.is_active !== false) ||
      (statusFilter === 'inactive' && p.is_active === false)
    return matchSearch && matchStatus
  })

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Process — Customers</h1>
        <p className="text-slate-400 text-sm mt-1">Browse customers and run their associated workflows.</p>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search customers…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded-lg p-1">
          {['all', 'active', 'inactive'].map(s => (
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

      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading customers…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10">
          <AlertCircle size={18} /> {error}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <FolderOpen size={48} className="mb-4 opacity-30" />
          <p className="text-lg font-medium">No customers found</p>
          <p className="text-sm mt-1">Try adjusting your search or filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(project => (
            <ProjectCard
              key={project.id}
              project={project}
              workflowMap={workflowMap}
              onRun={wf => navigateToRuns({ id: wf.id, name: wf.name })}
              onExport={handleExport}
              showExport={showExport}
            />
          ))}
        </div>
      )}
    </div>
  )
}
