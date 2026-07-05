import React, { useEffect, useState, useCallback, useRef } from 'react'
import {
  Search, X, ChevronLeft, ChevronRight, AlertCircle,
  InboxIcon, ChevronDown, ChevronUp, RefreshCw, ShieldAlert
} from 'lucide-react'
import { getAuditLogs, getAuditSummary } from '../../api/api'

// ── Constants ─────────────────────────────────────────────────────────────────
const PAGE_SIZE = 50

const ACTION_OPTIONS = [
  'all', 'login', 'logout', 'create', 'update', 'delete',
  'execute', 'approve', 'reject',
]

const RESOURCE_TYPE_OPTIONS = [
  'all', 'user', 'group', 'project', 'workflow', 'tool',
  'agent', 'template', 'data_model',
]

const ACTION_COLOR = {
  login:   { bg: 'bg-blue-500/20   text-blue-300   border-blue-500/30',   dot: 'bg-blue-400' },
  logout:  { bg: 'bg-slate-700     text-slate-300  border-slate-600',      dot: 'bg-slate-400' },
  create:  { bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', dot: 'bg-emerald-400' },
  update:  { bg: 'bg-amber-500/20  text-amber-300  border-amber-500/30',   dot: 'bg-amber-400' },
  delete:  { bg: 'bg-red-500/20    text-red-300    border-red-500/30',     dot: 'bg-red-400' },
  execute: { bg: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',  dot: 'bg-indigo-400' },
  approve: { bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', dot: 'bg-emerald-400' },
  reject:  { bg: 'bg-red-500/20    text-red-300    border-red-500/30',     dot: 'bg-red-400' },
}

function actionStyle(action) {
  return ACTION_COLOR[action?.toLowerCase()] ?? {
    bg: 'bg-slate-700 text-slate-300 border-slate-600',
    dot: 'bg-slate-400',
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatLabel(s = '') {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function Skeleton({ className = '' }) {
  return <div className={`animate-pulse bg-slate-700 rounded ${className}`} />
}

// ── Action badge ──────────────────────────────────────────────────────────────
function ActionBadge({ action }) {
  const style = actionStyle(action)
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border whitespace-nowrap ${style.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {formatLabel(action ?? '—')}
    </span>
  )
}

// ── JSON detail viewer ────────────────────────────────────────────────────────
function DetailViewer({ details }) {
  const [open, setOpen] = useState(false)
  if (!details || (typeof details === 'object' && !Object.keys(details).length)) {
    return <span className="text-slate-600 text-xs">—</span>
  }
  const text = typeof details === 'string' ? details : JSON.stringify(details, null, 2)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {open ? 'Hide' : 'Show'} details
      </button>
      {open && (
        <pre className="mt-2 p-2 bg-slate-900 border border-slate-700 rounded text-xs text-slate-300 overflow-x-auto max-w-xs leading-relaxed whitespace-pre-wrap break-all">
          {text}
        </pre>
      )}
    </div>
  )
}

// ── Summary cards ─────────────────────────────────────────────────────────────
function SummaryCards({ summary, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-slate-800 rounded-xl border border-slate-700 p-3">
            <Skeleton className="h-3 w-16 mb-2" />
            <Skeleton className="h-6 w-10" />
          </div>
        ))}
      </div>
    )
  }

  if (!summary) return null

  const total = summary.total ?? 0
  const byAction = summary.by_action ?? {}
  const TOP_ACTIONS = ['login', 'create', 'update', 'delete', 'execute']

  const cards = [
    { label: 'Total Logs', value: total.toLocaleString(), color: 'text-white', dotColor: 'bg-slate-400' },
    ...TOP_ACTIONS.map(a => ({
      label: formatLabel(a),
      value: (byAction[a] ?? 0).toLocaleString(),
      color: actionStyle(a).bg,
      dotColor: actionStyle(a).dot,
      isBadge: true,
    })),
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
      {cards.map((c, i) => (
        <div key={i} className="bg-slate-800 rounded-xl border border-slate-700 p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className={`w-2 h-2 rounded-full ${c.dotColor}`} />
            <p className="text-xs text-slate-400 uppercase tracking-wider truncate">{c.label}</p>
          </div>
          <p className={`text-xl font-bold ${i === 0 ? 'text-white' : 'text-slate-200'}`}>{c.value}</p>
        </div>
      ))}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function AuditLogs() {
  // Filter state
  const [search, setSearch]           = useState('')
  const [actionFilter, setActionFilter]       = useState('all')
  const [resourceFilter, setResourceFilter]   = useState('all')

  // Applied filter (triggers fetch)
  const [appliedFilters, setAppliedFilters] = useState({ search: '', action: 'all', resource_type: 'all' })

  // Data state
  const [logs, setLogs]         = useState([])
  const [summary, setSummary]   = useState(null)
  const [loading, setLoading]   = useState(true)
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [error, setError]       = useState(null)

  // Pagination
  const [page, setPage] = useState(1)

  // ── Fetch logs ──────────────────────────────────────────────
  const fetchLogs = useCallback(async (filters) => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search)      params.search       = filters.search
      if (filters.action && filters.action !== 'all')
        params.action = filters.action
      if (filters.resource_type && filters.resource_type !== 'all')
        params.resource_type = filters.resource_type
      // fetch a large batch; we paginate client-side
      params.limit = 500
      const data = await getAuditLogs(params)
      setLogs(Array.isArray(data) ? data : (data.items ?? []))
      setPage(1)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Fetch summary ───────────────────────────────────────────
  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true)
    try {
      const data = await getAuditSummary()
      setSummary(data)
    } catch {
      // non-critical
    } finally {
      setSummaryLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLogs(appliedFilters)
    fetchSummary()
  }, [appliedFilters])

  // ── Apply filters ───────────────────────────────────────────
  const handleSearch = () => {
    setAppliedFilters({ search, action: actionFilter, resource_type: resourceFilter })
  }

  const handleClear = () => {
    setSearch('')
    setActionFilter('all')
    setResourceFilter('all')
    setAppliedFilters({ search: '', action: 'all', resource_type: 'all' })
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch()
  }

  // ── Pagination ──────────────────────────────────────────────
  const totalPages = Math.max(1, Math.ceil(logs.length / PAGE_SIZE))
  const pageLogs = logs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const hasFilters = search || actionFilter !== 'all' || resourceFilter !== 'all'
  const hasApplied = appliedFilters.search || appliedFilters.action !== 'all' || appliedFilters.resource_type !== 'all'

  return (
    <div className="flex-1 overflow-y-auto p-6">

      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-white">Audit Logs</h1>
          <p className="text-sm text-slate-400 mt-0.5">Complete history of platform activity</p>
        </div>
        <button
          onClick={() => { fetchLogs(appliedFilters); fetchSummary() }}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-sm transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* ── Summary cards ── */}
      <SummaryCards summary={summary} loading={summaryLoading} />

      {/* ── Filter bar ── */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 mb-5">
        <div className="flex flex-wrap gap-3 items-end">
          {/* Search */}
          <div className="flex-1 min-w-[180px]">
            <label className="text-xs text-slate-400 mb-1.5 block">Search</label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              <input
                type="text"
                placeholder="User, resource, details..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
          </div>

          {/* Action filter */}
          <div className="min-w-[150px]">
            <label className="text-xs text-slate-400 mb-1.5 block">Action</label>
            <select
              value={actionFilter}
              onChange={e => setActionFilter(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
            >
              {ACTION_OPTIONS.map(a => (
                <option key={a} value={a}>{a === 'all' ? 'All Actions' : formatLabel(a)}</option>
              ))}
            </select>
          </div>

          {/* Resource type filter */}
          <div className="min-w-[160px]">
            <label className="text-xs text-slate-400 mb-1.5 block">Resource Type</label>
            <select
              value={resourceFilter}
              onChange={e => setResourceFilter(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
            >
              {RESOURCE_TYPE_OPTIONS.map(r => (
                <option key={r} value={r}>{r === 'all' ? 'All Resources' : formatLabel(r)}</option>
              ))}
            </select>
          </div>

          {/* Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleSearch}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
            >
              <Search size={14} />
              Search
            </button>
            {(hasFilters || hasApplied) && (
              <button
                onClick={handleClear}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white text-sm transition-colors"
              >
                <X size={14} />
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Active filters chips */}
        {hasApplied && (
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-slate-700">
            <span className="text-xs text-slate-500">Active filters:</span>
            {appliedFilters.search && (
              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                Search: "{appliedFilters.search}"
              </span>
            )}
            {appliedFilters.action !== 'all' && (
              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                Action: {formatLabel(appliedFilters.action)}
              </span>
            )}
            {appliedFilters.resource_type !== 'all' && (
              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                Resource: {formatLabel(appliedFilters.resource_type)}
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 mb-5">
          <AlertCircle size={16} className="shrink-0" />
          <span className="text-sm">{error}</span>
          <button onClick={() => fetchLogs(appliedFilters)} className="ml-auto text-xs underline underline-offset-2">
            Retry
          </button>
        </div>
      )}

      {/* ── Table ── */}
      <div className="bg-slate-800 rounded-xl border border-slate-700">

        {loading ? (
          <div className="p-5">
            {/* Skeleton table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    {['Timestamp', 'User', 'Action', 'Resource Type', 'Resource Name', 'Details'].map(h => (
                      <th key={h} className="py-3 px-4 text-left">
                        <Skeleton className="h-3 w-20" />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="border-b border-slate-700/50">
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="py-3 px-4">
                          <Skeleton className="h-4 w-full" />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : pageLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500">
            <ShieldAlert size={40} className="mb-3 opacity-30" />
            <p className="text-sm font-medium">No audit logs found</p>
            {hasApplied && (
              <p className="text-xs mt-1 text-slate-600">Try adjusting your filters</p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  {['Timestamp', 'User', 'Action', 'Resource Type', 'Resource Name', 'Details'].map(h => (
                    <th
                      key={h}
                      className="text-left text-xs font-medium text-slate-400 uppercase tracking-wider py-3 px-4 whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {pageLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-700/30 transition-colors group">
                    {/* Timestamp */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="text-slate-400 text-xs font-mono">
                        {new Date(log.timestamp).toLocaleString(undefined, {
                          year: 'numeric', month: '2-digit', day: '2-digit',
                          hour: '2-digit', minute: '2-digit', second: '2-digit',
                        })}
                      </span>
                    </td>

                    {/* User */}
                    <td className="py-3 px-4">
                      <div>
                        <p className="text-white text-sm font-medium leading-tight">
                          {log.user_name ?? log.user_id ?? '—'}
                        </p>
                        {log.user_email && (
                          <p className="text-slate-500 text-xs leading-tight mt-0.5">{log.user_email}</p>
                        )}
                      </div>
                    </td>

                    {/* Action badge */}
                    <td className="py-3 px-4">
                      <ActionBadge action={log.action} />
                    </td>

                    {/* Resource type */}
                    <td className="py-3 px-4">
                      <span className="text-slate-300 text-xs font-medium">
                        {formatLabel(log.resource_type ?? '—')}
                      </span>
                    </td>

                    {/* Resource name */}
                    <td className="py-3 px-4">
                      <div>
                        <p className="text-slate-300 text-sm leading-tight">
                          {log.resource_name ?? '—'}
                        </p>
                        {log.resource_id && (
                          <p className="text-slate-600 text-xs font-mono leading-tight mt-0.5">
                            {log.resource_id}
                          </p>
                        )}
                      </div>
                    </td>

                    {/* Details toggle */}
                    <td className="py-3 px-4">
                      <DetailViewer details={log.details} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Pagination footer ── */}
        {!loading && logs.length > 0 && (
          <div className="flex items-center justify-between border-t border-slate-700 px-5 py-3">
            <p className="text-xs text-slate-500">
              Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, logs.length)} of {logs.length.toLocaleString()} entries
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={13} />
                Previous
              </button>
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let p
                  if (totalPages <= 5) {
                    p = i + 1
                  } else if (page <= 3) {
                    p = i + 1
                  } else if (page >= totalPages - 2) {
                    p = totalPages - 4 + i
                  } else {
                    p = page - 2 + i
                  }
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`w-8 h-7 rounded text-xs font-medium transition-colors
                        ${p === page
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-white'
                        }`}
                    >
                      {p}
                    </button>
                  )
                })}
              </div>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
      </div>

    </div>
  )
}
