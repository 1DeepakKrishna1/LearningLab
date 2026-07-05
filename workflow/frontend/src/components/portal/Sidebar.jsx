import { BarChart2, Home, FileText, Shield, GitBranch, Play, History, Settings, Wrench, Bot, Layout, Database, Users, UserCheck, FolderOpen, CheckCircle, SlidersHorizontal, Activity, Radio, LineChart } from 'lucide-react'
import useAuthStore from '../../store/authStore'
import usePortalStore, { NAV } from '../../store/portalStore'
import { getSidebarConfig, VISIBILITY } from '../../config/sidebarConfig'

const { HIDE, DISABLE } = VISIBILITY

// ---------------------------------------------------------------------------
// Data definitions
// ---------------------------------------------------------------------------

const INSIGHTS_ITEMS = [
  { label: 'Dashboard',   icon: Home,        page: NAV.INSIGHTS_DASHBOARD },
  { label: 'Reports',     icon: FileText,    page: NAV.INSIGHTS_REPORTS },
  { label: 'Audit Logs',  icon: Shield,      page: NAV.INSIGHTS_AUDIT },
]

const OBSERVABILITY_ITEMS = [
  { label: 'Live Monitor',  icon: Radio,      page: NAV.OBSERVABILITY_LIVE },
  { label: 'Insights',      icon: LineChart,  page: NAV.OBSERVABILITY_INSIGHTS },
]

const PROCESS_ITEMS = [
  { label: 'Workflows', icon: Play,       page: NAV.PROCESS },
  { label: 'Runs',      icon: History,    page: NAV.PROCESS_RUNS },
  { label: 'Customers',  icon: FolderOpen, page: NAV.PROCESS_PROJECTS },
]

const LIBRARY_ITEMS = [
  { label: 'Tools',      icon: Wrench,       page: NAV.MANAGE_TOOLS },
  { label: 'Agents',     icon: Bot,          page: NAV.MANAGE_AGENTS },
  { label: 'Templates',  icon: Layout,       page: NAV.MANAGE_TEMPLATES },
  { label: 'Reviews',    icon: CheckCircle,  page: NAV.MANAGE_REVIEWS },
]

const DATA_ITEMS = [
  { label: 'Data Models', icon: Database, page: NAV.MANAGE_DATA_MODELS },
]

const IDENTITY_ITEMS = [
  { label: 'Users',    icon: Users,      page: NAV.MANAGE_USERS },
  { label: 'Groups',   icon: UserCheck,  page: NAV.MANAGE_GROUPS },
  { label: 'Customers', icon: FolderOpen, page: NAV.MANAGE_PROJECTS },
]

const CONFIG_ITEMS = [
  { label: 'Dashboard & Reports', icon: SlidersHorizontal, page: NAV.MANAGE_DASHBOARD_REPORTS },
]

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeader({ icon: Icon, label, collapsed, disabled }) {
  return (
    <div className={`flex items-center gap-2 px-3 pt-4 pb-1 ${disabled ? 'opacity-40' : ''}`}>
      <Icon size={13} className="text-slate-500 shrink-0" />
      {!collapsed && (
        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest truncate">
          {label}
        </span>
      )}
    </div>
  )
}

function SubGroupLabel({ label, collapsed, disabled }) {
  if (collapsed) return null
  return (
    <div className="px-3 pt-3 pb-0.5">
      <span className={`text-[9px] font-medium uppercase tracking-widest ${disabled ? 'text-slate-700' : 'text-slate-600'}`}>
        {label}
      </span>
    </div>
  )
}

