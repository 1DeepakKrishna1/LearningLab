import React, { useState, useEffect, useCallback } from 'react'
import {
  ChevronDown,
  ChevronRight as ChevronRightIcon,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  AlertCircle,
  RefreshCw,
  Database,
} from 'lucide-react'
import { getDashboardDetail } from '../../api/api'
import { FILTER_DETAIL_CONFIG, ACCENT_COLORS } from './dashboardDetailConfig'

// ── Debounce hook ─────────────────────────────────────────────────────────────
function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

// ── Cell renderer ─────────────────────────────────────────────────────────────
function CellValue({ type, value }) {
  if (value === null || value === undefined || value === '') {
    if (type === 'datetime' || type === 'duration' || type === 'duration_s') {
      return <span className="text-slate-500">—</span>
    }
  }

  switch (type) {
    case 'status': {
      const map = {
        active:    'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        draft:     'bg-amber-500/20 text-amber-300 border-amber-500/30',
        running:   'bg-blue-500/20 text-blue-300 border-blue-500/30',
        completed: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        failed:    'bg-red-500/20 text-red-300 border-red-500/30',
        pending:   'bg-slate-600/50 text-slate-300 border-slate-500/30',
        archived:  'bg-slate-600/50 text-slate-300 border-slate-500/30',
      }
      const cls = map[value] ?? 'bg-slate-600/50 text-slate-300 border-slate-500/30'
      return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
          {value}
        </span>
      )
    }

    case 'datetime': {
      if (!value) return <span className="text-slate-500">—</span>
      try {
        const d = new Date(value)
        const mon = d.toLocaleString('default', { month: 'short' })
        const day = d.getDate()
        const hh = String(d.getHours()).padStart(2, '0')
        const mm = String(d.getMinutes()).padStart(2, '0')
        return <span className="text-slate-300 text-xs">{`${mon} ${day}, ${hh}:${mm}`}</span>
      } catch {
        return <span className="text-slate-300 text-xs">{value}</span>
      }
    }

    case 'number':
      return <span className="text-slate-200 tabular-nums">{Number(value).toLocaleString()}</span>

    case 'pct':
      return <span className="text-slate-200 tabular-nums">{Number(value).toFixed(1)}%</span>

    case 'duration': {
      if (!value && value !== 0) return <span className="text-slate-500">—</span>
      const ms = Number(value)
      if (ms === 0) return <span className="text-slate-500">—</span>
      return <span className="text-slate-200 tabular-nums">{(ms / 1000).toFixed(1)}s</span>
    }

    case 'duration_s': {
      if (!value && value !== 0) return <span className="text-slate-500">—</span>
      const s = Number(value)
      if (s === 0) return <span className="text-slate-500">—</span>
      return <span className="text-slate-200 tabular-nums">{s.toFixed(1)}s</span>
    }

    case 'sla': {
      if (value === 'breach') {
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-500/20 text-red-300 border border-red-500/30">
            breach
          </span>
        )
      }
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          ok
        </span>
      )
    }

    case 'rstatus': {
      const map = {
        approved: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        pending:  'bg-amber-500/20 text-amber-300 border-amber-500/30',
        rejected: 'bg-red-500/20 text-red-300 border-red-500/30',
      }
      const cls = map[value] ?? 'bg-slate-600/50 text-slate-300 border-slate-500/30'
      return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
          {value}
        </span>
      )
    }

    case 'cost':
      return <span className="text-slate-200 tabular-nums">${Number(value).toFixed(4)}</span>

    case 'change': {
      const n = Number(value)
      if (n > 0) return <span className="text-emerald-400 tabular-nums">+{n.toFixed(1)}%</span>
      if (n < 0) return <span className="text-red-400 tabular-nums">{n.toFixed(1)}%</span>
      return <span className="text-slate-400 tabular-nums">0%</span>
    }

    default:
      return <span className="text-slate-200">{String(value ?? '')}</span>
  }
}

