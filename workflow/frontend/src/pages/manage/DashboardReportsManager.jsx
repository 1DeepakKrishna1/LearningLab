import { useState, useEffect, useCallback } from 'react'
import {
  Plus, Trash2, Pencil, ArrowUp, ArrowDown,
  Check, X, RotateCcw, Settings2, BarChart2,
  ChevronDown, AlertCircle,
} from 'lucide-react'
import {
  loadWidgets, saveWidgets,
  loadReportTabs, saveReportTabs,
  DEFAULT_WIDGETS, DEFAULT_REPORT_TABS,
  METRIC_KEYS, REPORT_OPTIONS, ACCENT_OPTIONS,
} from '../../dashboardConfig'
import useAuthStore from '../../store/authStore'
import usePortalStore from '../../store/portalStore'

// ── Helpers ───────────────────────────────────────────────────────────────────

const ACCENT_DOT = {
  indigo:  'bg-indigo-500',
  emerald: 'bg-emerald-500',
  amber:   'bg-amber-500',
  red:     'bg-red-500',
  purple:  'bg-purple-500',
  cyan:    'bg-cyan-500',
  slate:   'bg-slate-400',
  orange:  'bg-orange-500',
}

const ACCENT_BADGE = {
  indigo:  'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  emerald: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  amber:   'bg-amber-500/20  text-amber-300  border-amber-500/30',
  red:     'bg-red-500/20    text-red-300    border-red-500/30',
  purple:  'bg-purple-500/20 text-purple-300 border-purple-500/30',
  cyan:    'bg-cyan-500/20   text-cyan-300   border-cyan-500/30',
  slate:   'bg-slate-700     text-slate-300  border-slate-600',
  orange:  'bg-orange-500/20 text-orange-300 border-orange-500/30',
}

function accentDot(accent) {
  return ACCENT_DOT[accent] ?? 'bg-slate-400'
}

function accentBadgeCls(accent) {
  return ACCENT_BADGE[accent] ?? ACCENT_BADGE.slate
}

