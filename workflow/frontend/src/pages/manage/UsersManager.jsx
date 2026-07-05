import { useState, useEffect } from 'react'
import {
  getUsers, createUser, updateUser, deleteUser, toggleUserStatus,
  getProjects
} from '../../api/api'
import {
  Users, Plus, Pencil, Trash2, X, Loader2, AlertCircle, Search, ChevronDown,
  UserCheck, UserX
} from 'lucide-react'

const ROLE_COLORS = {
  product_admin: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
  process_admin: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  org_user: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
}

const ROLE_LABELS = {
  product_admin: 'Product Admin',
  process_admin: 'Process Admin',
  org_user: 'Org User',
}

const ROLES = ['product_admin', 'process_admin', 'org_user']

function Modal({ title, onClose, children, size = 'max-w-lg' }) {
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

function UserForm({ initial, onSave, onClose, saving, projects }) {
  const [form, setForm] = useState({
    name: initial?.name || '',
    email: initial?.email || '',
    password: '',
    role: initial?.role || 'org_user',
    project_ids: initial?.project_ids || [],
  })

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  function toggleProject(pid) {
    set('project_ids', form.project_ids.includes(pid)
      ? form.project_ids.filter(p => p !== pid)
      : [...form.project_ids, pid])
  }

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
            placeholder="Full name"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Email <span className="text-red-400">*</span></label>
          <input
            required
            type="email"
            value={form.email}
            onChange={e => set('email', e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            placeholder="user@example.com"
          />
        </div>
        {!initial && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Password <span className="text-red-400">*</span></label>
            <input
              required={!initial}
              type="password"
              value={form.password}
              onChange={e => set('password', e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              placeholder="••••••••"
            />
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Role</label>
          <div className="relative">
            <select
              value={form.role}
              onChange={e => set('role', e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 appearance-none"
            >
              {ROLES.map(r => (
                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          </div>
        </div>
        {projects.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Customers</label>
            <div className="bg-slate-900 border border-slate-600 rounded-lg p-2 max-h-40 overflow-y-auto space-y-1">
              {projects.map(p => (
                <label key={p.id} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.project_ids.includes(p.id)}
                    onChange={() => toggleProject(p.id)}
                    className="accent-indigo-500"
                  />
                  <span className="text-sm text-slate-300">{p.name}</span>
                </label>
              ))}
            </div>
          </div>
        )}
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
          {initial ? 'Save Changes' : 'Create User'}
        </button>
      </div>
    </form>
  )
}

function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`relative w-10 h-5 rounded-full transition-colors ${checked ? 'bg-emerald-500' : 'bg-slate-600'} disabled:opacity-50`}
    >
      <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? 'left-5' : 'left-0.5'}`} />
    </button>
  )
}

export default function UsersManager() {
  const [users, setUsers] = useState([])
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [modalState, setModalState] = useState(null)
  const [saving, setSaving] = useState(false)
  const [togglingId, setTogglingId] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      setLoading(true)
      const [u, p] = await Promise.all([getUsers(), getProjects()])
      setUsers(u)
      setProjects(p)
    } catch {
      setError('Failed to load users.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(form) {
    try {
      setSaving(true)
      if (modalState.type === 'add') {
        await createUser(form)
      } else {
        const { password, ...data } = form
        await updateUser(modalState.user.id, data)
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
      await deleteUser(modalState.user.id)
      setModalState(null)
      loadData()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  async function handleToggle(user) {
    try {
      setTogglingId(user.id)
      await toggleUserStatus(user.id, !user.is_active)
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, is_active: !u.is_active } : u))
    } catch {
      /* silently ignore */
    } finally {
      setTogglingId(null)
    }
  }

  const filtered = users.filter(u => {
    const matchSearch = !search ||
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
    const matchRole = roleFilter === 'all' || u.role === roleFilter
    const matchStatus = statusFilter === 'all' ||
      (statusFilter === 'active' ? u.is_active : !u.is_active)
    return matchSearch && matchRole && matchStatus
  })

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Users</h1>
          <p className="text-slate-400 text-sm mt-1">Manage platform users, roles, and access.</p>
        </div>
        <button
          onClick={() => setModalState({ type: 'add' })}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus size={16} /> Add User
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search users…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="relative">
          <select
            value={roleFilter}
            onChange={e => setRoleFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 appearance-none pr-8"
          >
            <option value="all">All Roles</option>
            <option value="product_admin">Product Admin</option>
            <option value="process_admin">Process Admin</option>
            <option value="org_user">Org User</option>
          </select>
          <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>
        <div className="relative">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 appearance-none pr-8"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading users…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10"><AlertCircle size={18} /> {error}</div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Email</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Role</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Groups</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Customers</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Status</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-slate-500 py-10">
                    <Users size={32} className="mx-auto mb-2 opacity-30" />
                    No users found.
                  </td>
                </tr>
              ) : (
                filtered.map(user => (
                  <tr key={user.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-white">{user.name}</td>
                    <td className="px-4 py-3 text-slate-400">{user.email}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[user.role] || 'bg-slate-700 text-slate-300'}`}>
                        {ROLE_LABELS[user.role] || user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs hidden md:table-cell">
                      {(user.group_ids || []).length}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs hidden md:table-cell">
                      {(user.project_ids || []).length}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Toggle
                          checked={user.is_active}
                          onChange={() => handleToggle(user)}
                          disabled={togglingId === user.id}
                        />
                        <span className="text-xs text-slate-400">
                          {user.is_active
                            ? <span className="flex items-center gap-1 text-emerald-400"><UserCheck size={12} /> Active</span>
                            : <span className="flex items-center gap-1 text-slate-500"><UserX size={12} /> Inactive</span>
                          }
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setModalState({ type: 'edit', user })}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'delete', user })}
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
        <Modal title="Add User" onClose={() => setModalState(null)}>
          <UserForm onSave={handleSave} onClose={() => setModalState(null)} saving={saving} projects={projects} />
        </Modal>
      )}
      {modalState?.type === 'edit' && (
        <Modal title="Edit User" onClose={() => setModalState(null)}>
          <UserForm
            initial={modalState.user}
            onSave={handleSave}
            onClose={() => setModalState(null)}
            saving={saving}
            projects={projects}
          />
        </Modal>
      )}
      {modalState?.type === 'delete' && (
        <Modal title="Delete User" onClose={() => setModalState(null)}>
          <p className="text-slate-300 text-sm mb-4">
            Are you sure you want to delete <span className="text-white font-medium">"{modalState.user.name}"</span>? This action cannot be undone.
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