// ── Aggregation strip ─────────────────────────────────────────────────────────
function AggregationBar({ aggregations, filter }) {
  if (!aggregations) return null
  const { total_count, active_count, failed_count, avg_duration_s, success_pct, token_usage } = aggregations

  const items = [
    { label: 'Total', value: total_count?.toLocaleString() ?? '—' },
  ]

  if (filter === 'Tokens') {
    items.push({ label: 'Avg Tokens', value: active_count?.toLocaleString() ?? '—', dot: 'bg-amber-400' })
  } else {
    items.push({ label: 'Active', value: active_count?.toLocaleString() ?? '—', dot: 'bg-emerald-400' })
    items.push({ label: 'Failed', value: failed_count?.toLocaleString() ?? '—', dot: 'bg-red-400' })
  }

  if (avg_duration_s > 0) {
    items.push({ label: 'Avg Duration', value: `${avg_duration_s}s` })
  }
  if (success_pct > 0) {
    items.push({ label: 'Success', value: `${success_pct}%` })
  }
  if (token_usage > 0 && filter !== 'Tokens') {
    items.push({ label: 'Tokens', value: token_usage.toLocaleString() })
  }
  if (filter === 'Tokens' && token_usage > 0) {
    items.push({ label: 'Total Tokens', value: token_usage.toLocaleString(), dot: 'bg-amber-400' })
  }

  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-2 bg-slate-900/60 border-b border-slate-700">
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-1.5">
          {item.dot && <span className={`inline-block w-2 h-2 rounded-full ${item.dot}`} />}
          <span className="text-xs text-slate-500">{item.label}:</span>
          <span className="text-xs font-semibold text-slate-200">{item.value}</span>
        </div>
      ))}
    </div>
  )
}

