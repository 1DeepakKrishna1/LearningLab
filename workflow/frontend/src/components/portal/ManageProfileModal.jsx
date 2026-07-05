import { useState } from 'react'
import {
  X, User, ShieldCheck, Palette, Home, Bell,
  Check, Eye, EyeOff, Save, Lock, Mail, Tag,
} from 'lucide-react'
import useAuthStore from '../../store/authStore'
import usePortalStore, { NAV } from '../../store/portalStore'
import useStore from '../../store/workflowStore'
import { THEMES } from '../../themes'

const TABS = [
  { id: 'profile',       icon: User,        label: 'Profile Info' },
  { id: 'security',      icon: ShieldCheck, label: 'Login & Security' },
  { id: 'appearance',    icon: Palette,     label: 'Appearance' },
  { id: 'landing',       icon: Home,        label: 'Landing Page' },
  { id: 'notifications', icon: Bell,        label: 'Notifications' },
]

const ROLE_BADGE = {
  product_admin: { label: 'Product Admin', cls: 'bg-purple-500/20 text-purple-300 border border-purple-500/30' },
  process_admin: { label: 'Process Admin', cls: 'bg-blue-500/20 text-blue-300 border border-blue-500/30' },
  org_user:      { label: 'Org User',      cls: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' },
}

const LANDING_OPTIONS = [
  { group: 'Insights', items: [
    { value: NAV.INSIGHTS_DASHBOARD, label: 'Dashboard' },
    { value: NAV.INSIGHTS_REPORTS,   label: 'Reports' },
    { value: NAV.INSIGHTS_AUDIT,     label: 'Audit Logs' },
  ]},
  { group: 'Process', items: [
    { value: NAV.PROCESS,       label: 'Workflows' },
    { value: NAV.PROCESS_RUNS,  label: 'Runs' },
    { value: NAV.PROCESS_PROJECTS, label: 'Customers' },
  ]},
  { group: 'Manage', items: [
    { value: NAV.MANAGE_TOOLS,      label: 'Tools' },
    { value: NAV.MANAGE_AGENTS,     label: 'Agents' },
    { value: NAV.MANAGE_TEMPLATES,  label: 'Templates' },
    { value: NAV.MANAGE_REVIEWS,    label: 'Reviews' },
  ]},
]

const FONT_SIZES = [
  { id: 'small',  label: 'Small',  desc: '13 px' },
  { id: 'medium', label: 'Medium', desc: '15 px' },
  { id: 'large',  label: 'Large',  desc: '17 px' },
]

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()
}

function pwStrength(pw) {
  if (!pw) return 0
  let s = 0
  if (pw.length >= 8)          s++
  if (/[A-Z]/.test(pw))        s++
  if (/[0-9]/.test(pw))        s++
  if (/[^A-Za-z0-9]/.test(pw)) s++
  return s
}

