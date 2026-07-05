import { useState, useEffect } from 'react'
import { getReviews, approveReview, rejectReview } from '../../api/api'
import {
  ClipboardCheck, CheckCircle, XCircle, Clock, X, Loader2,
  AlertCircle, Search, ChevronDown, Filter
} from 'lucide-react'

const STATUS_COLORS = {
  pending: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  approved: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  rejected: 'bg-red-500/20 text-red-400 border border-red-500/30',
}

const TYPE_COLORS = {
  tool: 'bg-blue-500/20 text-blue-400',
  agent: 'bg-purple-500/20 text-purple-400',
  template: 'bg-indigo-500/20 text-indigo-400',
  workflow: 'bg-cyan-500/20 text-cyan-400',
}

const STATUS_ICONS = {
  pending: Clock,
  approved: CheckCircle,
  rejected: XCircle,
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-md shadow-2xl">
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

function ReviewActionModal({ review, action, onConfirm, onClose, saving }) {
  const [notes, setNotes] = useState('')
  const isApprove = action === 'approve'

  return (
    <Modal title={isApprove ? 'Approve Review' : 'Reject Review'} onClose={onClose}>
      <p className="text-slate-300 text-sm mb-3">
        {isApprove
          ? `Approve "${review.item_name}"?`
          : `Reject "${review.item_name}"?`
        }
      </p>
      <div className="mb-4">
        <label className="block text-xs font-medium text-slate-400 mb-1">
          Notes {!isApprove && <span className="text-red-400">*</span>}
        </label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          required={!isApprove}
          rows={3}
          className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
          placeholder={isApprove ? 'Optional notes…' : 'Provide a reason for rejection…'}
        />
      </div>
      <div className="flex gap-3 justify-end">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Cancel
        </button>
        <button
          onClick={() => onConfirm(notes)}
          disabled={saving || (!isApprove && !notes.trim())}
          className={`px-4 py-2 text-sm text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 ${
            isApprove
              ? 'bg-emerald-600 hover:bg-emerald-500'
              : 'bg-red-600 hover:bg-red-500'
          }`}
        >
          {saving && <Loader2 size={14} className="animate-spin" />}
          {isApprove ? 'Approve' : 'Reject'}
        </button>
      </div>
    </Modal>
  )
}

export default function ReviewsManager() {
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [modalState, setModalState] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadReviews() }, [])

  async function loadReviews() {
    try {
      setLoading(true)
      const data = await getReviews()
      setReviews(data)
    } catch {
      setError('Failed to load reviews.')
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(notes) {
    try {
      setSaving(true)
      if (modalState.action === 'approve') {
        await approveReview(modalState.review.id, notes)
      } else {
        await rejectReview(modalState.review.id, notes)
      }
      setModalState(null)
      loadReviews()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  // Counts
  const counts = {
    pending: reviews.filter(r => r.status === 'pending').length,
    approved: reviews.filter(r => r.status === 'approved').length,
    rejected: reviews.filter(r => r.status === 'rejected').length,
  }

  const STATUS_TABS = ['all', 'pending', 'approved', 'rejected']
  const TYPE_OPTIONS = ['all', 'tool', 'agent', 'template', 'workflow']

  const filtered = reviews.filter(r => {
    const matchSearch = !search ||
      r.item_name?.toLowerCase().includes(search.toLowerCase()) ||
      r.submitted_by_name?.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || r.status === statusFilter
    const matchType = typeFilter === 'all' || r.type === typeFilter
    return matchSearch && matchStatus && matchType
  })

  function formatDate(dt) {
    if (!dt) return '—'
    return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Review Queue</h1>
          <p className="text-slate-400 text-sm mt-1">Approve or reject submitted tools, agents, and templates.</p>
        </div>
        {/* Summary Badges */}
        <div className="flex gap-2 flex-wrap">
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
            <Clock size={14} className="text-amber-400" />
            <span className="text-amber-400 text-sm font-semibold">{counts.pending}</span>
            <span className="text-amber-400/70 text-xs">Pending</span>
          </div>
          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">
            <CheckCircle size={14} className="text-emerald-400" />
            <span className="text-emerald-400 text-sm font-semibold">{counts.approved}</span>
            <span className="text-emerald-400/70 text-xs">Approved</span>
          </div>
          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
            <XCircle size={14} className="text-red-400" />
            <span className="text-red-400 text-sm font-semibold">{counts.rejected}</span>
            <span className="text-red-400/70 text-xs">Rejected</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search reviews…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        {/* Status tabs */}
        <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded-lg p-1">
          {STATUS_TABS.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors flex items-center gap-1.5 ${
                statusFilter === s ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {s === 'all' ? 'All' : s}
              {s !== 'all' && counts[s] > 0 && (
                <span className={`rounded-full px-1.5 py-0 text-[10px] ${
                  s === 'pending' ? 'bg-amber-500/30 text-amber-300'
                  : s === 'approved' ? 'bg-emerald-500/30 text-emerald-300'
                  : 'bg-red-500/30 text-red-300'
                }`}>{counts[s]}</span>
              )}
            </button>
          ))}
        </div>
        {/* Type filter */}
        <div className="relative">
          <Filter size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-8 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 appearance-none"
          >
            {TYPE_OPTIONS.map(t => (
              <option key={t} value={t}>{t === 'all' ? 'All Types' : t.charAt(0).toUpperCase() + t.slice(1) + 's'}</option>
            ))}
          </select>
          <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading reviews…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10"><AlertCircle size={18} /> {error}</div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Item Name</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Type</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Status</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden lg:table-cell">Submitted By</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden lg:table-cell">Submitted</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden xl:table-cell">Reviewed By</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden xl:table-cell">Reviewed</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center text-slate-500 py-10">
                    <ClipboardCheck size={32} className="mx-auto mb-2 opacity-30" />
                    No reviews found.
                  </td>
                </tr>
              ) : (
                filtered.map(review => {
                  const StatusIcon = STATUS_ICONS[review.status] || Clock
                  return (
                    <tr key={review.id} className="hover:bg-slate-700/50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-medium text-white">{review.item_name}</p>
                        {review.notes && (
                          <p className="text-xs text-slate-500 mt-0.5 truncate max-w-[180px]" title={review.notes}>
                            {review.notes}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${TYPE_COLORS[review.type] || 'bg-slate-700 text-slate-300'}`}>
                          {review.type || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[review.status] || STATUS_COLORS.pending}`}>
                          <StatusIcon size={10} />
                          {review.status || 'pending'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs hidden lg:table-cell">
                        {review.submitted_by_name || '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs hidden lg:table-cell">
                        {formatDate(review.submitted_at)}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs hidden xl:table-cell">
                        {review.reviewed_by_name || '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs hidden xl:table-cell">
                        {formatDate(review.reviewed_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          {review.status === 'pending' ? (
                            <>
                              <button
                                onClick={() => setModalState({ review, action: 'approve' })}
                                className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors"
                                title="Approve"
                              >
                                <CheckCircle size={12} /> Approve
                              </button>
                              <button
                                onClick={() => setModalState({ review, action: 'reject' })}
                                className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors"
                                title="Reject"
                              >
                                <XCircle size={12} /> Reject
                              </button>
                            </>
                          ) : (
                            <span className="text-xs text-slate-500 italic">
                              {review.status === 'approved' ? 'Approved' : 'Rejected'}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Action Modal */}
      {modalState && (
        <ReviewActionModal
          review={modalState.review}
          action={modalState.action}
          onConfirm={handleAction}
          onClose={() => setModalState(null)}
          saving={saving}
        />
      )}
    </div>
  )
}