function Badge({ children, accent = 'slate' }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border whitespace-nowrap ${accentBadgeCls(accent)}`}>
      {children}
    </span>
  )
}

function DataTypeBadge({ value }) {
  const opt = REPORT_OPTIONS.find(o => o.id === value)
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 whitespace-nowrap">
      {opt ? opt.label : value}
    </span>
  )
}

// ── Reusable Toggle ────────────────────────────────────────────────────────────

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${checked ? 'bg-emerald-500' : 'bg-slate-600'}`}
    >
      <span
        className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? 'left-5' : 'left-0.5'}`}
      />
    </button>
  )
}

// ── Reusable Modal shell ───────────────────────────────────────────────────────

function Modal({ title, onClose, children, size = 'max-w-md' }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className={`bg-slate-800 border border-slate-700 rounded-xl w-full ${size} shadow-2xl`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

// ── Shared form field helpers ──────────────────────────────────────────────────

function Field({ label, required, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
    </div>
  )
}

const inputCls = 'w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500'
const selectCls = `${inputCls} appearance-none`

function SelectWrap({ children }) {
  return (
    <div className="relative">
      {children}
      <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
    </div>
  )
}

// ── Confirm dialog ─────────────────────────────────────────────────────────────

function ConfirmModal({ title, message, confirmLabel = 'Confirm', danger = true, onConfirm, onClose }) {
  return (
    <Modal title={title} onClose={onClose}>
      <p className="text-slate-300 text-sm mb-5">{message}</p>
      <div className="flex gap-3 justify-end">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className={`px-4 py-2 text-sm text-white rounded-lg transition-colors ${
            danger ? 'bg-red-600 hover:bg-red-500' : 'bg-indigo-600 hover:bg-indigo-500'
          }`}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  )
}

// ── Icon-button helpers ────────────────────────────────────────────────────────

function IconBtn({ onClick, title, disabled, danger, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`p-1.5 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
        danger
          ? 'text-slate-400 hover:text-red-400 hover:bg-red-500/10'
          : 'text-slate-400 hover:text-white hover:bg-slate-600'
      }`}
    >
      {children}
    </button>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// WIDGETS TAB
// ═══════════════════════════════════════════════════════════════════════════════

function WidgetInlineEdit({ widget, onSave, onCancel, existingGroups }) {
  const [form, setForm] = useState({
    title:       widget.title,
    accent:      widget.accent,
    report_link: widget.report_link,
    group:       widget.group,
    metric_key:  widget.metric_key || '',
  })
  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  return (
    <tr className="bg-slate-700/60">
      <td colSpan={8} className="px-4 py-3">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {/* Title */}
          <Field label="Title" required>
            <input
              required
              value={form.title}
              onChange={e => set('title', e.target.value)}
              className={inputCls}
            />
          </Field>

          {/* Group */}
          <Field label="Group">
            <SelectWrap>
              <select value={form.group} onChange={e => set('group', e.target.value)} className={selectCls}>
                {existingGroups.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </SelectWrap>
          </Field>

          {/* Accent */}
          <Field label="Accent">
            <SelectWrap>
              <select value={form.accent} onChange={e => set('accent', e.target.value)} className={selectCls}>
                {ACCENT_OPTIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </SelectWrap>
          </Field>

          {/* Report link */}
          <Field label="Report Link">
            <SelectWrap>
              <select value={form.report_link} onChange={e => set('report_link', e.target.value)} className={selectCls}>
                <option value="">— none —</option>
                {REPORT_OPTIONS.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
              </select>
            </SelectWrap>
          </Field>

          {/* Metric key — only for custom */}
          {widget.custom && (
            <Field label="Metric Key">
              <SelectWrap>
                <select value={form.metric_key} onChange={e => set('metric_key', e.target.value)} className={selectCls}>
                  <option value="">— select —</option>
                  {METRIC_KEYS.map(m => <option key={m.key} value={m.key}>{m.label}</option>)}
                </select>
              </SelectWrap>
            </Field>
          )}
        </div>
        <div className="flex gap-2 mt-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-300 bg-slate-600 hover:bg-slate-500 rounded-lg transition-colors"
          >
            <X size={13} /> Cancel
          </button>
          <button
            type="button"
            onClick={() => onSave(form)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Check size={13} /> Save
          </button>
        </div>
      </td>
    </tr>
  )
}

function AddWidgetModal({ onAdd, onClose, existingGroups }) {
  const [form, setForm] = useState({
    title:       '',
    group:       existingGroups[0] || '',
    row:         1,
    accent:      'indigo',
    report_link: REPORT_OPTIONS[0].id,
    metric_key:  METRIC_KEYS[0].key,
  })
  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.title.trim()) return
    onAdd(form)
  }

  return (
    <Modal title="Add Widget" onClose={onClose} size="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Title" required>
          <input
            required
            value={form.title}
            onChange={e => set('title', e.target.value)}
            className={inputCls}
            placeholder="e.g. Active Users"
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Group">
            <input
              value={form.group}
              onChange={e => set('group', e.target.value)}
              list="group-suggestions"
              className={inputCls}
              placeholder="Group name"
            />
            <datalist id="group-suggestions">
              {existingGroups.map(g => <option key={g} value={g} />)}
            </datalist>
          </Field>

          <Field label="Row (1–5)">
            <SelectWrap>
              <select value={form.row} onChange={e => set('row', Number(e.target.value))} className={selectCls}>
                {[1,2,3,4,5].map(n => <option key={n} value={n}>Row {n}</option>)}
              </select>
            </SelectWrap>
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Accent Color">
            <SelectWrap>
              <select value={form.accent} onChange={e => set('accent', e.target.value)} className={selectCls}>
                {ACCENT_OPTIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </SelectWrap>
          </Field>

          <Field label="Report Link">
            <SelectWrap>
              <select value={form.report_link} onChange={e => set('report_link', e.target.value)} className={selectCls}>
                <option value="">— none —</option>
                {REPORT_OPTIONS.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
              </select>
            </SelectWrap>
          </Field>
        </div>

        <Field label="Metric Key" required>
          <SelectWrap>
            <select value={form.metric_key} onChange={e => set('metric_key', e.target.value)} className={selectCls}>
              <option value="">— select —</option>
              {METRIC_KEYS.map(m => <option key={m.key} value={m.key}>{m.label}</option>)}
            </select>
          </SelectWrap>
        </Field>

        <div className="flex gap-3 justify-end pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Plus size={14} /> Add Widget
          </button>
        </div>
      </form>
    </Modal>
  )
}

function WidgetsTab({ widgets, onChange }) {
  const [editingId, setEditingId]   = useState(null)
  const [showAdd, setShowAdd]       = useState(false)
  const [confirmDel, setConfirmDel] = useState(null)   // widget object

  const existingGroups = [...new Set(widgets.map(w => w.group).filter(Boolean))]

  function move(idx, dir) {
    const next = [...widgets]
    const target = idx + dir
    if (target < 0 || target >= next.length) return
    ;[next[idx], next[target]] = [next[target], next[idx]]
    onChange(next)
  }

  function handleToggle(idx) {
    const next = widgets.map((w, i) => i === idx ? { ...w, enabled: !w.enabled } : w)
    onChange(next)
  }

  function handleReportLink(idx, val) {
    const next = widgets.map((w, i) => i === idx ? { ...w, report_link: val } : w)
    onChange(next)
  }

  function handleInlineSave(idx, form) {
    const next = widgets.map((w, i) =>
      i === idx ? { ...w, ...form, title: form.title.trim() || w.title } : w
    )
    onChange(next)
    setEditingId(null)
  }

  function handleAdd(form) {
    const newWidget = {
      id:          `custom_${Date.now()}`,
      title:       form.title.trim(),
      icon:        'BarChart2',
      accent:      form.accent,
      group:       form.group.trim() || 'Custom',
      row:         form.row,
      order:       widgets.length,
      report_link: form.report_link,
      enabled:     true,
      custom:      true,
      metric_key:  form.metric_key,
    }
    onChange([...widgets, newWidget])
    setShowAdd(false)
  }

  function handleDelete(widget) {
    onChange(widgets.filter(w => w.id !== widget.id))
    setConfirmDel(null)
  }

  return (
    <div>
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 w-16">Order</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3">Widget</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 hidden sm:table-cell">Group</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 hidden md:table-cell w-16">Row</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 hidden lg:table-cell">Report Link</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 w-20">Enabled</th>
                <th className="text-right text-xs font-medium text-slate-400 px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {widgets.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center text-slate-500 py-10 text-sm">
                    No widgets configured.
                  </td>
                </tr>
              )}
              {widgets.map((w, idx) => {
                if (editingId === w.id) {
                  return (
                    <WidgetInlineEdit
                      key={w.id}
                      widget={w}
                      existingGroups={existingGroups}
                      onSave={(form) => handleInlineSave(idx, form)}
                      onCancel={() => setEditingId(null)}
                    />
                  )
                }
                return (
                  <tr key={w.id} className="hover:bg-slate-700/50 transition-colors">
                    {/* Order buttons */}
                    <td className="px-3 py-2">
                      <div className="flex flex-col gap-0.5">
                        <IconBtn
                          onClick={() => move(idx, -1)}
                          disabled={idx === 0}
                          title="Move up"
                        >
                          <ArrowUp size={13} />
                        </IconBtn>
                        <IconBtn
                          onClick={() => move(idx, 1)}
                          disabled={idx === widgets.length - 1}
                          title="Move down"
                        >
                          <ArrowDown size={13} />
                        </IconBtn>
                      </div>
                    </td>

                    {/* Title + accent dot */}
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${accentDot(w.accent)}`} />
                        <span className="text-white font-medium truncate max-w-[180px]">{w.title}</span>
                        {w.custom && (
                          <span className="text-xs text-slate-500 border border-slate-600 rounded px-1 py-0.5 shrink-0">
                            custom
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Group */}
                    <td className="px-3 py-2 hidden sm:table-cell">
                      <Badge accent="slate">{w.group}</Badge>
                    </td>

                    {/* Row */}
                    <td className="px-3 py-2 hidden md:table-cell text-slate-400 text-center">
                      {w.row}
                    </td>

                    {/* Report link — inline select */}
                    <td className="px-3 py-2 hidden lg:table-cell">
                      <div className="relative">
                        <select
                          value={w.report_link || ''}
                          onChange={e => handleReportLink(idx, e.target.value)}
                          className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 appearance-none pr-6 max-w-[180px]"
                        >
                          <option value="">— none —</option>
                          {REPORT_OPTIONS.map(o => (
                            <option key={o.id} value={o.id}>{o.label}</option>
                          ))}
                        </select>
                        <ChevronDown size={11} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                      </div>
                    </td>

                    {/* Enabled toggle */}
                    <td className="px-3 py-2">
                      <Toggle checked={w.enabled} onChange={() => handleToggle(idx)} />
                    </td>

                    {/* Action buttons */}
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-end gap-1">
                        <IconBtn
                          onClick={() => setEditingId(w.id)}
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </IconBtn>
                        {w.custom && (
                          <IconBtn
                            onClick={() => setConfirmDel(w)}
                            title="Delete"
                            danger
                          >
                            <Trash2 size={14} />
                          </IconBtn>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Footer: Add button */}
        <div className="border-t border-slate-700 px-4 py-3 flex items-center justify-between">
          <p className="text-xs text-slate-500">{widgets.length} widget{widgets.length !== 1 ? 's' : ''}</p>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Plus size={14} /> Add Widget
          </button>
        </div>
      </div>

      {showAdd && (
        <AddWidgetModal
          onAdd={handleAdd}
          onClose={() => setShowAdd(false)}
          existingGroups={existingGroups}
        />
      )}

      {confirmDel && (
        <ConfirmModal
          title="Delete Widget"
          message={`Delete widget "${confirmDel.title}"? This cannot be undone.`}
          confirmLabel="Delete"
          danger
          onConfirm={() => handleDelete(confirmDel)}
          onClose={() => setConfirmDel(null)}
        />
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// REPORT TABS TAB
// ═══════════════════════════════════════════════════════════════════════════════

function ReportTabInlineEdit({ tab, onSave, onCancel }) {
  const [form, setForm] = useState({
    label:     tab.label,
    data_type: tab.data_type,
    icon:      tab.icon || '',
  })
  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  return (
    <tr className="bg-slate-700/60">
      <td colSpan={6} className="px-4 py-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Field label="Label" required>
            <input
              required
              value={form.label}
              onChange={e => set('label', e.target.value)}
              className={inputCls}
            />
          </Field>

          {/* Data type — only editable for custom tabs */}
          {tab.custom ? (
            <Field label="Data Type">
              <SelectWrap>
                <select
                  value={form.data_type}
                  onChange={e => set('data_type', e.target.value)}
                  className={selectCls}
                >
                  {REPORT_OPTIONS.map(o => (
                    <option key={o.id} value={o.id}>{o.label}</option>
                  ))}
                </select>
              </SelectWrap>
            </Field>
          ) : (
            <Field label="Data Type">
              <input
                value={form.data_type}
                readOnly
                className={`${inputCls} opacity-50 cursor-not-allowed`}
              />
            </Field>
          )}

          {tab.custom && (
            <Field label="Icon (lucide name)">
              <input
                value={form.icon}
                onChange={e => set('icon', e.target.value)}
                className={inputCls}
                placeholder="e.g. BarChart2"
              />
            </Field>
          )}
        </div>
        <div className="flex gap-2 mt-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-300 bg-slate-600 hover:bg-slate-500 rounded-lg transition-colors"
          >
            <X size={13} /> Cancel
          </button>
          <button
            type="button"
            onClick={() => onSave(form)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Check size={13} /> Save
          </button>
        </div>
      </td>
    </tr>
  )
}

function AddReportTabModal({ onAdd, onClose }) {
  const [form, setForm] = useState({
    label:     '',
    data_type: REPORT_OPTIONS[0].id,
  })
  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.label.trim()) return
    onAdd(form)
  }

  return (
    <Modal title="Add Report Tab" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Label" required>
          <input
            required
            value={form.label}
            onChange={e => set('label', e.target.value)}
            className={inputCls}
            placeholder="e.g. My Custom Report"
          />
        </Field>

        <Field label="Data Type">
          <SelectWrap>
            <select
              value={form.data_type}
              onChange={e => set('data_type', e.target.value)}
              className={selectCls}
            >
              {REPORT_OPTIONS.map(o => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
          </SelectWrap>
        </Field>

        <p className="text-xs text-slate-500">
          The Data Type determines which backend report endpoint this tab fetches.
        </p>

        <div className="flex gap-3 justify-end pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Plus size={14} /> Add Tab
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ReportTabsTab({ tabs, onChange }) {
  const [editingId, setEditingId]   = useState(null)
  const [showAdd, setShowAdd]       = useState(false)
  const [confirmDel, setConfirmDel] = useState(null)

  function move(idx, dir) {
    const next = [...tabs]
    const target = idx + dir
    if (target < 0 || target >= next.length) return
    ;[next[idx], next[target]] = [next[target], next[idx]]
    onChange(next)
  }

  function handleToggle(idx) {
    const next = tabs.map((t, i) => i === idx ? { ...t, enabled: !t.enabled } : t)
    onChange(next)
  }

  function handleInlineSave(idx, form) {
    const next = tabs.map((t, i) =>
      i === idx ? { ...t, ...form, label: form.label.trim() || t.label } : t
    )
    onChange(next)
    setEditingId(null)
  }

  function handleAdd(form) {
    const newTab = {
      id:        `custom_tab_${Date.now()}`,
      label:     form.label.trim(),
      icon:      'BarChart2',
      data_type: form.data_type,
      enabled:   true,
      order:     tabs.length,
      custom:    true,
    }
    onChange([...tabs, newTab])
    setShowAdd(false)
  }

  function handleDelete(tab) {
    onChange(tabs.filter(t => t.id !== tab.id))
    setConfirmDel(null)
  }

  return (
    <div>
      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 w-16">Order</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3">Label</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 hidden sm:table-cell">Data Type</th>
                <th className="text-left text-xs font-medium text-slate-400 px-3 py-3 w-20">Enabled</th>
                <th className="text-right text-xs font-medium text-slate-400 px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {tabs.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-slate-500 py-10 text-sm">
                    No report tabs configured.
                  </td>
                </tr>
              )}
              {tabs.map((tab, idx) => {
                if (editingId === tab.id) {
                  return (
                    <ReportTabInlineEdit
                      key={tab.id}
                      tab={tab}
                      onSave={(form) => handleInlineSave(idx, form)}
                      onCancel={() => setEditingId(null)}
                    />
                  )
                }
                return (
                  <tr key={tab.id} className="hover:bg-slate-700/50 transition-colors">
                    {/* Order buttons */}
                    <td className="px-3 py-2">
                      <div className="flex flex-col gap-0.5">
                        <IconBtn
                          onClick={() => move(idx, -1)}
                          disabled={idx === 0}
                          title="Move up"
                        >
                          <ArrowUp size={13} />
                        </IconBtn>
                        <IconBtn
                          onClick={() => move(idx, 1)}
                          disabled={idx === tabs.length - 1}
                          title="Move down"
                        >
                          <ArrowDown size={13} />
                        </IconBtn>
                      </div>
                    </td>

                    {/* Label */}
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{tab.label}</span>
                        {tab.custom && (
                          <span className="text-xs text-slate-500 border border-slate-600 rounded px-1 py-0.5 shrink-0">
                            custom
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Data type */}
                    <td className="px-3 py-2 hidden sm:table-cell">
                      <DataTypeBadge value={tab.data_type} />
                    </td>

                    {/* Enabled */}
                    <td className="px-3 py-2">
                      <Toggle checked={tab.enabled} onChange={() => handleToggle(idx)} />
                    </td>

                    {/* Actions */}
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-end gap-1">
                        <IconBtn
                          onClick={() => setEditingId(tab.id)}
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </IconBtn>
                        {tab.custom && (
                          <IconBtn
                            onClick={() => setConfirmDel(tab)}
                            title="Delete"
                            danger
                          >
                            <Trash2 size={14} />
                          </IconBtn>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-700 px-4 py-3 flex items-center justify-between">
          <p className="text-xs text-slate-500">{tabs.length} tab{tabs.length !== 1 ? 's' : ''}</p>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
          >
            <Plus size={14} /> Add Tab
          </button>
        </div>
      </div>

      {showAdd && (
        <AddReportTabModal
          onAdd={handleAdd}
          onClose={() => setShowAdd(false)}
        />
      )}

      {confirmDel && (
        <ConfirmModal
          title="Delete Report Tab"
          message={`Delete report tab "${confirmDel.label}"? This cannot be undone.`}
          confirmLabel="Delete"
          danger
          onConfirm={() => handleDelete(confirmDel)}
          onClose={() => setConfirmDel(null)}
        />
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════════════════════════

const PAGE_TABS = [
  { id: 'widgets',      label: 'Dashboard Widgets', icon: Settings2  },
  { id: 'report_tabs',  label: 'Report Tabs',        icon: BarChart2  },
]

export default function DashboardReportsManager() {
  const { isAdmin }   = useAuthStore()
  const { notify }    = usePortalStore()

  const [activeTab, setActiveTab]         = useState('widgets')
  const [widgets, setWidgetsState]        = useState(() => loadWidgets())
  const [reportTabs, setReportTabsState]  = useState(() => loadReportTabs())
  const [savedFlash, setSavedFlash]       = useState(false)
  const [confirmReset, setConfirmReset]   = useState(false)

  // ── persist + notify on any widgets change ───────────────────────────────
  const handleWidgetsChange = useCallback((next) => {
    const normalised = saveWidgets(next)
    setWidgetsState(normalised)
    triggerSaved()
  }, [])

  // ── persist + notify on any report tabs change ───────────────────────────
  const handleTabsChange = useCallback((next) => {
    const normalised = saveReportTabs(next)
    setReportTabsState(normalised)
    triggerSaved()
  }, [])

  function triggerSaved() {
    notify('Changes saved', 'success')
    setSavedFlash(true)
    setTimeout(() => setSavedFlash(false), 2000)
  }

  function handleReset() {
    const w = saveWidgets([...DEFAULT_WIDGETS])
    const t = saveReportTabs([...DEFAULT_REPORT_TABS])
    setWidgetsState(w)
    setReportTabsState(t)
    setConfirmReset(false)
    notify('Reset to defaults', 'success')
  }

  // Guard: non-admins see an access-denied message
  if (!isAdmin()) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-5 max-w-lg">
          <AlertCircle size={20} className="shrink-0" />
          <div>
            <p className="font-semibold">Access Denied</p>
            <p className="text-sm mt-0.5 text-red-300/80">
              You need admin permissions to manage dashboard and report configuration.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">

      {/* ── Page header ── */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Dashboard &amp; Reports Config</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Configure which widgets appear on the dashboard and which report tabs are visible.
            Changes are saved immediately to local storage.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Save flash indicator */}
          {savedFlash && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/25 rounded-lg px-3 py-1.5 transition-opacity">
              <Check size={12} /> Saved
            </span>
          )}

          {/* Reset to defaults */}
          <button
            onClick={() => setConfirmReset(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500 text-sm transition-colors"
          >
            <RotateCcw size={14} />
            Reset Defaults
          </button>
        </div>
      </div>

      {/* ── Tab switcher (same pill style as Reports.jsx) ── */}
      <div className="flex gap-1 bg-slate-800/60 border border-slate-700 rounded-xl p-1 mb-5 overflow-x-auto max-w-sm">
        {PAGE_TABS.map(tab => {
          const Icon = tab.icon
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex-1 justify-center
                ${active
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

      {/* ── Active tab content ── */}
      {activeTab === 'widgets' && (
        <WidgetsTab
          widgets={widgets}
          onChange={handleWidgetsChange}
        />
      )}
      {activeTab === 'report_tabs' && (
        <ReportTabsTab
          tabs={reportTabs}
          onChange={handleTabsChange}
        />
      )}

      {/* ── Reset confirm dialog ── */}
      {confirmReset && (
        <ConfirmModal
          title="Reset to Defaults"
          message="This will discard all customisations — widget order, enabled states, custom widgets, and custom report tabs — and restore factory defaults. Continue?"
          confirmLabel="Reset"
          danger={false}
          onConfirm={handleReset}
          onClose={() => setConfirmReset(false)}
        />
      )}
    </div>
  )
}
