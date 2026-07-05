import { useState } from 'react'
import { Plus, X } from 'lucide-react'

function parseValue(raw) {
  const trimmed = raw.trim()
  if (trimmed === '') return ''
  try { return JSON.parse(trimmed) } catch { return raw }
}

function displayValue(v) {
  return typeof v === 'string' ? v : JSON.stringify(v)
}

export default function PropertiesEditor({ value = {}, onChange }) {
  const [pairs, setPairs] = useState(
    () => Object.entries(value).map(([k, v]) => ({ key: k, raw: displayValue(v) }))
  )

  function sync(next) {
    setPairs(next)
    const obj = {}
    next.forEach(({ key, raw }) => {
      if (key.trim()) obj[key.trim()] = parseValue(raw)
    })
    onChange(obj)
  }

  const add    = ()      => sync([...pairs, { key: '', raw: '' }])
  const remove = (i)     => sync(pairs.filter((_, idx) => idx !== i))
  const setKey = (i, k)  => sync(pairs.map((p, idx) => idx === i ? { ...p, key: k } : p))
  const setRaw = (i, r)  => sync(pairs.map((p, idx) => idx === i ? { ...p, raw: r } : p))

  return (
    <div className="space-y-2">
      {pairs.length === 0 && (
        <p className="text-[11px] text-slate-500 italic">No properties defined.</p>
      )}
      {pairs.map(({ key, raw }, i) => (
        <div key={i} className="flex gap-1.5 items-center">
          <input
            value={key}
            onChange={e => setKey(i, e.target.value)}
            placeholder="key"
            className="w-36 shrink-0 bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-[11px] text-indigo-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <span className="text-slate-600 text-xs shrink-0">:</span>
          <input
            value={raw}
            onChange={e => setRaw(i, e.target.value)}
            placeholder='value — string, 42, true, {}, []'
            className="flex-1 bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <button
            type="button"
            onClick={() => remove(i)}
            className="p-1 text-slate-600 hover:text-red-400 transition-colors shrink-0"
          >
            <X size={13} />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="flex items-center gap-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors pt-0.5"
      >
        <Plus size={12} /> Add property
      </button>
    </div>
  )
}
