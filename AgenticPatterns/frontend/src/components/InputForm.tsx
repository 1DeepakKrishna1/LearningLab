import { useState, useEffect, FormEvent } from 'react'
import type { Pattern, PatternField } from '../types'
import './InputForm.css'

interface Props {
  pattern: Pattern
  onSubmit: (inputs: Record<string, unknown>) => void
  isLoading: boolean
}

function buildDefaults(fields: PatternField[]): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  fields.forEach((f) => {
    out[f.name] = f.default
  })
  return out
}

export default function InputForm({ pattern, onSubmit, isLoading }: Props) {
  const [values, setValues] = useState<Record<string, unknown>>(buildDefaults(pattern.fields))

  // Reset form when pattern changes
  useEffect(() => {
    setValues(buildDefaults(pattern.fields))
  }, [pattern.id])

  function set(name: string, value: unknown) {
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit(values)
  }

  return (
    <form className="input-form" onSubmit={handleSubmit}>
      <div className="input-form-header">
        <div className="input-form-pattern-name">
          <span className="input-form-pattern-id">{String(pattern.id).padStart(2, '0')}</span>
          {pattern.name}
        </div>
        <p className="input-form-description">{pattern.description}</p>
      </div>

      <div className="input-form-fields">
        {pattern.fields.map((field) => (
          <FieldControl
            key={field.name}
            field={field}
            value={values[field.name]}
            onChange={(v) => set(field.name, v)}
          />
        ))}
      </div>

      <button className="input-form-submit" type="submit" disabled={isLoading}>
        {isLoading ? (
          <>
            <span className="spinner" />
            Running…
          </>
        ) : (
          <>
            <span className="submit-icon">▶</span>
            Run Pattern
          </>
        )}
      </button>
    </form>
  )
}

interface FieldControlProps {
  field: PatternField
  value: unknown
  onChange: (v: unknown) => void
}

function FieldControl({ field, value, onChange }: FieldControlProps) {
  const strVal = String(value ?? field.default ?? '')

  if (field.type === 'boolean') {
    return (
      <label className="field field--checkbox">
        <input
          type="checkbox"
          checked={Boolean(value ?? field.default)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span>{field.label}</span>
      </label>
    )
  }

  if (field.type === 'select') {
    return (
      <label className="field">
        <span className="field-label">{field.label}</span>
        <select
          className="field-select"
          value={strVal}
          onChange={(e) => onChange(e.target.value)}
        >
          {(field.options ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </label>
    )
  }

  if (field.type === 'number') {
    return (
      <label className="field">
        <span className="field-label">{field.label}</span>
        <input
          className="field-input"
          type="number"
          value={Number(value ?? field.default)}
          min={field.min}
          max={field.max}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      </label>
    )
  }

  if (field.type === 'textarea') {
    return (
      <label className="field">
        <span className="field-label">{field.label}</span>
        <textarea
          className="field-textarea"
          value={strVal}
          rows={4}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    )
  }

  // text (default)
  return (
    <label className="field">
      <span className="field-label">{field.label}</span>
      <input
        className="field-input"
        type="text"
        value={strVal}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  )
}
