import { useState, useRef, useEffect } from 'react'
import { Menu, Zap, ChevronDown, LogOut, User, Settings } from 'lucide-react'
import useAuthStore from '../../store/authStore'
import usePortalStore from '../../store/portalStore'
import ThemeSwitcher from '../ThemeSwitcher'
import ManageProfileModal from './ManageProfileModal'
import { isVisible } from '../../config/pageConfig'

const ROLE_BADGE = {
  product_admin: { label: 'Product Admin', cls: 'bg-purple-500/20 text-purple-300 border border-purple-500/30' },
  process_admin: { label: 'Process Admin', cls: 'bg-blue-500/20 text-blue-300 border border-blue-500/30' },
  org_user:      { label: 'Org User',      cls: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' },
  cust_user:     { label: 'Customer User',  cls: 'bg-teal-500/20 text-teal-300 border border-teal-500/30' },
  cust_admin:    { label: 'Customer Admin', cls: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' },
}

function getInitials(name) {
  if (!name) return '?'
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export default function TopBar() {
  const { user, logout } = useAuthStore()
  const { toggleSidebar, launchStudio, org } = usePortalStore()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [profileOpen, setProfileOpen]   = useState(false)
  const dropdownRef = useRef(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    if (dropdownOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [dropdownOpen])

  const badge = ROLE_BADGE[user?.role] ?? {
    label: user?.role ?? 'Unknown',
    cls: 'bg-slate-700 text-slate-300 border border-slate-600',
  }

  async function handleLogout() {
    setDropdownOpen(false)
    await logout()
  }

  function openProfile() {
    setDropdownOpen(false)
    setProfileOpen(true)
  }

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 h-14 flex items-center px-4 bg-slate-900 border-b border-slate-800">
        {/* Left: hamburger + logo */}
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            aria-label="Toggle sidebar"
          >
            <Menu size={18} />
          </button>

          <div className="flex items-center gap-2">
            {org.hasLogo && org.logoUrl && (
              <img
                src={org.logoUrl}
                alt={`${org.name} logo`}
                className="h-7 w-7 object-contain"
                onError={(e) => { e.target.style.display = 'none' }}
              />
            )}
            <span className="text-base font-bold text-slate-100 tracking-tight select-none">
              {org.name}
            </span>
          </div>
        </div>

        {/* Center: subtitle */}
        <div className="flex-1 flex justify-center">
          <span className="text-xs font-medium text-slate-500 tracking-widest uppercase hidden sm:block select-none">
            Workflow Platform
          </span>
        </div>

        {/* Right: Theme switcher + Launch Studio + user menu */}
        <div className="flex items-center gap-3">
          <ThemeSwitcher />

          {isVisible(user?.role, 'topBar', 'launchStudio') && (
            <button
              onClick={launchStudio}
              className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-1.5 rounded-md transition-colors"
            >
              <Zap size={13} />
              <span className="hidden sm:inline">Launch Studio</span>
              <span className="sm:hidden">Studio</span>
            </button>
          )}

          {/* User avatar + dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen((v) => !v)}
              className="flex items-center gap-1.5 group"
              aria-expanded={dropdownOpen}
              aria-haspopup="true"
            >
              <div className="h-8 w-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white select-none">
                {getInitials(user?.name)}
              </div>
              <ChevronDown
                size={13}
                className={`text-slate-400 group-hover:text-slate-200 transition-transform duration-150 ${dropdownOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {/* Dropdown panel */}
            {dropdownOpen && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50">
                {/* User info */}
                <div className="px-4 py-3 border-b border-slate-700/60">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
                      {getInitials(user?.name)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-100 truncate">{user?.name ?? '—'}</p>
                      <p className="text-xs text-slate-400 truncate">{user?.email ?? '—'}</p>
                    </div>
                  </div>
                  <div className="mt-2.5">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${badge.cls}`}>
                      {badge.label}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="py-1">
                  <button
                    onClick={openProfile}
                    className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
                  >
                    <Settings size={14} />
                    Manage Profile
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <LogOut size={14} />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Profile modal */}
      {profileOpen && <ManageProfileModal onClose={() => setProfileOpen(false)} />}
    </>
  )
}
