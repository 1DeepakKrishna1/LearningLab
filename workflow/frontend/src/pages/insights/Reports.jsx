import React, { useEffect, useState, useCallback } from 'react'
import {
  RefreshCw, Download, AlertCircle, InboxIcon,
  GitBranch, Bot, Users, Coins, Search, X
} from 'lucide-react'
import { getReport } from '../../api/api'
import { loadReportTabs } from '../../dashboardConfig'
import usePortalStore from '../../store/portalStore'

// ── Icon map ──────────────────────────────────────────────────────────────────
const ICON_MAP = { GitBranch, Bot, Users, Coins }

// ── Fallback cols per data_type / id ─────────────────────────────────────────
const TAB_COLS = {
  workflow_usage: 6,
  agent_performance: 5,
  user_activity: 5,
  token_consumption: 3,
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function Badge({ children, color = 'slate' }) {
  const map = {
    indigo:  'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    emerald: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    amber:   'bg-amber-500/20  text-amber-300  border-amber-500/30',
    red:     'bg-red-500/20    text-red-300    border-red-500/30',
    purple:  'bg-purple-500/20 text-purple-300 border-purple-500/30',
    orange:  'bg-orange-500/20 text-orange-300 border-orange-500/30',
    cyan:    'bg-cyan-500/20   text-cyan-300   border-cyan-500/30',
    slate:   'bg-slate-700     text-slate-300  border-slate-600',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border whitespace-nowrap ${map[color] ?? map.slate}`}>
      {children}
    </span>
  )
}

const STATUS_COLOR = {
  active: 'emerald', draft: 'amber', inactive: 'slate',
  published: 'indigo', archived: 'slate',
}
const AGENT_TYPE_COLOR = {
  automatic: 'indigo', role_based: 'emerald', human_in_the_loop: 'amber',
  human_review: 'sky',
  conditional: 'orange', parallel: 'purple',
}
const ROLE_COLOR = {
  admin: 'red', manager: 'indigo', developer: 'emerald',
  viewer: 'slate', analyst: 'cyan',
}

function statusColor(s) { return STATUS_COLOR[s] ?? 'slate' }
function agentTypeColor(t) { return AGENT_TYPE_COLOR[t] ?? 'slate' }
function roleColor(r) { return ROLE_COLOR[r] ?? 'slate' }

function formatLabel(s = '') {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// ── Export CSV ────────────────────────────────────────────────────────────────
function exportCSV(rows, filename) {
  if (!rows?.length) return
  const headers = Object.keys(rows[0])
  const lines = [
    headers.join(','),
    ...rows.map(r =>
      headers.map(h => {
        const v = r[h] ?? ''
        const s = String(v).replace(/"/g, '""')
        return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s}"` : s
      }).join(',')
    ),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Table shell ────────────────────────────────────────────────────────────────
