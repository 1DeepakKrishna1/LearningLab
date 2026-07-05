import { useState } from 'react'

const s = {
  card: {
    background: 'var(--surface2)',
    border: '1px solid var(--yellow)',
    borderRadius: 10,
    padding: '14px 16px',
    marginTop: 8,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  icon: { fontSize: 16, color: 'var(--yellow)' },
  title: { fontSize: 13, fontWeight: 600, color: 'var(--yellow)' },
  subtitle: { fontSize: 11, color: 'var(--text3)', marginLeft: 'auto' },
  fieldGroup: { marginBottom: 10 },
  label: {
    display: 'block',
    fontSize: 11,
    fontWeight: 500,
    color: 'var(--text2)',
    marginBottom: 4,
    letterSpacing: '0.02em',
  },
  required: { color: 'var(--red)', marginLeft: 3 },
  input: {
    width: '100%',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    padding: '7px 10px',
    color: 'var(--text)',
    fontSize: 13,
    fontFamily: "'Inter', sans-serif",
    outline: 'none',
    transition: 'border-color 0.15s',
  },
  select: {
    width: '100%',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    padding: '7px 10px',
    color: 'var(--text)',
    fontSize: 13,
    fontFamily: "'Inter', sans-serif",
    outline: 'none',
    cursor: 'pointer',
  },
  textarea: {
    width: '100%',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    padding: '7px 10px',
    color: 'var(--text)',
    fontSize: 13,
    fontFamily: "'Inter', sans-serif",
    outline: 'none',
    resize: 'vertical',
    minHeight: 64,
  },
  submitRow: { display: 'flex', gap: 8, marginTop: 12 },
  submitBtn: (disabled) => ({
    flex: 1,
    padding: '8px 0',
    borderRadius: 6,
    border: 'none',
    background: disabled
      ? 'var(--surface)'
      : 'linear-gradient(135deg, var(--yellow), var(--orange))',
    color: disabled ? 'var(--text3)' : '#111',
    fontSize: 13,
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.15s',
  }),
}

export default function InputForm({ event, onSubmit, onSkip }) {
  const fields = event.required_fields || []
  const [values, setValues] = useState(() => {
    const init = {}
    fields.forEach(f => { init[f.key] = f.current ?? '' })
    return init
  })

  const canSubmit = fields.every(f => !f.required || (values[f.key] !== '' && values[f.key] !== null))

  function set(key, val) {
    setValues(prev => ({ ...prev, [key]: val }))
  }

  function handleSubmit() {
    if (!canSubmit) return
    onSubmit(event.node_id, values)
  }

  if (fields.length === 0) {
    return (
      <div style={{ ...s.card, borderColor: 'var(--accent)' }}>
        <div style={s.header}>
          <span style={{ ...s.icon, color: 'var(--accent)' }}>ℹ</span>
          <span style={{ ...s.title, color: 'var(--accent)' }}>
            {event.node_name} — no fields required
          </span>
        </div>
        <button style={s.submitBtn(false)} onClick={() => onSubmit(event.node_id, {})}>
          Continue
        </button>
      </div>
    )
  }

  return (
    <div style={s.card}>
      <div style={s.header}>
        <span style={s.icon}>⚠</span>
        <span style={s.title}>Input required: {event.node_name}</span>
        <span style={s.subtitle}>{event.node_type?.replace(/_/g, ' ')}</span>
      </div>

      {fields.map(field => (
        <div key={field.key} style={s.fieldGroup}>
          <label style={s.label}>
            {field.label}
            {field.required && <span style={s.required}>*</span>}
          </label>

          {field.type === 'select' ? (
            <select
              style={s.select}
              value={values[field.key] ?? ''}
              onChange={e => set(field.key, e.target.value)}
            >
              <option value="">— select —</option>
              {field.options?.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          ) : field.type === 'textarea' ? (
            <textarea
              style={s.textarea}
              value={values[field.key] ?? ''}
              placeholder={field.placeholder || ''}
              onChange={e => set(field.key, e.target.value)}
            />
          ) : (
            <input
              style={s.input}
              type="text"
              value={values[field.key] ?? ''}
              placeholder={field.placeholder || ''}
              onChange={e => set(field.key, e.target.value)}
              onFocus={e => { e.target.style.borderColor = 'var(--accent)' }}
              onBlur={e => { e.target.style.borderColor = 'var(--border)' }}
            />
          )}
        </div>
      ))}

      <div style={s.submitRow}>
        <button style={s.submitBtn(!canSubmit)} disabled={!canSubmit} onClick={handleSubmit}>
          Submit & Continue
        </button>
      </div>
    </div>
  )
}
