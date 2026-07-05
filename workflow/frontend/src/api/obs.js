// Frontend observability client: batched logs, events, traces, metrics.
// Posts to backend /observability/* endpoints. No external deps.
import axios from 'axios'

const BASE_URL = 'http://localhost:8000'
const SESSION_ID = (() => {
  let s = sessionStorage.getItem('wf-obs-session')
  if (!s) {
    s = `s-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    sessionStorage.setItem('wf-obs-session', s)
  }
  return s
})()

// Dedicated axios instance to avoid feedback loops in the main interceptor.
const _http = axios.create({ baseURL: BASE_URL, timeout: 8000 })

// ── Buffers + flush ────────────────────────────────────────────────
const LOG_BUFFER = []
const EVENT_BUFFER = []
const FLUSH_INTERVAL_MS = 2500
const MAX_BUFFER = 50
let _flushing = false

function _currentUserId() {
  try {
    const raw = localStorage.getItem('wf-user')
    return raw ? (JSON.parse(raw).id || null) : null
  } catch { return null }
}

async function _flush() {
  if (_flushing) return
  if (LOG_BUFFER.length === 0 && EVENT_BUFFER.length === 0) return
  _flushing = true
  try {
    if (LOG_BUFFER.length) {
      const batch = LOG_BUFFER.splice(0, LOG_BUFFER.length)
      try {
        await _http.post('/observability/logs/batch', { entries: batch })
      } catch { /* drop on transport failure */ }
    }
    if (EVENT_BUFFER.length) {
      const batch = EVENT_BUFFER.splice(0, EVENT_BUFFER.length)
      try {
        await _http.post('/observability/events/batch', { entries: batch })
      } catch { /* drop on transport failure */ }
    }
  } finally {
    _flushing = false
  }
}

setInterval(_flush, FLUSH_INTERVAL_MS)
window.addEventListener('beforeunload', () => {
  // Best-effort sync flush via sendBeacon
  if (navigator.sendBeacon) {
    if (LOG_BUFFER.length) {
      navigator.sendBeacon(`${BASE_URL}/observability/logs/batch`,
        new Blob([JSON.stringify({ entries: LOG_BUFFER })], { type: 'application/json' }))
    }
    if (EVENT_BUFFER.length) {
      navigator.sendBeacon(`${BASE_URL}/observability/events/batch`,
        new Blob([JSON.stringify({ entries: EVENT_BUFFER })], { type: 'application/json' }))
    }
  }
})

// ── Public API ─────────────────────────────────────────────────────
export function log(level, message, extra = {}) {
  const entry = {
    level, message, source: 'frontend', logger: extra.logger || 'app',
    trace_id: extra.trace_id || null,
    span_id: extra.span_id || null,
    user_id: _currentUserId(),
    workflow_id: extra.workflow_id || null,
    extra: extra.extra || {},
  }
  LOG_BUFFER.push(entry)
  if (LOG_BUFFER.length >= MAX_BUFFER) _flush()
}

export function trackEvent(kind, name, attributes = {}) {
  const entry = {
    kind, name,
    url: window.location?.href,
    user_id: _currentUserId(),
    session_id: SESSION_ID,
    duration_ms: attributes.duration_ms,
    status: attributes.status,
    attributes: { ...attributes },
    ts: new Date().toISOString(),
  }
  delete entry.attributes.duration_ms
  delete entry.attributes.status
  EVENT_BUFFER.push(entry)
  if (EVENT_BUFFER.length >= MAX_BUFFER) _flush()
}

export async function startTrace(name, attributes = {}) {
  try {
    const r = await _http.post('/observability/traces/start', {
      name, source: 'frontend', attributes, user_id: _currentUserId(),
    })
    return r.data
  } catch { return null }
}

export async function endTrace(trace_id, status = 'ok') {
  if (!trace_id) return
  try { await _http.post('/observability/traces/end', { trace_id, status }) }
  catch { /* swallow */ }
}

export async function startSpan(trace_id, name, parent_span_id = null, attributes = {}) {
  if (!trace_id) return null
  try {
    const r = await _http.post('/observability/traces/span', { trace_id, name, parent_span_id, attributes })
    return r.data?.span_id
  } catch { return null }
}

export async function endSpan(trace_id, span_id, status = 'ok', attributes = {}) {
  if (!trace_id || !span_id) return
  try { await _http.post('/observability/traces/span/end', { trace_id, span_id, status, attributes }) }
  catch { /* swallow */ }
}

export function recordMetric(name, value, labels = {}) {
  try { _http.post('/observability/metrics', { name, value, labels }) }
  catch { /* swallow */ }
}

// ── Read APIs (used by Live Monitor + Dashboard) ───────────────────
const _http_authed = axios.create({ baseURL: BASE_URL })
_http_authed.interceptors.request.use(cfg => {
  const token = localStorage.getItem('wf-token')
  if (token) cfg.headers['Authorization'] = `Bearer ${token}`
  return cfg
})

export const fetchLogs    = (params = {}) => _http_authed.get('/observability/logs',    { params }).then(r => r.data)
export const fetchTraces  = (params = {}) => _http_authed.get('/observability/traces',  { params }).then(r => r.data)
export const fetchTrace   = (id)          => _http_authed.get(`/observability/traces/${id}`).then(r => r.data)
export const fetchEvents  = (params = {}) => _http_authed.get('/observability/events',  { params }).then(r => r.data)
export const fetchStream  = (params = {}) => _http_authed.get('/observability/stream',  { params }).then(r => r.data)
export const fetchMetricsSnapshot = (window_minutes = 60) =>
  _http_authed.get('/observability/metrics/snapshot', { params: { window_minutes } }).then(r => r.data)

// ── Browser-side auto-instrumentation ──────────────────────────────
let _installed = false
export function installAutoInstrumentation() {
  if (_installed) return
  _installed = true

  // Global JS errors
  window.addEventListener('error', (ev) => {
    log('error', `JS error: ${ev.message}`, {
      logger: 'window.onerror',
      extra: { filename: ev.filename, lineno: ev.lineno, colno: ev.colno },
    })
    trackEvent('error', ev.message || 'unknown', {
      status: 'error',
      attributes: { filename: ev.filename, lineno: ev.lineno },
    })
  })

  window.addEventListener('unhandledrejection', (ev) => {
    log('error', `Unhandled promise rejection: ${ev.reason}`, { logger: 'unhandledrejection' })
    trackEvent('error', String(ev.reason || 'unhandledrejection'), { status: 'error' })
  })

  // Page load timing
  if (performance && performance.timing) {
    setTimeout(() => {
      const t = performance.timing
      const navStart = t.navigationStart
      if (!navStart) return
      const ttfb = t.responseStart - navStart
      const domReady = t.domContentLoadedEventEnd - navStart
      const loadEvt = t.loadEventEnd - navStart
      trackEvent('nav', 'page_load', {
        duration_ms: loadEvt,
        attributes: { ttfb_ms: ttfb, dom_ready_ms: domReady },
      })
    }, 0)
  }

  log('info', 'Frontend observability initialized', { logger: 'obs' })
}

export const obsSessionId = () => SESSION_ID
