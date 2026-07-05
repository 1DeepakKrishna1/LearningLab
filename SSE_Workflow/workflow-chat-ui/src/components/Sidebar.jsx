import { useState, useEffect } from 'react'
import { fetchWorkflows } from '../api.js'

const MODES = [
  { value: 'FULL_WITH_SSE', label: 'Full (Live SSE)', desc: 'Continuous real-time updates' },
  { value: 'STEP_MODE',     label: 'Step Mode',      desc: 'Pause & confirm after each node' },
  { value: 'FULL_NO_SSE',   label: 'No SSE',         desc: 'Synchronous, no streaming' },
]

const s = {
  root: {
    width: 280,
    minWidth: 280,
    background: 'var(--surface)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    padding: '20px 16px 12px',
    borderBottom: '1px solid var(--border)',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  logoIcon: {
    width: 28,
    height: 28,
    background: 'linear-gradient(135deg, var(--accent), var(--accent2))',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 14,
    fontWeight: 700,
    color: '#fff',
  },
  logoText: { fontSize: 15, fontWeight: 700, color: 'var(--text)' },
  subtitle: { fontSize: 11, color: 'var(--text3)', marginTop: 2 },
  section: { padding: '12px 16px 0' },
  sectionLabel: {
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text3)',
    marginBottom: 8,
  },
  modeBtn: (active) => ({
    display: 'block',
    width: '100%',
    textAlign: 'left',
    padding: '8px 10px',
    marginBottom: 4,
    borderRadius: 6,
    border: `1px solid ${active ? 'var(--accent)' : 'transparent'}`,
    background: active ? 'rgba(108,142,245,0.12)' : 'transparent',
    cursor: 'pointer',
    transition: 'all 0.15s',
  }),
  modeBtnLabel: (active) => ({
    fontSize: 13,
    fontWeight: 500,
    color: active ? 'var(--accent)' : 'var(--text)',
  }),
  modeBtnDesc: { fontSize: 11, color: 'var(--text3)', marginTop: 1 },
  wfList: { flex: 1, overflowY: 'auto', padding: '8px 16px 16px' },
  wfItem: (active) => ({
    padding: '10px 12px',
    marginBottom: 6,
    borderRadius: 8,
    border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
    background: active ? 'rgba(108,142,245,0.08)' : 'var(--surface2)',
    cursor: 'pointer',
    transition: 'all 0.15s',
  }),
  wfName: (active) => ({
    fontSize: 13,
    fontWeight: 500,
    color: active ? 'var(--accent)' : 'var(--text)',
    marginBottom: 3,
    lineHeight: 1.3,
  }),
  wfMeta: {
    display: 'flex',
    gap: 8,
    alignItems: 'center',
  },
  badge: {
    fontSize: 10,
    padding: '1px 6px',
    borderRadius: 10,
    background: 'var(--surface)',
    color: 'var(--text3)',
    border: '1px solid var(--border)',
  },
  startBtn: (disabled) => ({
    margin: '0 16px 16px',
    padding: '10px 0',
    borderRadius: 8,
    border: 'none',
    background: disabled
      ? 'var(--surface2)'
      : 'linear-gradient(135deg, var(--accent), var(--accent2))',
    color: disabled ? 'var(--text3)' : '#fff',
    fontSize: 13,
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.15s',
  }),
  loading: { color: 'var(--text3)', fontSize: 13, textAlign: 'center', padding: 24 },
  err: { color: 'var(--red)', fontSize: 12, padding: '8px 16px' },
}

export default function Sidebar({ onExecute, onSelect, executing }) {
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedWf, setSelectedWf] = useState(null)
  const [selectedMode, setSelectedMode] = useState('FULL_WITH_SSE')

  useEffect(() => {
    fetchWorkflows()
      .then(list => { setWorkflows(list); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  const canStart = selectedWf && !executing

  return (
    <div style={s.root}>
      <div style={s.header}>
        <div style={s.logo}>
          <div style={s.logoIcon}>W</div>
          <span style={s.logoText}>Workflow AI</span>
        </div>
        <div style={s.subtitle}>Select a workflow and execution mode</div>
      </div>

      <div style={s.section}>
        <div style={s.sectionLabel}>Execution Mode</div>
        {MODES.map(m => (
          <button
            key={m.value}
            style={s.modeBtn(selectedMode === m.value)}
            onClick={() => setSelectedMode(m.value)}
          >
            <div style={s.modeBtnLabel(selectedMode === m.value)}>{m.label}</div>
            <div style={s.modeBtnDesc}>{m.desc}</div>
          </button>
        ))}
      </div>

      <div style={{ ...s.section, marginTop: 12 }}>
        <div style={s.sectionLabel}>Workflows ({workflows.length})</div>
      </div>

      <div style={s.wfList}>
        {loading && <div style={s.loading}>Loading workflows…</div>}
        {error && <div style={s.err}>{error}</div>}
        {workflows.map(wf => (
          <div
            key={wf.id}
            style={s.wfItem(selectedWf?.id === wf.id)}
            onClick={() => { setSelectedWf(wf); onSelect?.(wf) }}
          >
            <div style={s.wfName(selectedWf?.id === wf.id)}>{wf.name}</div>
            <div style={s.wfMeta}>
              <span style={s.badge}>{wf.node_count} nodes</span>
              {wf.tags?.slice(0, 2).map(t => (
                <span key={t} style={s.badge}>{t}</span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        style={s.startBtn(!canStart)}
        disabled={!canStart}
        onClick={() => canStart && onExecute(selectedWf, selectedMode)}
      >
        {executing ? 'Running…' : selectedWf ? `Run "${selectedWf.name}"` : 'Select a workflow'}
      </button>
    </div>
  )
}