function StatusMsg({ msg }) {
  if (!msg) return null
  return (
    <p className={`text-xs mt-2 ${msg.type === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
      {msg.text}
    </p>
  )
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors shrink-0 ${
        checked ? 'bg-indigo-600' : 'bg-slate-600'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

export default function ManageProfileModal({ onClose }) {
  const { user, updateProfile, updatePassword } = useAuthStore()
  const {
    defaultLandingPage, setDefaultLandingPage,
    fontSize, setFontSize,
    notifPrefs, setNotifPrefs,
  } = usePortalStore()
  const { theme, setTheme } = useStore()

  const [activeTab, setActiveTab] = useState('profile')

  // ── Profile tab state ─────────────────────────────────────────
  const [name, setName]               = useState(user?.name || '')
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileMsg, setProfileMsg]   = useState(null)

  // ── Security tab state ────────────────────────────────────────
  const [newPw, setNewPw]           = useState('')
  const [confirmPw, setConfirmPw]   = useState('')
  const [showNew, setShowNew]       = useState(false)
  const [showConf, setShowConf]     = useState(false)
  const [pwSaving, setPwSaving]     = useState(false)
  const [pwMsg, setPwMsg]           = useState(null)

  const badge = ROLE_BADGE[user?.role] ?? {
    label: user?.role ?? 'Unknown',
    cls: 'bg-slate-700 text-slate-300 border border-slate-600',
  }

  // ── Handlers ──────────────────────────────────────────────────
  async function handleSaveProfile() {
    if (!name.trim()) return
    setProfileSaving(true)
    setProfileMsg(null)
    const ok = await updateProfile(name.trim())
    setProfileSaving(false)
    setProfileMsg(ok
      ? { type: 'success', text: 'Profile updated successfully.' }
      : { type: 'error',   text: 'Failed to update profile. Try again.' })
    setTimeout(() => setProfileMsg(null), 3000)
  }

  async function handleChangePassword() {
    if (!newPw) { setPwMsg({ type: 'error', text: 'Enter a new password.' }); return }
    if (newPw !== confirmPw) { setPwMsg({ type: 'error', text: 'Passwords do not match.' }); return }
    if (newPw.length < 6)   { setPwMsg({ type: 'error', text: 'Password must be at least 6 characters.' }); return }
    setPwSaving(true)
    setPwMsg(null)
    const ok = await updatePassword(newPw)
    setPwSaving(false)
    if (ok) {
      setNewPw('')
      setConfirmPw('')
      setPwMsg({ type: 'success', text: 'Password changed successfully.' })
    } else {
      setPwMsg({ type: 'error', text: 'Failed to change password. Try again.' })
    }
    setTimeout(() => setPwMsg(null), 3000)
  }

  const strength    = pwStrength(newPw)
  const strLabel    = ['', 'Weak', 'Fair', 'Good', 'Strong'][strength]
  const strColor    = ['', 'bg-red-500', 'bg-yellow-500', 'bg-blue-500', 'bg-emerald-500'][strength]

  // ── All landing page options flat ──────────────────────────────
  const allLandingOptions = LANDING_OPTIONS.flatMap(g => g.items)
  const selectedLandingLabel = allLandingOptions.find(o => o.value === defaultLandingPage)?.label ?? 'Dashboard'

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.72)' }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="relative w-full max-w-3xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex"
        style={{ height: 560 }}
      >
        {/* ── Left sidebar ──────────────────────────────────────── */}
        <div className="w-52 bg-slate-800/60 border-r border-slate-700/70 flex flex-col shrink-0">
          {/* Avatar + name */}
          <div className="px-4 pt-5 pb-4 border-b border-slate-700/60">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-bold text-white shrink-0">
                {getInitials(user?.name)}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-100 truncate">{user?.name ?? '—'}</p>
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${badge.cls}`}>
                  {badge.label}
                </span>
              </div>
            </div>
          </div>

          {/* Nav tabs */}
          <nav className="flex-1 py-2 space-y-0.5 px-2">
            {TABS.map((tab) => {
              const Icon   = tab.icon
              const active = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left ${
                    active
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/40'
                  }`}
                >
                  <Icon size={14} />
                  {tab.label}
                </button>
              )
            })}
          </nav>
        </div>

        {/* ── Right panel ───────────────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/60 shrink-0">
            <h2 className="text-base font-semibold text-slate-100">
              {TABS.find((t) => t.id === activeTab)?.label}
            </h2>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-700 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

            {/* ── Profile Info ───────────────────────────────────── */}
            {activeTab === 'profile' && (
              <div className="space-y-5">
                {/* Avatar */}
                <div className="flex items-center gap-4">
                  <div className="h-16 w-16 rounded-full bg-indigo-600 flex items-center justify-center text-xl font-bold text-white shrink-0">
                    {getInitials(name || user?.name)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">{name || user?.name}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{user?.email}</p>
                  </div>
                </div>

                {/* Display name */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    <User size={11} className="inline mr-1" />
                    Display Name
                  </label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                    placeholder="Your full name"
                  />
                </div>

                {/* Email (read-only) */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    <Mail size={11} className="inline mr-1" />
                    Email Address
                  </label>
                  <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/60 rounded-lg px-3 py-2">
                    <span className="flex-1 text-sm text-slate-400">{user?.email}</span>
                    <Lock size={12} className="text-slate-600 shrink-0" />
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1">Email address cannot be changed.</p>
                </div>

                {/* Role (read-only) */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    <Tag size={11} className="inline mr-1" />
                    Role
                  </label>
                  <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/60 rounded-lg px-3 py-2">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badge.cls}`}>
                      {badge.label}
                    </span>
                    <Lock size={12} className="text-slate-600 ml-auto shrink-0" />
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1">Role is assigned by an administrator.</p>
                </div>

                <div>
                  <button
                    onClick={handleSaveProfile}
                    disabled={profileSaving || !name.trim()}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
                  >
                    <Save size={13} />
                    {profileSaving ? 'Saving…' : 'Save Profile'}
                  </button>
                  <StatusMsg msg={profileMsg} />
                </div>
              </div>
            )}

            {/* ── Login & Security ───────────────────────────────── */}
            {activeTab === 'security' && (
              <div className="space-y-5">
                {/* Username / email */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    <Mail size={11} className="inline mr-1" />
                    Username (Email)
                  </label>
                  <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/60 rounded-lg px-3 py-2">
                    <span className="flex-1 text-sm text-slate-400">{user?.email}</span>
                    <Lock size={12} className="text-slate-600 shrink-0" />
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1">
                    Your email is used as your login username and cannot be changed here.
                  </p>
                </div>

                <hr className="border-slate-700/50" />

                <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide">Change Password</p>

                {/* New password */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">New Password</label>
                  <div className="relative">
                    <input
                      type={showNew ? 'text' : 'password'}
                      value={newPw}
                      onChange={(e) => setNewPw(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                      placeholder="Enter new password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNew((v) => !v)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showNew ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                  {/* Strength bar */}
                  {newPw && (
                    <div className="mt-2 space-y-1">
                      <div className="flex gap-1">
                        {[1,2,3,4].map((i) => (
                          <div
                            key={i}
                            className={`h-1 flex-1 rounded-full transition-colors ${
                              i <= strength ? strColor : 'bg-slate-700'
                            }`}
                          />
                        ))}
                      </div>
                      <p className="text-[11px] text-slate-500">{strLabel}</p>
                    </div>
                  )}
                </div>

                {/* Confirm password */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Confirm Password</label>
                  <div className="relative">
                    <input
                      type={showConf ? 'text' : 'password'}
                      value={confirmPw}
                      onChange={(e) => setConfirmPw(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                      placeholder="Confirm new password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConf((v) => !v)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showConf ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                  {confirmPw && newPw !== confirmPw && (
                    <p className="text-[11px] text-red-400 mt-1">Passwords do not match.</p>
                  )}
                  {confirmPw && newPw === confirmPw && newPw && (
                    <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
                      <Check size={10} /> Passwords match.
                    </p>
                  )}
                </div>

                <div>
                  <button
                    onClick={handleChangePassword}
                    disabled={pwSaving || !newPw || !confirmPw}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
                  >
                    <ShieldCheck size={13} />
                    {pwSaving ? 'Saving…' : 'Update Password'}
                  </button>
                  <StatusMsg msg={pwMsg} />
                </div>
              </div>
            )}

            {/* ── Appearance ─────────────────────────────────────── */}
            {activeTab === 'appearance' && (
              <div className="space-y-6">
                {/* Theme */}
                <div>
                  <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-3">UI Theme</p>
                  <div className="grid grid-cols-3 gap-2">
                    {THEMES.map((t) => {
                      const active = theme === t.id
                      return (
                        <button
                          key={t.id}
                          onClick={() => setTheme(t.id)}
                          className={`relative flex flex-col items-start p-3 rounded-xl border transition-all text-left ${
                            active
                              ? 'border-2 scale-[1.02]'
                              : 'border-slate-700/60 hover:border-slate-500 hover:scale-[1.01]'
                          }`}
                          style={{
                            backgroundColor: t.swatches[0],
                            borderColor: active ? t.swatches[2] : undefined,
                          }}
                        >
                          <div className="flex gap-1 mb-2">
                            {t.swatches.map((s, i) => (
                              <div
                                key={i}
                                className="rounded-full border border-white/10"
                                style={{
                                  width: i === 2 ? 13 : 9,
                                  height: i === 2 ? 13 : 9,
                                  backgroundColor: s,
                                }}
                              />
                            ))}
                          </div>
                          <span
                            className="text-[11px] font-semibold"
                            style={{ color: t.id === 'light' ? '#0f172a' : '#e2e8f0' }}
                          >
                            {t.name}
                          </span>
                          <span
                            className="text-[9px] mt-0.5"
                            style={{ color: t.id === 'light' ? '#64748b' : '#94a3b8' }}
                          >
                            {t.description}
                          </span>
                          {active && (
                            <span
                              className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full flex items-center justify-center"
                              style={{ backgroundColor: t.swatches[2] }}
                            >
                              <Check size={8} className="text-white" />
                            </span>
                          )}
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Font size */}
                <div>
                  <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-3">Font Size</p>
                  <div className="flex gap-2">
                    {FONT_SIZES.map((fs) => {
                      const active = fontSize === fs.id
                      return (
                        <button
                          key={fs.id}
                          onClick={() => setFontSize(fs.id)}
                          className={`flex-1 flex flex-col items-center py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                            active
                              ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-300'
                              : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                          }`}
                        >
                          <span className={`font-semibold leading-none mb-1 ${
                            fs.id === 'small' ? 'text-xs' : fs.id === 'medium' ? 'text-sm' : 'text-base'
                          }`}>Aa</span>
                          <span className="text-[11px]">{fs.label}</span>
                          <span className="text-[10px] text-slate-600 mt-0.5">{fs.desc}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Accessibility */}
                <div>
                  <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-3">Accessibility</p>
                  <div className="space-y-3">
                    {[
                      { key: 'reduceMotion', label: 'Reduce Motion', desc: 'Minimise animations and transitions' },
                      { key: 'highContrast', label: 'High Contrast Text', desc: 'Increase text contrast for readability' },
                    ].map(({ key, label, desc }) => (
                      <div key={key} className="flex items-center justify-between py-2 border-b border-slate-700/40 last:border-0">
                        <div>
                          <p className="text-sm text-slate-200">{label}</p>
                          <p className="text-[11px] text-slate-500">{desc}</p>
                        </div>
                        <Toggle
                          checked={!!notifPrefs[key]}
                          onChange={(val) => setNotifPrefs({ ...notifPrefs, [key]: val })}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ── Landing Page ───────────────────────────────────── */}
            {activeTab === 'landing' && (
              <div className="space-y-4">
                <p className="text-sm text-slate-400">
                  Choose which page opens when you log in to the platform.
                </p>
                <p className="text-xs text-slate-500">
                  Current default: <span className="text-indigo-400 font-medium">{selectedLandingLabel}</span>
                </p>

                {LANDING_OPTIONS.map(({ group, items }) => (
                  <div key={group}>
                    <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">{group}</p>
                    <div className="space-y-1">
                      {items.map((opt) => {
                        const active = defaultLandingPage === opt.value
                        return (
                          <button
                            key={opt.value}
                            onClick={() => setDefaultLandingPage(opt.value)}
                            className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg border text-sm text-left transition-colors ${
                              active
                                ? 'bg-indigo-600/15 border-indigo-500/40 text-indigo-300'
                                : 'bg-slate-800/40 border-slate-700/50 text-slate-300 hover:border-slate-600 hover:bg-slate-800'
                            }`}
                          >
                            {opt.label}
                            {active && <Check size={13} className="text-indigo-400 shrink-0" />}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── Notifications ──────────────────────────────────── */}
            {activeTab === 'notifications' && (
              <div className="space-y-2">
                <p className="text-sm text-slate-400 mb-4">
                  Control which notifications you receive from the platform.
                </p>

                {/* Email */}
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mt-2 mb-2">Email Notifications</p>
                {[
                  { key: 'emailAlerts',        label: 'Security Alerts',        desc: 'Login from a new device or unusual activity' },
                  { key: 'emailWorkflow',       label: 'Workflow Completions',   desc: 'Notify when a workflow run finishes' },
                  { key: 'emailReview',         label: 'Review Requests',        desc: 'Notify when a tool or agent needs your review' },
                  { key: 'emailDigest',         label: 'Weekly Digest',          desc: 'Summary of activity sent every Monday' },
                ].map(({ key, label, desc }) => (
                  <div key={key} className="flex items-center justify-between py-2.5 border-b border-slate-700/40 last:border-0">
                    <div>
                      <p className="text-sm text-slate-200">{label}</p>
                      <p className="text-[11px] text-slate-500">{desc}</p>
                    </div>
                    <Toggle
                      checked={notifPrefs[key] !== false}
                      onChange={(val) => setNotifPrefs({ ...notifPrefs, [key]: val })}
                    />
                  </div>
                ))}

                {/* In-app */}
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mt-4 mb-2">In-App Notifications</p>
                {[
                  { key: 'inAppWorkflow', label: 'Workflow Events',  desc: 'Show notifications for run starts, failures, completions' },
                  { key: 'inAppReview',   label: 'Review Updates',   desc: 'Show when approvals or rejections occur' },
                  { key: 'inAppSystem',   label: 'System Messages',  desc: 'Platform updates and announcements' },
                ].map(({ key, label, desc }) => (
                  <div key={key} className="flex items-center justify-between py-2.5 border-b border-slate-700/40 last:border-0">
                    <div>
                      <p className="text-sm text-slate-200">{label}</p>
                      <p className="text-[11px] text-slate-500">{desc}</p>
                    </div>
                    <Toggle
                      checked={notifPrefs[key] !== false}
                      onChange={(val) => setNotifPrefs({ ...notifPrefs, [key]: val })}
                    />
                  </div>
                ))}

                <p className="text-[11px] text-slate-600 pt-2">
                  Notification preferences are saved automatically and persist across sessions.
                </p>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  )
}
