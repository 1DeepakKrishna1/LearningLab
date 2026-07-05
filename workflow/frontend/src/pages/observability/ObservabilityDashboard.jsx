import React, { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertCircle, Bug, ChevronRight, Clock, Cpu, Globe, Hash,
  Layers, RefreshCw, Server, ShieldCheck, Terminal, TimerReset, TrendingDown,
  TrendingUp, Zap,
} from 'lucide-react'
import {
  fetchMetricsSnapshot, fetchLogs, fetchTraces, fetchEvents,
} from '../../api/obs'
import usePortalStore, { NAV } from '../../store/portalStore'

const PERIODS = [
  { label: '15 m', value: 15  },
  { label: '60 m', value: 60  },
  { label: '4 h',  value: 240 },
]

// ── Skeleton ─────────────────────────────────────────────────────
function Skeleton({ className = '' }) {
  return <div className={`animate-pulse bg-slate-700 rounded ${className}`} />
}

// ── Card ─────────────────────────────────────────────────────────
function Card({ children, className = '', onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-slate-800 rounded-xl border border-slate-700 p-5 ${onClick ? 'cursor-pointer hover:border-indigo-500/50 transition-colors' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

// ── KPI tile ─────────────────────────────────────────────────────
function Kpi({ label, value, hint, icon: Icon, color, trend }) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-wider text-slate-400">{label}</p>
          <p className="text-3xl font-bold text-white mt-1 truncate">{value}</p>
          {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
        </div>
        {Icon && (
          <div className={`p-2 rounded-lg ${color || 'bg-slate-700'}`}>
            <Icon size={18} className="text-white" />
          </div>
        )}
      </div>
      {trend != null && (
        <div className="flex items-center gap-1 mt-3 text-xs">
          {trend >= 0
            ? <TrendingUp size={12} className="text-emerald-400" />
            : <TrendingDown size={12} className="text-red-400" />}
          <span className={trend >= 0 ? 'text-emerald-400' : 'text-red-400'}>
            {Math.abs(trend).toFixed(1)}%
          </span>
          <span className="text-slate-500">vs prior window</span>
        </div>
      )}
    </Card>
  )
}

// ── Stacked bar chart (requests + errors) ────────────────────────
function StackedBars({ series, height = 140 }) {
  if (!series?.length) return <div className="text-xs text-slate-500">No data yet.</div>
  const maxV = Math.max(1, ...series.map(s => s.requests))
  return (
    <div className="flex items-end gap-0.5" style={{ height }}>
      {series.map((s, i) => {
        const total = Math.max(0, (s.requests / maxV) * 100)
        const errorPct = s.requests > 0 ? (s.errors / s.requests) * 100 : 0
        return (
          <div key={i} className="flex-1 flex flex-col-reverse min-w-0" title={`${s.minute} · ${s.requests} req · ${s.errors} err · ${s.avg_duration_ms}ms`}>
            <div className="w-full bg-indigo-500/80 rounded-t-sm" style={{ height: `${total}%`, minHeight: total > 0 ? '2px' : 0 }}>
              {errorPct > 0 && (
                <div className="w-full bg-red-500/90 rounded-t-sm" style={{ height: `${errorPct}%` }} />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Line chart (latency) ─────────────────────────────────────────
function LineChart({ series, accessor, height = 100, color = 'rgb(56,189,248)' }) {
  if (!series?.length) return <div className="text-xs text-slate-500">No data.</div>
  const vals = series.map(accessor)
  const max  = Math.max(1, ...vals)
  const w    = 100
  const step = w / Math.max(1, vals.length - 1)
  const points = vals.map((v, i) => `${i * step},${height - (v / max) * height}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="w-full" style={{ height }}>
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
    </svg>
  )
}

// ── Distribution bar ─────────────────────────────────────────────
function Distribution({ data, labels, colors }) {
  const total = data.reduce((a, b) => a + b, 0) || 1
  return (
    <div>
      <div className="flex h-2 rounded-full overflow-hidden bg-slate-700">
        {data.map((v, i) => (
          <div key={i} className={colors[i]} style={{ width: `${(v / total) * 100}%` }} title={`${labels[i]}: ${v}`} />
        ))}
      </div>
      <div className="flex justify-between text-[10px] text-slate-400 mt-2">
        {labels.map((l, i) => (
          <div key={i} className="flex items-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-full ${colors[i]}`} />
            <span>{l} ({data[i]})</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Top endpoints table ──────────────────────────────────────────
function TopEndpoints({ events }) {
  const summary = useMemo(() => {
    const map = new Map()
    for (const e of events) {
      if (e.kind !== 'api') continue
      const key = e.name || 'unknown'
      const cur = map.get(key) || { count: 0, errors: 0, totalDur: 0 }
      cur.count += 1
      cur.totalDur += (e.duration_ms || 0)
      if (e.status && e.status !== 'ok') cur.errors += 1
      map.set(key, cur)
    }
    return Array.from(map.entries())
      .map(([name, s]) => ({ name, ...s, avg: s.count ? s.totalDur / s.count : 0 }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  }, [events])

  if (!summary.length) return <div className="text-xs text-slate-500">No API calls yet.</div>
  return (
    <div className="text-xs">
      <div className="grid grid-cols-12 gap-2 py-1 text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-700">
        <span className="col-span-6">Endpoint</span>
        <span className="col-span-2 text-right">Calls</span>
        <span className="col-span-2 text-right">Errors</span>
        <span className="col-span-2 text-right">Avg ms</span>
      </div>
      {summary.map(row => (
        <div key={row.name} className="grid grid-cols-12 gap-2 py-1.5 border-b border-slate-800">
          <span className="col-span-6 font-mono text-slate-200 truncate">{row.name}</span>
          <span className="col-span-2 text-right text-slate-300">{row.count}</span>
          <span className={`col-span-2 text-right ${row.errors > 0 ? 'text-red-400' : 'text-slate-300'}`}>{row.errors}</span>
          <span className="col-span-2 text-right text-slate-300">{Math.round(row.avg)}</span>
        </div>
      ))}
    </div>
  )
}

// ── Recent traces preview ────────────────────────────────────────
function RecentTraces({ traces, onOpen }) {
  if (!traces.length) return <div className="text-xs text-slate-500">No traces yet.</div>
  return (
    <div className="space-y-1">
      {traces.slice(0, 8).map(t => (
        <button
          key={t.trace_id}
          onClick={() => onOpen()}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-700/40 text-left"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${t.status === 'error' ? 'bg-red-400' : t.status === 'running' ? 'bg-sky-400' : 'bg-emerald-400'}`} />
          <span className="text-xs font-mono text-slate-200 truncate flex-1">{t.name}</span>
          <span className="text-[10px] text-slate-400 whitespace-nowrap">{t.span_count} spans</span>
          <span className="text-[10px] text-slate-400 font-mono whitespace-nowrap">{t.duration_ms != null ? `${t.duration_ms}ms` : '—'}</span>
          <ChevronRight size={12} className="text-slate-500" />
        </button>
      ))}
    </div>
  )
}

// ── Main ─────────────────────────────────────────────────────────
export default function ObservabilityDashboard() {
  const [windowM, setWindowM]   = useState(60)
  const [snapshot, setSnapshot] = useState(null)
  const [recentLogs, setRecentLogs]   = useState([])
  const [recentTraces, setRecentTraces] = useState([])
  const [recentEvents, setRecentEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const { setCurrentPage } = usePortalStore()

  const load = async (silent = false) => {
    try {
      if (silent) setRefreshing(true); else setLoading(true)
      setError(null)
      const [snap, logsR, tracesR, eventsR] = await Promise.all([
        fetchMetricsSnapshot(windowM),
        fetchLogs({ limit: 200 }),
        fetchTraces({ limit: 100 }),
        fetchEvents({ limit: 200 }),
      ])
      setSnapshot(snap)
      setRecentLogs(logsR.rows || [])
      setRecentTraces(tracesR.rows || [])
      setRecentEvents(eventsR.rows || [])
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { load() }, [windowM])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-7 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-56" /><Skeleton className="h-56" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-4">
        <AlertCircle size={16} />
        <span className="text-sm">{error}</span>
        <button onClick={() => load()} className="ml-auto text-xs underline">Retry</button>
      </div>
    )
  }

  const tot = snapshot?.totals || { requests: 0, errors: 0, client_errors: 0, avg_duration_ms: 0, error_rate_pct: 0 }
  const tr  = snapshot?.traces || { active: 0, finished: 0, p50_ms: 0, p95_ms: 0 }
  const fe  = snapshot?.frontend || { events_total: 0, events_5m: 0 }
  const lg  = snapshot?.logs || { total: 0, by_level: {} }
  const series = snapshot?.series || []

  const halfPoint = Math.floor(series.length / 2)
  const prev = series.slice(0, halfPoint).reduce((a, b) => a + b.requests, 0)
  const curr = series.slice(halfPoint).reduce((a, b) => a + b.requests, 0)
  const trend = prev > 0 ? ((curr - prev) / prev) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-white">Observability Insights</h1>
            <span className="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded-full">{windowM} min window</span>
          </div>
          <p className="text-sm text-slate-400 mt-0.5">Logs, traces, metrics, and frontend events</p>
        </div>
        <div className="flex items-center gap-2">
          {PERIODS.map(p => (
            <button key={p.value} onClick={() => setWindowM(p.value)}
              className={`px-3 py-1 rounded-full text-xs font-medium ${windowM === p.value
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:text-slate-200'}`}>
              {p.label}
            </button>
          ))}
          <button onClick={() => load(true)} disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:border-slate-500 text-sm disabled:opacity-50">
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={() => setCurrentPage(NAV.OBSERVABILITY_LIVE)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm">
            <Activity size={14} /> Live Monitor
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Total Requests" value={tot.requests.toLocaleString()} icon={Zap} color="bg-indigo-500/60" trend={trend} hint={`${windowM} min`} />
        <Kpi label="Error Rate" value={`${tot.error_rate_pct}%`} hint={`${tot.errors} 5xx · ${tot.client_errors} 4xx`} icon={Bug} color={tot.error_rate_pct > 5 ? 'bg-red-500/60' : 'bg-emerald-500/60'} />
        <Kpi label="Avg Latency" value={`${tot.avg_duration_ms} ms`} hint="Backend handler time" icon={TimerReset} color="bg-sky-500/60" />
        <Kpi label="Active Traces" value={tr.active.toLocaleString()} hint={`${tr.finished} finished · p95 ${tr.p95_ms}ms`} icon={Activity} color="bg-purple-500/60" />
      </div>

      {/* Requests chart + log breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-medium text-white">Requests over time</h3>
              <p className="text-xs text-slate-500">Indigo = total · Red = errors</p>
            </div>
            <Zap size={14} className="text-indigo-400" />
          </div>
          <StackedBars series={series} />
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-white">Logs by level</h3>
            <Terminal size={14} className="text-slate-400" />
          </div>
          <div className="grid grid-cols-5 gap-1 mb-3">
            {['debug','info','warn','error','critical'].map(lvl => (
              <div key={lvl} className="text-center">
                <div className={`text-xl font-bold ${
                  lvl === 'critical' || lvl === 'error' ? 'text-red-400' :
                  lvl === 'warn' ? 'text-amber-400' :
                  lvl === 'info' ? 'text-sky-400' : 'text-slate-400'}`}>
                  {lg.by_level?.[lvl] ?? 0}
                </div>
                <div className="text-[9px] text-slate-500 uppercase">{lvl}</div>
              </div>
            ))}
          </div>
          <div className="text-xs text-slate-500 mb-1">{lg.total} buffered</div>
          <Distribution
            data={[lg.by_level?.debug ?? 0, lg.by_level?.info ?? 0, lg.by_level?.warn ?? 0, lg.by_level?.error ?? 0, lg.by_level?.critical ?? 0]}
            labels={['debug','info','warn','error','critical']}
            colors={['bg-slate-500','bg-sky-500','bg-amber-500','bg-red-500','bg-red-700']}
          />
        </Card>
      </div>

      {/* Latency line + frontend events */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-medium text-white">Avg request latency (ms)</h3>
              <p className="text-xs text-slate-500">Per-minute average over window</p>
            </div>
            <Clock size={14} className="text-sky-400" />
          </div>
          <LineChart series={series} accessor={d => d.avg_duration_ms} />
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-white">Frontend events</h3>
            <Globe size={14} className="text-emerald-400" />
          </div>
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-bold text-white">{fe.events_total}</span>
              <span className="text-xs text-slate-400">total</span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-lg font-semibold text-emerald-400">{fe.events_5m}</span>
              <span className="text-xs text-slate-400">last 5 min</span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-lg font-semibold text-sky-400">{tr.p50_ms} ms</span>
              <span className="text-xs text-slate-400">p50 trace</span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-lg font-semibold text-amber-400">{tr.p95_ms} ms</span>
              <span className="text-xs text-slate-400">p95 trace</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Bottom: top endpoints + recent traces */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-white">Top API endpoints (frontend)</h3>
            <Server size={14} className="text-indigo-400" />
          </div>
          <TopEndpoints events={recentEvents} />
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-white">Recent traces</h3>
            <Hash size={14} className="text-purple-400" />
          </div>
          <RecentTraces traces={recentTraces} onOpen={() => setCurrentPage(NAV.OBSERVABILITY_LIVE)} />
        </Card>
      </div>

      {/* Recent errors */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-white">Recent errors & warnings</h3>
          <AlertCircle size={14} className="text-red-400" />
        </div>
        <div className="text-xs">
          {recentLogs.filter(l => l.level === 'error' || l.level === 'warn' || l.level === 'critical').slice(0, 10).map(l => (
            <div key={l.id} className="flex items-start gap-3 py-1.5 border-b border-slate-800 last:border-0">
              <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap mt-0.5">{l.ts.slice(11, 19)}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded border whitespace-nowrap ${
                l.level === 'warn' ? 'bg-amber-500/15 text-amber-300 border-amber-500/30' :
                l.level === 'error' ? 'bg-red-500/15 text-red-300 border-red-500/30' :
                'bg-red-600/20 text-red-200 border-red-500/40'}`}>{l.level}</span>
              <span className="text-[10px] text-slate-400 whitespace-nowrap hidden md:inline">{l.source}/{l.logger}</span>
              <span className="flex-1 text-xs font-mono text-slate-200 break-all">{l.message}</span>
            </div>
          ))}
          {recentLogs.filter(l => l.level === 'error' || l.level === 'warn' || l.level === 'critical').length === 0 && (
            <div className="flex items-center gap-2 text-emerald-400 text-xs py-3">
              <ShieldCheck size={14} /> No errors or warnings in the buffer — all clear.
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
