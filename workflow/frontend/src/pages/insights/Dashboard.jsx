import React, { useEffect, useState } from 'react'
import {
  Activity, GitBranch, FileEdit, CheckCircle2, XCircle, Zap,
  Timer, ShieldCheck, Coins, Wrench, Bot, Users, TrendingUp,
  BarChart2, AlertCircle, RefreshCw, ArrowUpRight
} from 'lucide-react'
import { getDashboardMetrics, getWorkflows } from '../../api/api'
import { loadWidgets } from '../../dashboardConfig'
import usePortalStore, { NAV } from '../../store/portalStore'
import DrillDownSection from './DrillDownSection'

// ── Skeleton pulse block ──────────────────────────────────────────────────────
function Skeleton({ className = '' }) {
  return <div className={`animate-pulse bg-slate-700 rounded ${className}`} />
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function Card({ children, className = '', onClick }) {
  const interactive = !!onClick
  return (
    <div
      className={`group bg-slate-800 rounded-xl border border-slate-700 p-5 transition-all duration-200 ${interactive ? 'cursor-pointer hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-900/20' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

// ── Small coloured dot ────────────────────────────────────────────────────────
function Dot({ color }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${color} mr-2`} />
}

// ── Badge ─────────────────────────────────────────────────────────────────────
function Badge({ children, color = 'indigo' }) {
  const map = {
    indigo: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    emerald: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    amber: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    red: 'bg-red-500/20 text-red-300 border-red-500/30',
    slate: 'bg-slate-700 text-slate-300 border-slate-600',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${map[color] ?? map.slate}`}>
      {children}
    </span>
  )
}

// ── Progress bar ──────────────────────────────────────────────────────────────
function ProgressBar({ value, max = 100, colorClass }) {
  const pct = Math.min(100, Math.max(0, max > 0 ? (value / max) * 100 : 0))
  return (
    <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden mt-2">
      <div
        className={`h-full rounded-full transition-all duration-700 ${colorClass}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

// ── Mini bar chart ────────────────────────────────────────────────────────────
function BarChart({ data = [], barColor = 'bg-indigo-500' }) {
  const maxVal = Math.max(...data.map(d => d.count), 1)
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-end gap-1.5 flex-1 min-h-0 pt-2">
        {data.map((d, i) => {
          const heightPct = Math.max(4, (d.count / maxVal) * 100)
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-1 min-w-0">
              <span className="text-slate-400 text-[10px] leading-none">{d.count}</span>
              <div
                className={`w-full rounded-t-sm ${barColor} transition-all duration-500`}
                style={{ height: `${heightPct}%` }}
                title={`${d.day}: ${d.count}`}
              />
            </div>
          )
        })}
      </div>
      <div className="flex items-end gap-1.5 mt-1">
        {data.map((d, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-slate-500 text-[9px] leading-none truncate block">
              {d.day ? d.day.slice(5) : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Skeleton card rows ────────────────────────────────────────────────────────
function SkeletonRow({ cols }) {
  return (
    <div className={`grid gap-4 ${cols}`}>
      {Array.from({ length: parseInt(cols.match(/\d+/)?.[0] ?? 3) }).map((_, i) => (
        <Card key={i}>
          <Skeleton className="h-4 w-24 mb-3" />
          <Skeleton className="h-8 w-16 mb-2" />
          <Skeleton className="h-3 w-32" />
        </Card>
      ))}
    </div>
  )
}

// ── Grid cols helper ──────────────────────────────────────────────────────────
function gridCols(n) {
  return ['', 'sm:grid-cols-1', 'sm:grid-cols-2', 'sm:grid-cols-3', 'sm:grid-cols-4'][Math.min(n, 4)] || 'sm:grid-cols-4'
}

// ── Period label helper ───────────────────────────────────────────────────────
const PERIOD_LABELS = { '7d': 'Last 7 Days', '30d': 'Last 30 Days', '90d': 'Last 90 Days', 'all': 'All Time' }

// ── All groups in display order ───────────────────────────────────────────────
const ALL_GROUPS = ['Workflows', 'Executions', 'Performance', 'Tokens', 'Trends', 'Library', 'Users']

// ── Widget → group mapping for card filtering ─────────────────────────────────
const WIDGET_GROUP = {
  total_workflows:   'Workflows',
  active_workflows:  'Workflows',
  draft_workflows:   'Workflows',
  total_executions:  'Executions',
  completed:         'Executions',
  failed:            'Executions',
  success_rate:      'Executions',
  avg_duration:      'Performance',
  sla_compliance:    'Performance',
  token_usage:       'Tokens',
  exec_trend:        'Trends',
  token_trend:       'Trends',
  component_library: 'Library',
  platform_users:    'Users',
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [period, setPeriod] = useState('7d')
  const [selectedGroup, setSelectedGroup] = useState('All')
  const [workflowId, setWorkflowId] = useState('')
  const [workflowList, setWorkflowList] = useState([])
  const [widgets, setWidgets] = useState([])

  const { setCurrentPage, setReportTab } = usePortalStore()

  useEffect(() => { setWidgets(loadWidgets()) }, [])

  useEffect(() => {
    getWorkflows().then(data => setWorkflowList(Array.isArray(data) ? data : [])).catch(() => {})
  }, [])

  const load = async (showRefresh = false, p = period, wid = workflowId) => {
    try {
      if (showRefresh) setRefreshing(true)
      else setLoading(true)
      setError(null)
      const data = await getDashboardMetrics(p, wid)
      setMetrics(data)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Failed to load metrics')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => { load(false, period, workflowId) }, [workflowId])

  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod)
    load(false, newPeriod, workflowId)
  }

  const navigate = (reportLink) => {
    setReportTab(reportLink)
    setCurrentPage(NAV.INSIGHTS_REPORTS)
  }

  const isVisible = (id) => {
    const w = widgets.find(w => w.id === id)
    if (w && !w.enabled) return false
    if (selectedGroup === 'All') return true
    return WIDGET_GROUP[id] === selectedGroup
  }

  const widgetLink = (id) => widgets.find(w => w.id === id)?.report_link ?? 'workflow_usage'
  const widgetTitle = (id) => widgets.find(w => w.id === id)?.title

  // ── Error state ─────────────────────────────────────────────
  if (error) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4">
          <AlertCircle size={18} className="shrink-0" />
          <span className="text-sm">{error}</span>
          <button onClick={() => load()} className="ml-auto text-xs underline underline-offset-2">Retry</button>
        </div>
      </div>
    )
  }

  // ── Loading skeleton ────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-8 w-28" />
        </div>
        <Skeleton className="h-10 w-full rounded-xl" />
        <SkeletonRow cols="grid-cols-3" />
        <SkeletonRow cols="grid-cols-4" />
        <SkeletonRow cols="grid-cols-3" />
        <div className="grid grid-cols-2 gap-4">
          {[0, 1].map(i => (
            <Card key={i}>
              <Skeleton className="h-4 w-32 mb-4" />
              <div className="flex items-end gap-1.5 h-24">
                {Array.from({ length: 7 }).map((_, j) => (
                  <Skeleton key={j} className="flex-1" style={{ height: `${30 + Math.random() * 60}%` }} />
                ))}
              </div>
            </Card>
          ))}
        </div>
        <SkeletonRow cols="grid-cols-2" />
      </div>
    )
  }

  const m = metrics || {}
  const ex   = m.executions  || { success_rate: 0, total: 0, completed: 0, failed: 0, running: 0 }
  const perf = m.performance || { avg_duration_ms: 0, sla_compliance_pct: 0 }
  const tok  = m.tokens      || { usage_pct: 0, today: 0, monthly_budget: 0 }
  const lib  = m.library     || { tools: 0, agents: 0 }
  const usr  = m.users       || { total: 0, active: 0 }
  const tr   = m.trends      || { executions_7d: [], tokens_7d: [] }

  const successRateColor =
    ex.success_rate >= 90 ? 'text-emerald-400' :
    ex.success_rate >= 70 ? 'text-amber-400' : 'text-red-400'

  const slaColor =
    perf.sla_compliance_pct >= 90 ? 'bg-emerald-500' :
    perf.sla_compliance_pct >= 70 ? 'bg-amber-500' : 'bg-red-500'

  const tokenBarColor =
    tok.usage_pct <= 70 ? 'bg-emerald-500' :
    tok.usage_pct <= 90 ? 'bg-amber-500' : 'bg-red-500'

  // ── Row visible counts ──────────────────────────────────────
  const row1Ids = ['total_workflows', 'active_workflows', 'draft_workflows']
  const row2Ids = ['total_executions', 'completed', 'failed', 'success_rate']
  const row3Ids = ['avg_duration', 'sla_compliance', 'token_usage']
  const row4Ids = ['exec_trend', 'token_trend']
  const row5Ids = ['component_library', 'platform_users']

  const row1Visible = row1Ids.filter(isVisible)
  const row2Visible = row2Ids.filter(isVisible)
  const row3Visible = row3Ids.filter(isVisible)
  const row4Visible = row4Ids.filter(isVisible)
  const row5Visible = row5Ids.filter(isVisible)

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-white">Dashboard</h1>
            <span className="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded-full">
              {PERIOD_LABELS[period]}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-0.5">Platform health and usage at a glance</p>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-sm transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* ── Filter bar ── */}
      <div className="flex flex-wrap items-center gap-3 bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3">
        {/* Time period pills */}
        <div className="flex items-center gap-1.5 mr-2">
          {[
            { label: '7 Days',  value: '7d'  },
            { label: '30 Days', value: '30d' },
            { label: '90 Days', value: '90d' },
            { label: 'All Time', value: 'all' },
          ].map(opt => (
            <button
              key={opt.value}
              onClick={() => handlePeriodChange(opt.value)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                period === opt.value
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-600'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="w-px h-5 bg-slate-700 hidden sm:block" />

        {/* Workflow filter */}
        <div className="flex items-center gap-2">
          <GitBranch size={13} className="text-slate-500 shrink-0" />
          <span className="text-xs text-slate-500 whitespace-nowrap">Workflow:</span>
          <select
            value={workflowId}
            onChange={e => setWorkflowId(e.target.value)}
            className="px-2 py-1 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer max-w-[180px]"
          >
            <option value="">All Workflows</option>
            {workflowList.map(wf => (
              <option key={wf.id} value={wf.id}>{wf.name}</option>
            ))}
          </select>
        </div>

        <div className="w-px h-5 bg-slate-700 hidden sm:block" />

        {/* Group pills — single select with All */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {['All', ...ALL_GROUPS].map(group => (
            <button
              key={group}
              onClick={() => setSelectedGroup(group)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                selectedGroup === group
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
              }`}
            >
              {group}
            </button>
          ))}
        </div>
      </div>

      {/* ── Row 1: Workflow Stats ── */}
      {row1Visible.length > 0 && (
        <div className={`grid grid-cols-1 ${gridCols(row1Visible.length)} gap-4`}>
          {isVisible('total_workflows') && (
            <Card onClick={() => navigate(widgetLink('total_workflows'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('total_workflows') || 'Total Workflows'}
                  </p>
                  <p className="text-3xl font-bold text-white mt-1">{m.workflows.total}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-indigo-500/10 rounded-lg">
                    <GitBranch size={18} className="text-indigo-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <Badge color="indigo">{m.workflows.active} active</Badge>
                <Badge color="amber">{m.workflows.draft} draft</Badge>
              </div>
            </Card>
          )}

          {isVisible('active_workflows') && (
            <Card onClick={() => navigate(widgetLink('active_workflows'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('active_workflows') || 'Active Workflows'}
                  </p>
                  <p className="text-3xl font-bold text-white mt-1">{m.workflows.active}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-emerald-500/10 rounded-lg">
                    <Activity size={18} className="text-emerald-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <p className="text-sm text-slate-400 mt-3 flex items-center">
                <Dot color="bg-emerald-400" />
                Running and available for execution
              </p>
            </Card>
          )}

          {isVisible('draft_workflows') && (
            <Card onClick={() => navigate(widgetLink('draft_workflows'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('draft_workflows') || 'Draft Workflows'}
                  </p>
                  <p className="text-3xl font-bold text-white mt-1">{m.workflows.draft}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-amber-500/10 rounded-lg">
                    <FileEdit size={18} className="text-amber-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <p className="text-sm text-slate-400 mt-3 flex items-center">
                <Dot color="bg-amber-400" />
                In progress, not yet published
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ── Row 2: Execution Stats ── */}
      {row2Visible.length > 0 && (
        <div className={`grid grid-cols-2 ${gridCols(row2Visible.length)} gap-4`}>
          {isVisible('total_executions') && (
            <Card onClick={() => navigate(widgetLink('total_executions'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('total_executions') || 'Total Executions'}
                  </p>
                  <p className="text-3xl font-bold text-white mt-1">{ex.total.toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-slate-700 rounded-lg">
                    <Zap size={18} className="text-slate-300" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-3">{ex.running} currently running</p>
            </Card>
          )}

          {isVisible('completed') && (
            <Card onClick={() => navigate(widgetLink('completed'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('completed') || 'Completed'}
                  </p>
                  <p className="text-3xl font-bold text-emerald-400 mt-1">{ex.completed.toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-emerald-500/10 rounded-lg">
                    <CheckCircle2 size={18} className="text-emerald-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-3">
                {ex.total > 0 ? ((ex.completed / ex.total) * 100).toFixed(1) : 0}% of total
              </p>
            </Card>
          )}

          {isVisible('failed') && (
            <Card onClick={() => navigate(widgetLink('failed'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('failed') || 'Failed'}
                  </p>
                  <p className="text-3xl font-bold text-red-400 mt-1">{ex.failed.toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-red-500/10 rounded-lg">
                    <XCircle size={18} className="text-red-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-3">
                {ex.total > 0 ? ((ex.failed / ex.total) * 100).toFixed(1) : 0}% failure rate
              </p>
            </Card>
          )}

          {isVisible('success_rate') && (
            <Card onClick={() => navigate(widgetLink('success_rate'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('success_rate') || 'Success Rate'}
                  </p>
                  <p className={`text-3xl font-bold mt-1 ${successRateColor}`}>
                    {ex.success_rate.toFixed(1)}%
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-slate-700 rounded-lg">
                    <TrendingUp size={18} className="text-slate-300" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <ProgressBar
                value={ex.success_rate}
                max={100}
                colorClass={
                  ex.success_rate >= 90 ? 'bg-emerald-500' :
                  ex.success_rate >= 70 ? 'bg-amber-500' : 'bg-red-500'
                }
              />
            </Card>
          )}
        </div>
      )}

      {/* ── Row 3: Performance + Tokens ── */}
      {row3Visible.length > 0 && (
        <div className={`grid grid-cols-1 ${gridCols(row3Visible.length)} gap-4`}>
          {isVisible('avg_duration') && (
            <Card onClick={() => navigate(widgetLink('avg_duration'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('avg_duration') || 'Avg Duration'}
                  </p>
                  <p className="text-3xl font-bold text-white mt-1">
                    {(perf.avg_duration_ms / 1000).toFixed(2)}
                    <span className="text-lg text-slate-400 font-normal ml-1">s</span>
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-indigo-500/10 rounded-lg">
                    <Timer size={18} className="text-indigo-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-3">Per execution average</p>
            </Card>
          )}

          {isVisible('sla_compliance') && (
            <Card onClick={() => navigate(widgetLink('sla_compliance'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('sla_compliance') || 'SLA Compliance'}
                  </p>
                  <p className={`text-3xl font-bold mt-1 ${
                    perf.sla_compliance_pct >= 90 ? 'text-emerald-400' :
                    perf.sla_compliance_pct >= 70 ? 'text-amber-400' : 'text-red-400'
                  }`}>
                    {perf.sla_compliance_pct.toFixed(1)}%
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-emerald-500/10 rounded-lg">
                    <ShieldCheck size={18} className="text-emerald-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <ProgressBar value={perf.sla_compliance_pct} max={100} colorClass={slaColor} />
              <p className="text-xs text-slate-500 mt-2">
                {perf.sla_compliance_pct >= 90 ? 'Within target' :
                 perf.sla_compliance_pct >= 70 ? 'Below target' : 'Critical — below threshold'}
              </p>
            </Card>
          )}

          {isVisible('token_usage') && (
            <Card onClick={() => navigate(widgetLink('token_usage'))}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {widgetTitle('token_usage') || 'Token Usage'}
                  </p>
                  <p className="text-3xl font-bold text-white mt-1">
                    {tok.usage_pct.toFixed(1)}
                    <span className="text-lg text-slate-400 font-normal ml-1">%</span>
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="p-2 bg-amber-500/10 rounded-lg">
                    <Coins size={18} className="text-amber-400" />
                  </div>
                  <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
              <ProgressBar value={tok.usage_pct} max={100} colorClass={tokenBarColor} />
              <div className="flex justify-between text-xs text-slate-500 mt-2">
                <span>Today: {tok.today.toLocaleString()}</span>
                <span>Budget: {tok.monthly_budget.toLocaleString()}</span>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Row 4: Trend Charts ── */}
      {row4Visible.length > 0 && (
        <div className={`grid grid-cols-1 ${gridCols(row4Visible.length)} gap-4`}>
          {isVisible('exec_trend') && (
            <Card className="flex flex-col" onClick={() => navigate(widgetLink('exec_trend'))}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <BarChart2 size={16} className="text-indigo-400" />
                  <h3 className="text-sm font-medium text-white">
                    {widgetTitle('exec_trend') || 'Executions Last 7 Days'}
                  </h3>
                </div>
                <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
              </div>
              <div className="flex-1" style={{ minHeight: '120px' }}>
                <BarChart data={tr.executions_7d} barColor="bg-indigo-500" />
              </div>
            </Card>
          )}

          {isVisible('token_trend') && (
            <Card className="flex flex-col" onClick={() => navigate(widgetLink('token_trend'))}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <BarChart2 size={16} className="text-emerald-400" />
                  <h3 className="text-sm font-medium text-white">
                    {widgetTitle('token_trend') || 'Token Consumption Trend'}
                  </h3>
                </div>
                <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
              </div>
              <div className="flex-1" style={{ minHeight: '120px' }}>
                <BarChart data={tr.tokens_7d} barColor="bg-emerald-500" />
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Row 5: Library + Users ── */}
      {row5Visible.length > 0 && (
        <div className={`grid grid-cols-1 ${gridCols(row5Visible.length)} gap-4`}>
          {isVisible('component_library') && (
            <Card onClick={() => navigate(widgetLink('component_library'))}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-purple-500/10 rounded-lg">
                    <GitBranch size={16} className="text-purple-400" />
                  </div>
                  <h3 className="text-sm font-medium text-white">
                    {widgetTitle('component_library') || 'Component Library'}
                  </h3>
                </div>
                <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3 bg-slate-700/50 rounded-lg p-3">
                  <div className="p-2 bg-indigo-500/10 rounded-lg">
                    <Wrench size={16} className="text-indigo-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{lib.tools}</p>
                    <p className="text-xs text-slate-400">Tools</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 bg-slate-700/50 rounded-lg p-3">
                  <div className="p-2 bg-emerald-500/10 rounded-lg">
                    <Bot size={16} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{lib.agents}</p>
                    <p className="text-xs text-slate-400">Agents</p>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {isVisible('platform_users') && (
            <Card onClick={() => navigate(widgetLink('platform_users'))}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-cyan-500/10 rounded-lg">
                    <Users size={16} className="text-cyan-400" />
                  </div>
                  <h3 className="text-sm font-medium text-white">
                    {widgetTitle('platform_users') || 'Platform Users'}
                  </h3>
                </div>
                <ArrowUpRight size={12} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3 bg-slate-700/50 rounded-lg p-3">
                  <div className="p-2 bg-cyan-500/10 rounded-lg">
                    <Users size={16} className="text-cyan-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{usr.total}</p>
                    <p className="text-xs text-slate-400">Total</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 bg-slate-700/50 rounded-lg p-3">
                  <div className="p-2 bg-emerald-500/10 rounded-lg">
                    <Activity size={16} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{usr.active}</p>
                    <p className="text-xs text-slate-400">Active</p>
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-3">
                {usr.total > 0 ? ((usr.active / usr.total) * 100).toFixed(0) : 0}% of users currently active
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ── Detail View — hidden when All is selected ── */}
      {selectedGroup !== 'All' && (
        <DrillDownSection
          visibleGroups={[selectedGroup]}
          period={period}
          workflowId={workflowId}
        />
      )}

    </div>
  )
}