function NavItem({ icon: Icon, label, page, currentPage, setCurrentPage, collapsed, disabled }) {
  const isActive = currentPage === page

  return (
    <div className="relative group px-2">
      <button
        onClick={disabled ? undefined : () => setCurrentPage(page)}
        disabled={disabled}
        className={[
          'w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm font-medium transition-colors',
          disabled
            ? 'text-slate-600 cursor-not-allowed opacity-50'
            : isActive
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100',
          collapsed ? 'justify-center' : '',
        ].join(' ')}
        aria-current={isActive && !disabled ? 'page' : undefined}
      >
        <Icon size={16} className="shrink-0" />
        {!collapsed && <span className="truncate">{label}</span>}
      </button>

      {/* Tooltip when collapsed */}
      {collapsed && (
        <div
          className="pointer-events-none absolute left-full top-1/2 -translate-y-1/2 ml-2 z-50
                     opacity-0 group-hover:opacity-100 transition-opacity duration-150"
        >
          <div className="bg-slate-700 text-slate-100 text-xs font-medium px-2.5 py-1.5 rounded-md shadow-lg whitespace-nowrap">
            {label}
            {disabled && <span className="ml-1 text-slate-400">(disabled)</span>}
            <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-700" />
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helper — filters hidden items, marks disabled ones (group-level overrides item-level)
// ---------------------------------------------------------------------------

function renderItems(items, itemCfg, itemProps, groupDisabled = false) {
  return items
    .filter(({ page }) => itemCfg[page] !== HIDE)
    .map(({ page, ...rest }) => (
      <NavItem
        key={page}
        page={page}
        {...rest}
        {...itemProps}
        disabled={groupDisabled || itemCfg[page] === DISABLE}
      />
    ))
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function Sidebar() {
  const { user } = useAuthStore()
  const { sidebarCollapsed, currentPage, setCurrentPage } = usePortalStore()
  const collapsed = sidebarCollapsed

  const cfg = getSidebarConfig(user?.role)
  const itemProps = { currentPage, setCurrentPage, collapsed }

  return (
    <aside
      className="fixed left-0 top-14 bottom-0 z-40 flex flex-col bg-slate-900 border-r border-slate-800 overflow-y-auto overflow-x-hidden"
      style={{
        width: collapsed ? '60px' : '240px',
        transition: 'width 0.2s ease',
      }}
    >
      {/* INSIGHTS */}
      {cfg.insights.section !== HIDE && (
        <div>
          <SectionHeader icon={BarChart2} label="Insights" collapsed={collapsed} disabled={cfg.insights.section === DISABLE} />
          {renderItems(INSIGHTS_ITEMS, cfg.insights.items, itemProps, cfg.insights.section === DISABLE)}
        </div>
      )}

      {/* OBSERVABILITY */}
      {cfg.observability && cfg.observability.section !== HIDE && (
        <div>
          <SectionHeader icon={Activity} label="Observability" collapsed={collapsed} disabled={cfg.observability.section === DISABLE} />
          {renderItems(OBSERVABILITY_ITEMS, cfg.observability.items, itemProps, cfg.observability.section === DISABLE)}
        </div>
      )}

      {/* PROCESS */}
      {cfg.process.section !== HIDE && (
        <div>
          <SectionHeader icon={GitBranch} label="Process" collapsed={collapsed} disabled={cfg.process.section === DISABLE} />
          {renderItems(PROCESS_ITEMS, cfg.process.items, itemProps, cfg.process.section === DISABLE)}
        </div>
      )}

      {/* MANAGE */}
      {cfg.manage.section !== HIDE && (
        <div>
          <SectionHeader icon={Settings} label="Manage" collapsed={collapsed} disabled={cfg.manage.section === DISABLE} />

          {cfg.manage.subgroups.library.group !== HIDE && (
            <>
              <SubGroupLabel label="Library" collapsed={collapsed} disabled={cfg.manage.subgroups.library.group === DISABLE} />
              {renderItems(LIBRARY_ITEMS, cfg.manage.subgroups.library.items, itemProps, cfg.manage.subgroups.library.group === DISABLE)}
            </>
          )}

          {cfg.manage.subgroups.data.group !== HIDE && (
            <>
              <SubGroupLabel label="Data" collapsed={collapsed} disabled={cfg.manage.subgroups.data.group === DISABLE} />
              {renderItems(DATA_ITEMS, cfg.manage.subgroups.data.items, itemProps, cfg.manage.subgroups.data.group === DISABLE)}
            </>
          )}

          {cfg.manage.subgroups.identity.group !== HIDE && (
            <>
              <SubGroupLabel label="Identity" collapsed={collapsed} disabled={cfg.manage.subgroups.identity.group === DISABLE} />
              {renderItems(IDENTITY_ITEMS, cfg.manage.subgroups.identity.items, itemProps, cfg.manage.subgroups.identity.group === DISABLE)}
            </>
          )}

          {cfg.manage.subgroups.config.group !== HIDE && (
            <>
              <SubGroupLabel label="Config" collapsed={collapsed} disabled={cfg.manage.subgroups.config.group === DISABLE} />
              {renderItems(CONFIG_ITEMS, cfg.manage.subgroups.config.items, itemProps, cfg.manage.subgroups.config.group === DISABLE)}
            </>
          )}
        </div>
      )}

      {/* Spacer at bottom */}
      <div className="flex-1 min-h-4" />
    </aside>
  )
}
