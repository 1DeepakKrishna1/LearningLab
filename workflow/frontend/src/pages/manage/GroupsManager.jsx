import { useState, useEffect } from 'react'
import {
  getGroups, createGroup, updateGroup, deleteGroup,
  addGroupMember, removeGroupMember, getUsers
} from '../../api/api'
import {
  Users, Plus, Pencil, Trash2, X, Loader2, AlertCircle, Search,
  UserPlus, UserMinus
} from 'lucide-react'

function Modal({ title, onClose, children, size = 'max-w-lg' }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className={`bg-slate-800 border border-slate-700 rounded-xl w-full ${size} shadow-2xl max-h-[90vh] flex flex-col`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 flex-shrink-0">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

function GroupForm({ initial, onSave, onClose, saving }) {
  const [form, setForm] = useState({
    name: initial?.name || '',
    description: initial?.description || '',
  })

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  return (
    <form onSubmit={e => { e.preventDefault(); onSave(form) }}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Name <span className="text-red-400">*</span></label>
          <input
            required
            value={form.name}
            onChange={e => set('name', e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            placeholder="Group name"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={e => set('description', e.target.value)}
            rows={3}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            placeholder="Describe this group's purpose…"
          />
        </div>
      </div>
      <div className="flex gap-3 justify-end mt-6">
        <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {saving && <Loader2 size={14} className="animate-spin" />}
          {initial ? 'Save Changes' : 'Create Group'}
        </button>
      </div>
    </form>
  )
}

function ManageMembersModal({ group, allUsers, onClose, onChanged }) {
  const [memberIds, setMemberIds] = useState(group.user_ids || [])
  const [search, setSearch] = useState('')
  const [actionId, setActionId] = useState(null)

  const members = allUsers.filter(u => memberIds.includes(u.id))
  const nonMembers = allUsers.filter(u =>
    !memberIds.includes(u.id) &&
    (!search || u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
  )

  async function removeMember(uid) {
    try {
      setActionId(uid)
      await removeGroupMember(group.id, uid)
      setMemberIds(prev => prev.filter(id => id !== uid))
      onChanged()
    } catch {
      /* silently ignore */
    } finally {
      setActionId(null)
    }
  }

  async function addMember(uid) {
    try {
      setActionId(uid)
      await addGroupMember(group.id, uid)
      setMemberIds(prev => [...prev, uid])
      onChanged()
    } catch {
      /* silently ignore */
    } finally {
      setActionId(null)
    }
  }

  return (
    <Modal title={`Manage Members — ${group.name}`} onClose={onClose} size="max-w-xl">
      {/* Current Members */}
      <div className="mb-4">
        <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
          Current Members ({members.length})
        </h3>
        {members.length === 0 ? (
          <p className="text-slate-500 text-sm py-2">No members in this group.</p>
        ) : (
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {members.map(u => (
              <div key={u.id} className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2">
                <div>
                  <p className="text-sm text-white font-medium">{u.name}</p>
                  <p className="text-xs text-slate-500">{u.email}</p>
                </div>
                <button
                  onClick={() => removeMember(u.id)}
                  disabled={actionId === u.id}
                  className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
                  title="Remove"
                >
                  {actionId === u.id ? <Loader2 size={14} className="animate-spin" /> : <UserMinus size={14} />}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Members */}
      <div>
        <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Add Members</h3>
        <div className="relative mb-2">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search users to add…"
            className="w-full bg-slate-900 border border-slate-600 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {nonMembers.length === 0 ? (
            <p className="text-slate-500 text-sm py-2">No users to add.</p>
          ) : (
            nonMembers.map(u => (
              <div key={u.id} className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2">
                <div>
                  <p className="text-sm text-white font-medium">{u.name}</p>
                  <p className="text-xs text-slate-500">{u.email}</p>
                </div>
                <button
                  onClick={() => addMember(u.id)}
                  disabled={actionId === u.id}
                  className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded transition-colors disabled:opacity-50"
                  title="Add"
                >
                  {actionId === u.id ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} />}
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex justify-end mt-4">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Done
        </button>
      </div>
    </Modal>
  )
}

export default function GroupsManager() {
  const [groups, setGroups] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [modalState, setModalState] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      setLoading(true)
      const [g, u] = await Promise.all([getGroups(), getUsers()])
      setGroups(g)
      setAllUsers(u)
    } catch {
      setError('Failed to load groups.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(form) {
    try {
      setSaving(true)
      if (modalState.type === 'add') {
        await createGroup(form)
      } else {
        await updateGroup(modalState.group.id, form)
      }
      setModalState(null)
      loadData()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    try {
      setSaving(true)
      await deleteGroup(modalState.group.id)
      setModalState(null)
      loadData()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  const filtered = groups.filter(g =>
    !search ||
    g.name.toLowerCase().includes(search.toLowerCase()) ||
    (g.description || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Groups</h1>
          <p className="text-slate-400 text-sm mt-1">Organize users into groups for access control.</p>
        </div>
        <button
          onClick={() => setModalState({ type: 'add' })}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus size={16} /> Add Group
        </button>
      </div>

      {/* Search */}
      <div className="mb-5">
        <div className="relative max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search groups…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading groups…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10"><AlertCircle size={18} /> {error}</div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Description</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Members</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Status</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-slate-500 py-10">
                    <Users size={32} className="mx-auto mb-2 opacity-30" />
                    No groups found.
                  </td>
                </tr>
              ) : (
                filtered.map(group => (
                  <tr key={group.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-white">{group.name}</td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate hidden md:table-cell">{group.description || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-slate-300 text-xs">
                        <Users size={12} />
                        {(group.user_ids || []).length} members
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {group.is_active !== false
                        ? <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Active</span>
                        : <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-slate-500/20 text-slate-400 border border-slate-500/30">Inactive</span>
                      }
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setModalState({ type: 'members', group })}
                          className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition-colors"
                          title="Manage Members"
                        >
                          <UserPlus size={14} />
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'edit', group })}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'delete', group })}
                          className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      {modalState?.type === 'add' && (
        <Modal title="Add Group" onClose={() => setModalState(null)}>
          <GroupForm onSave={handleSave} onClose={() => setModalState(null)} saving={saving} />
        </Modal>
      )}
      {modalState?.type === 'edit' && (
        <Modal title="Edit Group" onClose={() => setModalState(null)}>
          <GroupForm
            initial={modalState.group}
            onSave={handleSave}
            onClose={() => setModalState(null)}
            saving={saving}
          />
        </Modal>
      )}
      {modalState?.type === 'members' && (
        <ManageMembersModal
          group={modalState.group}
          allUsers={allUsers}
          onClose={() => setModalState(null)}
          onChanged={loadData}
        />
      )}
      {modalState?.type === 'delete' && (
        <Modal title="Delete Group" onClose={() => setModalState(null)}>
          <p className="text-slate-300 text-sm mb-4">
            Are you sure you want to delete <span className="text-white font-medium">"{modalState.group.name}"</span>?
          </p>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setModalState(null)} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={saving}
              className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              Delete
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
