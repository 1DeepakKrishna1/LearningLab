import React, { useEffect, useRef, useState } from 'react'
import {
  Activity, AlertCircle, ArrowDown, Bug, ChevronDown, ChevronRight,
  Cpu, Eye, EyeOff, Filter, Globe, Hash, Pause, Play, Radio, RefreshCw,
  Search, Server, Terminal, TimerReset, X, Zap,
} from 'lucide-react'
import { fetchStream, fetchTrace } from '../../api/obs'

const POLL_MS = 2000
const MAX_KEEP = 500

// ── Helpers ───────────────────────────────────────────────────────
const LEVEL_COLOR = {
  debug:    'text-slate-400',
  info:     'text-slate-200',
  warn:     'text-amber-400',
  error:    'text-red-400',
  critical: 'text-red-300',
}
const LEVEL_BADGE = {
  debug:    'bg-slate-700/60 text-slate-300 border-slate-600',
  info:     'bg-sky-500/15 text-sky-300 border-sky-500/30',
  warn:     'bg-amber-500/15 text-amber-300 border-amber-500/30',
  error:    'bg-red-500/15 text-red-300 border-red-500/30',
  critical: 'bg-red-600/20 text-red-200 border-red-500/40',
}
const STATUS_COLOR = {
  ok:           'text-emerald-400',
  error:        'text-red-400',
  running:      'text-sky-400',
  client_error: 'text-amber-400',
  pending:      'text-amber-300',
}
const EVENT_BADGE = {
  api:   'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  nav:   'bg-purple-500/15 text-purple-300 border-purple-500/30',
  click: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  error: 'bg-red-500/15 text-red-300 border-red-500/30',
  event: 'bg-slate-700/60 text-slate-300 border-slate-600',
}
function shortTs(iso) {
  if (!iso) return ''
  return iso.slice(11, 19)  // HH:MM:SS from ISO Z
}
function formatMs(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

// ── Tab pill ──────────────────────────────────────────────────────
function TabPill({ icon: Icon, label, count, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors
        ${active
          ? 'bg-indigo-600 text-white border-indigo-500'
          : 'bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-500'}`}
    >
      <Icon size={13} />
      <span>{label}</span>
      <span className={`ml-1 px-1.5 py-0.5 rounded-full text-[10px] ${active ? 'bg-indigo-700' : 'bg-slate-700'}`}>
        {count}
      </span>
    </button>
  )
}

// ── Metric mini-card ──────────────────────────────────────────────
function MetricCard({ label, value, hint, icon: Icon, color }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 flex items-center gap-3">
      {Icon && (
        <div className={`p-1.5 rounded-md ${color || 'bg-slate-700'}`}>
          <Icon size={14} className="text-white" />
        </div>
      )}
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-wider text-slate-400">{label}</div>
        <div className="text-base font-semibold text-white truncate">{value}</div>
        {hint && <div className="text-[10px] text-slate-500">{hint}</div>}
      </div>
    </div>
  )
}

// ── Sparkline (for live req/min) ──────────────────────────────────
function Sparkline({ data, accessor, height = 36, color = 'rgb(99,102,241)' }) {
  if (!data?.length) return <div className="h-full" />
  const vals = data.map(accessor)
  const max  = Math.max(1, ...vals)
  const w    = 100
  const step = w / Math.max(1, vals.length - 1)
  const points = vals.map((v, i) => `${i * step},${height - (v / max) * height}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="w-full h-full">
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
    </svg>
  )
}

// ── Log row ───────────────────────────────────────────────────────
function LogRow({ entry, onSelectTrace }) {
  const lvlClass = LEVEL_COLOR[entry.level] || 'text-slate-200'
  const badgeClass = LEVEL_BADGE[entry.level] || LEVEL_BADGE.info
  return (
    <div className="flex items-start gap-3 py-1.5 px-3 border-b border-slate-800 hover:bg-slate-800/40 group">
      <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap mt-0.5">{shortTs(entry.ts)}</span>
      <span className={`text-[10px] px-1.5 py-0.5 rounded border whitespace-nowrap ${badgeClass}`}>{entry.level}</span>
      <span className="text-[10px] text-slate-400 whitespace-nowrap mt-0.5 hidden md:inline">{entry.source}/{entry.logger}</span>
      <span className={`flex-1 text-xs font-mono ${lvlClass} break-all`}>{entry.message}</span>
      {entry.trace_id && (
        <button
          onClick={() => onSelectTrace(entry.trace_id)}
          title="View trace"
          className="opacity-0 group-hover:opacity-100 text-[10px] text-indigo-400 hover:text-indigo-300 whitespace-nowrap"
        >
          {entry.trace_id.slice(0, 8)}…
        </button>
      )}
    </div>
  )
}

// ── Trace row ─────────────────────────────────────────────────────
function TraceRow({ trace, onSelect }) {
  const sc = STATUS_COLOR[trace.status] || 'text-slate-300'
  return (
    <button
      onClick={() => onSelect(trace.trace_id)}
      className="w-full text-left flex items-center gap-3 py-1.5 px-3 border-b border-slate-800 hover:bg-slate-800/40"
    >
      <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap">{shortTs(trace.started_at)}</span>
      <span className={`text-xs font-medium whitespace-nowrap ${sc}`}>{trace.status}</span>
      <span className="text-[10px] text-slate-500 whitespace-nowrap">{trace.source}</span>
      <span className="flex-1 text-xs font-mono text-slate-200 break-all truncate">{trace.name}</span>
      <span className="text-[10px] text-slate-400 whitespace-nowrap">{trace.span_count} span</span>
      <span className="text-[10px] text-slate-300 font-mono whitespace-nowrap">{formatMs(trace.duration_ms)}</span>
    </button>
  )
}

// ── Event row ─────────────────────────────────────────────────────
function EventRow({ entry }) {
  const badge = EVENT_BADGE[entry.kind] || EVENT_BADGE.event
  return (
    <div className="flex items-start gap-3 py-1.5 px-3 border-b border-slate-800 hover:bg-slate-800/40">
      <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap mt-0.5">{shortTs(entry.ts)}</span>
      <span className={`text-[10px] px-1.5 py-0.5 rounded border whitespace-nowrap ${badge}`}>{entry.kind}</span>
      <span className="flex-1 text-xs font-mono text-slate-200 break-all">{entry.name}</span>
      {entry.duration_ms != null && (
        <span className="text-[10px] text-slate-400 whitespace-nowrap">{Math.round(entry.duration_ms)} ms</span>
      )}
      {entry.status && (
        <span className={`text-[10px] whitespace-nowrap ${STATUS_COLOR[entry.status] || 'text-slate-400'}`}>{entry.status}</span>
      )}
    </div>
  )
}

// ── Trace detail (waterfall) ──────────────────────────────────────
function TraceDetail({ traceId, onClose }) {
  const [trace, setTrace] = useState(null)
  const [err, setErr]     = useState(null)

  useEffect(() => {
    let cancel = false
    setTrace(null); setErr(null)
    fetchTrace(traceId)
      .then(t => { if (!cancel) setTrace(t) })
      .catch(e => { if (!cancel) setErr(e.message) })
    return () => { cancel = true }
  }, [traceId])

  if (err) {
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-red-400">Failed to load trace: {err}</div>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={16}/></button>
        </div>
      </div>
    )
  }
  if (!trace) {
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 text-sm text-slate-400">
        Loading trace…
      </div>
    )
  }

  const totalMs = trace.duration_ms || trace.spans.reduce((a, s) => Math.max(a, s.duration_ms || 0), 0) || 1
  const rootStart = new Date(trace.started_at).getTime()

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2 min-w-0">
          <Hash size={14} className="text-indigo-400 shrink-0" />
          <span className="text-xs text-slate-400">Trace</span>
          <span className="text-xs font-mono text-slate-200 truncate">{trace.trace_id}</span>
          <span className={`text-xs ml-2 ${STATUS_COLOR[trace.status] || 'text-slate-300'}`}>{trace.status}</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-slate-400">{formatMs(trace.duration_ms)}</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={16}/></button>
        </div>
      </div>
      <div className="p-3 max-h-[420px] overflow-y-auto">
        <div className="text-xs text-slate-300 mb-2">
          <span className="font-medium">{trace.name}</span>
          <span className="text-slate-500"> · {trace.spans.length} span{trace.spans.length === 1 ? '' : 's'}</span>
        </div>
        <div className="space-y-1">
          {trace.spans.map((sp, i) => {
            const spStart = sp.started_at ? new Date(sp.started_at).getTime() - rootStart : 0
            const dur = sp.duration_ms || 0
            const leftPct  = Math.max(0, Math.min(100, (spStart / totalMs) * 100))
            const widthPct = Math.max(1, Math.min(100 - leftPct, (dur / totalMs) * 100))
            const isRoot = !sp.parent_span_id
            const status = sp.status || 'ok'
            const barColor =
              status === 'error' ? 'bg-red-500/70' :
              status === 'running' ? 'bg-sky-500/70' :
              'bg-indigo-500/70'
            return (
              <div key={sp.span_id} className="flex items-center gap-3">
                <div className="w-44 flex items-center gap-1 truncate">
                  {!isRoot && <ChevronRight size={11} className="text-slate-500 shrink-0" />}
                  <span className="text-xs font-mono text-slate-200 truncate">{sp.name}</span>
                </div>
                <div className="flex-1 relative h-5 bg-slate-800 rounded">
                  <div
                    className={`absolute top-0 bottom-0 rounded ${barColor}`}
                    style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                    title={`${sp.name} · ${formatMs(dur)}`}
                  />
                </div>
                <div className="w-20 text-right text-[10px] text-slate-400 font-mono whitespace-nowrap">{formatMs(dur)}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────
export default function LiveMonitor() {
  const [tab, setTab]                  = useState('all') // all | logs | traces | events | metrics
  const [paused, setPaused]            = useState(false)
  const [logs, setLogs]                = useState([])
  const [traces, setTraces]            = useState([])
  const [events, setEvents]            = useState([])
  const [metrics, setMetrics]          = useState(null)
  const [autoScroll, setAutoScroll]    = useState(true)
  const [search, setSearch]            = useState('')
  const [logLevel, setLogLevel]        = useState('')
  const [logSource, setLogSource]      = useState('')
  const [eventKind, setEventKind]      = useState('')
  const [selectedTrace, setSelectedTrace] = useState(null)
  const [lastUpdate, setLastUpdate]    = useState(null)
  const [error, setError]              = useState(null)

  const sinceRefs = useRef({ log: null, trace: null, event: null })
  const scrollRef = useRef(null)

  // ── Poll loop ─────────────────────────────────────────────
  useEffect(() => {
    let mounted = true
    let timer = null
    async function tick() {
      if (paused) return
      try {
        const snap = await fetchStream({
          log_since: sinceRefs.current.log || '',
          trace_since: sinceRefs.current.trace || '',
          event_since: sinceRefs.current.event || '',
          limit: 200,
        })
        if (!mounted) return
        setError(null)
        setLastUpdate(new Date())
        setMetrics(snap.metrics)
        if (snap.logs?.length) {
          setLogs(prev => [...prev, ...snap.logs].slice(-MAX_KEEP))
          sinceRefs.current.log = snap.logs[snap.logs.length - 1].ts
        }
        if (snap.traces?.length) {
          // Merge by trace_id (latest wins)
          const byId = new Map()
          ;[...traces, ...snap.traces].forEach(t => byId.set(t.trace_id, t))
          const merged = Array.from(byId.values())
            .sort((a, b) => (a.started_at < b.started_at ? 1 : -1))
            .slice(0, MAX_KEEP)
          setTraces(merged)
          sinceRefs.current.trace = snap.traces
            .map(t => t.ended_at || t.started_at)
            .sort()
            .pop()
        }
        if (snap.frontend_events?.length) {
          setEvents(prev => [...prev, ...snap.frontend_events].slice(-MAX_KEEP))
          sinceRefs.current.event = snap.frontend_events[snap.frontend_events.length - 1].ts
        }
      } catch (e) {
        if (mounted) setError(e?.response?.data?.detail || e.message)
      }
    }
    tick()
    timer = setInterval(tick, POLL_MS)
    return () => { mounted = false; if (timer) clearInterval(timer) }
    // eslint-disable-next-line
  }, [paused])

  // Auto-scroll bottom on new logs/events
  useEffect(() => {
    if (!autoScroll || !scrollRef.current) return
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [logs, events, traces, tab, autoScroll])

  // ── Filters ──────────────────────────────────────────────
  const filteredLogs = logs.filter(l => {
    if (logLevel && l.level !== logLevel) return false
    if (logSource && l.source !== logSource) return false
    if (search && !`${l.message} ${l.logger}`.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })
  const filteredTraces = traces.filter(t => {
    if (search && !`${t.name} ${t.trace_id}`.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })
  const filteredEvents = events.filter(e => {
    if (eventKind && e.kind !== eventKind) return false
    if (search && !`${e.name} ${e.url || ''}`.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  // ── Metric tiles ─────────────────────────────────────────
  const tot = metrics?.totals || { requests: 0, errors: 0, avg_duration_ms: 0, error_rate_pct: 0 }
  const tr  = metrics?.traces || { active: 0, finished: 0, p50_ms: 0, p95_ms: 0 }
  const fe  = metrics?.frontend || { events_total: 0, events_5m: 0 }
  const lg  = metrics?.logs || { total: 0, by_level: {} }

  return (
    <div className="flex flex-col" style={{ minHeight: 'calc(100vh - 140px)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <Radio size={18} className={`${paused ? 'text-slate-500' : 'text-emerald-400 animate-pulse'}`} />
          <h1 className="text-xl font-semibold text-white">Live Monitor</h1>
          <span className="text-[10px] text-slate-400">
            {paused ? 'Paused' : (lastUpdate ? `Updated ${lastUpdate.toLocaleTimeString()}` : 'Connecting…')}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPaused(p => !p)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs border ${paused ? 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300' : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500'}`}
          >
            {paused ? <><Play size={12}/> Resume</> : <><Pause size={12}/> Pause</>}
          </button>
          <button
            onClick={() => setAutoScroll(s => !s)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs border ${autoScroll ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-300' : 'bg-slate-800 border-slate-700 text-slate-300'}`}
            title="Toggle auto-scroll"
          >
            {autoScroll ? <ArrowDown size={12}/> : <EyeOff size={12}/>}
            Auto-scroll
          </button>
          <button
            onClick={() => { setLogs([]); setTraces([]); setEvents([]); sinceRefs.current = { log: null, trace: null, event: null } }}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:border-slate-500 text-xs"
          >
            <RefreshCw size={12}/> Clear
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-300 rounded-lg px-3 py-2 text-xs mb-3">
          <AlertCircle size={14}/> Stream error: {error}
        </div>
      )}

      {/* Metric tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-3">
        <MetricCard label="Requests / 60m" value={tot.requests.toLocaleString()} icon={Zap} color="bg-indigo-500/60" />
        <MetricCard label="Error rate" value={`${tot.error_rate_pct}%`} hint={`${tot.errors} errors`} icon={Bug} color={tot.error_rate_pct > 5 ? 'bg-red-500/60' : 'bg-emerald-500/60'} />
        <MetricCard label="Avg latency" value={`${tot.avg_duration_ms} ms`} icon={TimerReset} color="bg-sky-500/60" />
        <MetricCard label="Active traces" value={tr.active} hint={`${tr.finished} finished`} icon={Activity} color="bg-purple-500/60" />
        <MetricCard label="p95 trace" value={`${tr.p95_ms} ms`} hint={`p50: ${tr.p50_ms} ms`} icon={Cpu} color="bg-amber-500/60" />
        <MetricCard label="Frontend events" value={fe.events_total} hint={`${fe.events_5m} in 5m`} icon={Globe} color="bg-emerald-500/60" />
      </div>

      {/* Spark + log breakdown row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 md:col-span-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] uppercase tracking-wider text-slate-400">Requests / min (last 60)</span>
            <span className="text-[10px] text-slate-500">{metrics?.series?.length || 0} points</span>
          </div>
          <div style={{ height: 60 }}>
            <Sparkline data={metrics?.series || []} accessor={d => d.requests} />
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Logs by level</div>
          <div className="grid grid-cols-5 gap-1 mt-2">
            {['debug','info','warn','error','critical'].map(lvl => (
              <div key={lvl} className="flex flex-col items-center">
                <span className={`text-base font-semibold ${LEVEL_COLOR[lvl]}`}>{lg.by_level?.[lvl] ?? 0}</span>
                <span className="text-[9px] text-slate-500 uppercase">{lvl}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs + filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <TabPill icon={Eye}      label="All"     count={filteredLogs.length + filteredTraces.length + filteredEvents.length} active={tab === 'all'}    onClick={() => setTab('all')} />
        <TabPill icon={Terminal} label="Logs"    count={filteredLogs.length}    active={tab === 'logs'}   onClick={() => setTab('logs')} />
        <TabPill icon={Hash}     label="Traces"  count={filteredTraces.length}  active={tab === 'traces'} onClick={() => setTab('traces')} />
        <TabPill icon={Globe}    label="Events"  count={filteredEvents.length}  active={tab === 'events'} onClick={() => setTab('events')} />
        <div className="flex-1 min-w-[200px]" />
        <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5">
          <Search size={12} className="text-slate-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search…"
            className="bg-transparent outline-none text-xs text-slate-100 w-44 placeholder-slate-500"
          />
        </div>
        {(tab === 'logs' || tab === 'all') && (
          <>
            <select value={logLevel} onChange={e => setLogLevel(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-1.5">
              <option value="">All levels</option>
              {['debug','info','warn','error','critical'].map(l => <option key={l} value={l}>{l}</option>)}
            </select>
            <select value={logSource} onChange={e => setLogSource(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-1.5">
              <option value="">All sources</option>
              <option value="backend">backend</option>
              <option value="frontend">frontend</option>
              <option value="workflow">workflow</option>
            </select>
          </>
        )}
        {(tab === 'events' || tab === 'all') && (
          <select value={eventKind} onChange={e => setEventKind(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-1.5">
            <option value="">All kinds</option>
            {['api','nav','click','error','event'].map(k => <option key={k} value={k}>{k}</option>)}
          </select>
        )}
      </div>

      {/* Trace detail */}
      {selectedTrace && (
        <div className="mb-3">
          <TraceDetail traceId={selectedTrace} onClose={() => setSelectedTrace(null)} />
        </div>
      )}

      {/* Stream pane */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto bg-slate-900 border border-slate-700 rounded-xl" style={{ minHeight: 420, maxHeight: 'calc(100vh - 520px)' }}>
        {tab === 'logs' && filteredLogs.map(l => <LogRow key={l.id} entry={l} onSelectTrace={setSelectedTrace} />)}
        {tab === 'traces' && filteredTraces.map(t => <TraceRow key={t.trace_id} trace={t} onSelect={setSelectedTrace} />)}
        {tab === 'events' && filteredEvents.map(e => <EventRow key={e.id} entry={e} />)}
        {tab === 'all' && (
          <>
            <div className="px-3 py-2 text-[10px] uppercase tracking-wider text-slate-500 sticky top-0 bg-slate-900 border-b border-slate-800 flex items-center gap-2">
              <Terminal size={11}/> Logs
            </div>
            {filteredLogs.slice(-50).map(l => <LogRow key={l.id} entry={l} onSelectTrace={setSelectedTrace} />)}
            <div className="px-3 py-2 text-[10px] uppercase tracking-wider text-slate-500 sticky top-0 bg-slate-900 border-b border-t border-slate-800 flex items-center gap-2">
              <Hash size={11}/> Traces
            </div>
            {filteredTraces.slice(0, 30).map(t => <TraceRow key={t.trace_id} trace={t} onSelect={setSelectedTrace} />)}
            <div className="px-3 py-2 text-[10px] uppercase tracking-wider text-slate-500 sticky top-0 bg-slate-900 border-b border-t border-slate-800 flex items-center gap-2">
              <Globe size={11}/> Frontend events
            </div>
            {filteredEvents.slice(-30).map(e => <EventRow key={e.id} entry={e} />)}
          </>
        )}
        {((tab === 'logs' && !filteredLogs.length) ||
          (tab === 'traces' && !filteredTraces.length) ||
          (tab === 'events' && !filteredEvents.length)) && (
          <div className="p-8 text-center text-xs text-slate-500">
            No {tab} yet. {paused ? 'Resume the stream to see new entries.' : 'Waiting for new data…'}
          </div>
        )}
      </div>
    </div>
  )
}