function Table({ headers, children, empty }) {
  if (empty) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-500">
        <InboxIcon size={36} className="mb-3 opacity-40" />
        <p className="text-sm">No data available</p>
      </div>
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            {headers.map(h => (
              <th key={h} className="text-left text-xs font-medium text-slate-400 uppercase tracking-wider py-3 px-4 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/50">{children}</tbody>
      </table>
    </div>
  )
}

function Td({ children, className = '' }) {
  return <td className={`py-3 px-4 text-slate-300 ${className}`}>{children}</td>
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skeleton({ className = '' }) {
  return <div className={`animate-pulse bg-slate-700 rounded ${className}`} />
}

function TableSkeleton({ cols = 5, rows = 6 }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i} className="py-3 px-4">
                <Skeleton className="h-3 w-20" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i} className="border-b border-slate-700/50">
              {Array.from({ length: cols }).map((_, j) => (
                <td key={j} className="py-3 px-4">
                  <Skeleton className="h-4 w-full" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Report tables ──────────────────────────────────────────────────────────────
function WorkflowUsageTable({ rows }) {
  return (
    <Table
      headers={['Workflow', 'Status', 'Executions', 'Completed', 'Failed', 'Last Run']}
      empty={!rows?.length}
    >
      {rows?.map((r, i) => (
        <tr key={i} className="hover:bg-slate-700/30 transition-colors">
          <Td className="font-medium text-white">{r.workflow_name ?? r.name ?? '—'}</Td>
          <Td><Badge color={statusColor(r.status)}>{formatLabel(r.status ?? '—')}</Badge></Td>
          <Td>{(r.total_executions ?? r.executions ?? 0).toLocaleString()}</Td>
          <Td><span className="text-emerald-400">{(r.completed ?? 0).toLocaleString()}</span></Td>
          <Td><span className="text-red-400">{(r.failed ?? 0).toLocaleString()}</span></Td>
          <Td className="text-slate-400">{r.last_run ? new Date(r.last_run).toLocaleString() : '—'}</Td>
        </tr>
      ))}
    </Table>
  )
}

function AgentPerformanceTable({ rows }) {
  return (
    <Table
      headers={['Agent', 'Type', 'Invocations', 'Avg Duration', 'Success Rate']}
      empty={!rows?.length}
    >
      {rows?.map((r, i) => {
        const sr = r.success_rate ?? 0
        const srColor = sr >= 90 ? 'text-emerald-400' : sr >= 70 ? 'text-amber-400' : 'text-red-400'
        return (
          <tr key={i} className="hover:bg-slate-700/30 transition-colors">
            <Td className="font-medium text-white">{r.agent_name ?? r.name ?? '—'}</Td>
            <Td>
              <Badge color={agentTypeColor(r.agent_type ?? r.type)}>
                {formatLabel(r.agent_type ?? r.type ?? '—')}
              </Badge>
            </Td>
            <Td>{(r.total_invocations ?? r.invocations ?? 0).toLocaleString()}</Td>
            <Td className="text-slate-400">
              {r.avg_duration_ms != null
                ? `${(r.avg_duration_ms / 1000).toFixed(2)}s`
                : r.avg_duration != null
                ? `${r.avg_duration}`
                : '—'}
            </Td>
            <Td><span className={`font-medium ${srColor}`}>{sr.toFixed(1)}%</span></Td>
          </tr>
        )
      })}
    </Table>
  )
}

function UserActivityTable({ rows }) {
  return (
    <Table
      headers={['Name', 'Email', 'Role', 'Actions', 'Last Active']}
      empty={!rows?.length}
    >
      {rows?.map((r, i) => (
        <tr key={i} className="hover:bg-slate-700/30 transition-colors">
          <Td className="font-medium text-white">{r.user_name ?? r.name ?? '—'}</Td>
          <Td className="text-slate-400">{r.user_email ?? r.email ?? '—'}</Td>
          <Td><Badge color={roleColor(r.role)}>{formatLabel(r.role ?? '—')}</Badge></Td>
          <Td>{(r.action_count ?? r.actions ?? 0).toLocaleString()}</Td>
          <Td className="text-slate-400">
            {r.last_active ? new Date(r.last_active).toLocaleString() : '—'}
          </Td>
        </tr>
      ))}
    </Table>
  )
}

function TokenConsumptionTable({ rows, summary }) {
  return (
    <>
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Total Tokens', value: (summary.total_tokens ?? 0).toLocaleString(), color: 'text-white' },
            { label: 'Total Cost', value: `$${(summary.total_cost_usd ?? 0).toFixed(4)}`, color: 'text-emerald-400' },
            { label: 'Workflows', value: summary.workflow_count ?? '—', color: 'text-indigo-400' },
            { label: 'Avg / Workflow', value: summary.avg_tokens_per_workflow != null
              ? summary.avg_tokens_per_workflow.toLocaleString() : '—', color: 'text-amber-400' },
          ].map(s => (
            <div key={s.label} className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{s.label}</p>
              <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}
      <Table
        headers={['Workflow', 'Tokens Consumed', 'Cost (USD)']}
        empty={!rows?.length}
      >
        {rows?.map((r, i) => (
          <tr key={i} className="hover:bg-slate-700/30 transition-colors">
            <Td className="font-medium text-white">{r.workflow_name ?? r.name ?? '—'}</Td>
            <Td>{(r.total_tokens ?? r.tokens ?? 0).toLocaleString()}</Td>
            <Td className="text-emerald-400">${(r.cost_usd ?? r.cost ?? 0).toFixed(4)}</Td>
          </tr>
        ))}
      </Table>
    </>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function Reports() {
  const { reportActiveTab, setReportTab } = usePortalStore()

  const [reportTabs] = useState(() => {
    const saved = loadReportTabs()
    return saved.filter(t => t.enabled)
  })

  const [activeTab, setActiveTab] = useState('workflow_usage')
  const [reportData, setReportData] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  // Consume initial tab from portalStore
  useEffect(() => {
    if (reportActiveTab) {
      setActiveTab(reportActiveTab)
      setReportTab(null)
    }
  }, [reportActiveTab])

  const currentTab = reportTabs.find(t => t.id === activeTab)

  const loadReport = useCallback(async (tabId) => {
    const tabConfig = reportTabs.find(t => t.id === tabId)
    const fetchType = tabConfig?.data_type ?? tabId
    setLoading(true)
    setError(null)
    try {
      const data = await getReport(fetchType)
      setReportData(prev => ({ ...prev, [tabId]: data }))
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Failed to load report')
    } finally {
      setLoading(false)
    }
  }, [reportTabs])

  useEffect(() => {
    if (!reportData[activeTab]) {
      loadReport(activeTab)
    }
    setSearch('')
  }, [activeTab])

  const handleRefresh = () => loadReport(activeTab)

  const handleExport = () => {
    const d = reportData[activeTab]
    if (!d?.rows?.length) return
    exportCSV(d.rows, activeTab)
  }

  const current = reportData[activeTab]
  const rows = current?.rows ?? []
  const summary = current?.summary

  const filteredRows = search.trim()
    ? rows.filter(row =>
        Object.values(row).some(v =>
          String(v ?? '').toLowerCase().includes(search.toLowerCase())
        )
      )
    : rows

  const skeletonCols = TAB_COLS[currentTab?.data_type ?? currentTab?.id] ?? 5

  return (
    <div className="flex-1 overflow-y-auto p-6">

      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-white">Reports</h1>
          <p className="text-sm text-slate-400 mt-0.5">Detailed analytics and exportable data</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Reload
          </button>
          <button
            onClick={handleExport}
            disabled={!rows.length}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download size={14} />
            Export CSV
          </button>
        </div>
      </div>

      {/* ── Tab switcher ── */}
      <div className="flex gap-1 bg-slate-800/60 border border-slate-700 rounded-xl p-1 mb-5 overflow-x-auto">
        {reportTabs.map(tab => {
          const Icon = ICON_MAP[tab.icon] || GitBranch
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex-1 justify-center
                ${isActive
                  ? 'bg-slate-700 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                }`}
            >
              <Icon size={15} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* ── Search bar ── */}
      <div className="relative mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={`Search ${currentTab?.label ?? 'results'}…`}
          className="w-full sm:w-80 bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            <X size={13} />
          </button>
        )}
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 mb-5">
          <AlertCircle size={16} className="shrink-0" />
          <span className="text-sm">{error}</span>
          <button onClick={handleRefresh} className="ml-auto text-xs underline underline-offset-2">Retry</button>
        </div>
      )}

      {/* ── Generated at ── */}
      {current?.generated_at && (
        <p className="text-xs text-slate-500 mb-3">
          Generated: {new Date(current.generated_at).toLocaleString()}
        </p>
      )}

      {/* ── Report card ── */}
      <div className="bg-slate-800 rounded-xl border border-slate-700">
        {loading ? (
          <div className="p-5">
            <TableSkeleton cols={skeletonCols} rows={8} />
          </div>
        ) : (
          <div className="p-5">
            {activeTab === 'workflow_usage'    && <WorkflowUsageTable   rows={filteredRows} />}
            {activeTab === 'agent_performance' && <AgentPerformanceTable rows={filteredRows} />}
            {activeTab === 'user_activity'     && <UserActivityTable    rows={filteredRows} />}
            {activeTab === 'token_consumption' && <TokenConsumptionTable rows={filteredRows} summary={summary} />}
          </div>
        )}

        {/* Row count footer */}
        {!loading && rows.length > 0 && (
          <div className="border-t border-slate-700 px-5 py-3">
            <p className="text-xs text-slate-500">
              {search ? `${filteredRows.length} of ${rows.length}` : rows.length} row{rows.length !== 1 ? 's' : ''}
              {search && filteredRows.length === 0 && <span className="ml-2 text-amber-400">No matches</span>}
            </p>
          </div>
        )}
      </div>

    </div>
  )
}