// ── Table skeleton ────────────────────────────────────────────────────────────
function TableSkeleton({ cols }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            {cols.map((col, i) => (
              <th key={i} className="px-4 py-3 text-left">
                <div className="h-3 w-20 bg-slate-700 rounded animate-pulse" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 5 }).map((_, ri) => (
            <tr key={ri} className="border-b border-slate-700/50">
              {cols.map((_, ci) => (
                <td key={ci} className="px-4 py-3">
                  <div
                    className="h-3 bg-slate-700 rounded animate-pulse"
                    style={{ width: `${40 + ((ri * 17 + ci * 13) % 40)}%` }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Detail table ──────────────────────────────────────────────────────────────
function FilterDetailTable({ filter, tab, period, workflowId }) {
  const config = FILTER_DETAIL_CONFIG[filter]
  const accentColors = ACCENT_COLORS[config.accent]

  const [search, setSearch] = useState('')
  const [contextFilters, setContextFilters] = useState(() => {
    const init = {}
    config.contextFilters.forEach(cf => { init[cf.key] = '' })
    return init
  })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [sortBy, setSortBy] = useState('')
  const [sortDir, setSortDir] = useState('asc')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const debouncedSearch = useDebounce(search, 300)

  // Reset page on filter change
  useEffect(() => { setPage(1) }, [tab, debouncedSearch, contextFilters, sortBy, sortDir, pageSize])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        filter: filter,
        tab: tab,
        page,
        page_size: pageSize,
        search: debouncedSearch,
        sort_by: sortBy,
        sort_dir: sortDir,
      }
      if (workflowId) params.workflow_id = workflowId
      // Map contextFilters keys to query params
      Object.entries(contextFilters).forEach(([k, v]) => {
        if (v) params[k] = v
      })
      const result = await getDashboardDetail(params)
      setData(result)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [filter, tab, page, pageSize, debouncedSearch, contextFilters, sortBy, sortDir, workflowId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSort = (col) => {
    if (!col.sortable) return
    if (sortBy === col.key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(col.key)
      setSortDir('asc')
    }
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

  return (
    <div className="flex flex-col">
      {/* Controls bar */}
      <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-slate-700">
        {/* Search */}
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search..."
            className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <span className="text-xs leading-none">&times;</span>
            </button>
          )}
        </div>

        {/* Context filters */}
        {config.contextFilters.map(cf => (
          <select
            key={cf.key}
            value={contextFilters[cf.key] ?? ''}
            onChange={e => setContextFilters(prev => ({ ...prev, [cf.key]: e.target.value }))}
            className="px-2 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
          >
            {cf.options.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        ))}

        <div className="flex-1" />

        {/* Page size */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Rows:</span>
          <select
            value={pageSize}
            onChange={e => setPageSize(Number(e.target.value))}
            className="px-2 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
          >
            {[10, 25, 50].map(n => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>

        {/* Refresh */}
        <button
          onClick={fetchData}
          disabled={loading}
          className="p-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Aggregations */}
      {data && <AggregationBar aggregations={data.aggregations} filter={filter} />}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 mx-4 my-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-3">
          <AlertCircle size={15} className="shrink-0" />
          <span className="text-xs">{error}</span>
          <button onClick={fetchData} className="ml-auto text-xs underline underline-offset-2 hover:text-red-300">
            Retry
          </button>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <TableSkeleton cols={config.columns} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-max">
            <thead>
              <tr className="border-b border-slate-700">
                {config.columns.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col)}
                    className={`px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap select-none ${col.sortable ? 'cursor-pointer hover:text-slate-200' : ''}`}
                  >
                    <span className="flex items-center gap-1">
                      {col.label}
                      {col.sortable && (
                        sortBy === col.key
                          ? sortDir === 'asc'
                            ? <ArrowUp size={11} className={accentColors.text} />
                            : <ArrowDown size={11} className={accentColors.text} />
                          : <ArrowUpDown size={11} className="text-slate-600" />
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(!data || data.rows.length === 0) ? (
                <tr>
                  <td colSpan={config.columns.length} className="px-4 py-12 text-center">
                    <div className="flex flex-col items-center gap-3 text-slate-500">
                      <Database size={28} className="opacity-40" />
                      <span className="text-sm">No data found</span>
                    </div>
                  </td>
                </tr>
              ) : (
                data.rows.map((row, ri) => (
                  <tr
                    key={row.id ?? ri}
                    className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors"
                  >
                    {config.columns.map(col => (
                      <td key={col.key} className="px-4 py-3 max-w-xs truncate">
                        {col.key === 'id' ? (
                          <span className="text-slate-400 text-xs font-mono truncate block max-w-[140px]" title={row[col.key]}>
                            {String(row[col.key] ?? '').slice(0, 8)}…
                          </span>
                        ) : col.type ? (
                          <CellValue type={col.type} value={row[col.key]} colKey={col.key} />
                        ) : (
                          <span className="text-slate-200">{String(row[col.key] ?? '')}</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {data && data.total > 0 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
          <span className="text-xs text-slate-500">
            {data.total} record{data.total !== 1 ? 's' : ''}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft size={13} />
              Prev
            </button>
            <span className="text-xs text-slate-400 px-1 tabular-nums">
              {page} / {Math.max(1, totalPages)}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRightIcon size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Single filter section (accordion) ────────────────────────────────────────
function FilterSection({ filter, period, workflowId }) {
  const config = FILTER_DETAIL_CONFIG[filter]
  if (!config) return null

  const accentColors = ACCENT_COLORS[config.accent]
  const [expanded, setExpanded] = useState(true)
  const [activeTab, setActiveTab] = useState(config.tabs[0].id)

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      {/* Section header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-3 px-5 py-3.5 hover:bg-slate-700/30 transition-colors text-left"
      >
        <span className={`text-sm font-semibold ${accentColors.text}`}>{filter}</span>
        <span className="text-xs text-slate-500">Detail View</span>
        <span className="flex-1" />
        {expanded
          ? <ChevronDown size={16} className="text-slate-400" />
          : <ChevronRightIcon size={16} className="text-slate-400" />
        }
      </button>

      {expanded && (
        <>
          {/* Sub-tabs bar */}
          <div className="flex items-center gap-0 px-5 border-b border-slate-700 overflow-x-auto">
            {config.tabs.map(t => {
              const active = t.id === activeTab
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`px-4 py-2.5 text-xs font-medium border-b-2 whitespace-nowrap transition-colors ${
                    active
                      ? `${accentColors.tab} border-b-2`
                      : 'border-transparent text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {t.label}
                </button>
              )
            })}
          </div>

          {/* Table */}
          <FilterDetailTable filter={filter} tab={activeTab} period={period} workflowId={workflowId} />
        </>
      )}
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function DrillDownSection({ visibleGroups, period, workflowId }) {
  if (!visibleGroups || visibleGroups.length === 0) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 pt-2">
        <div className="h-px flex-1 bg-slate-700" />
        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider px-3">
          Detail View
        </span>
        <div className="h-px flex-1 bg-slate-700" />
      </div>
      {visibleGroups.map(group => (
        <FilterSection key={group} filter={group} period={period} workflowId={workflowId} />
      ))}
    </div>
  )
}
