import { create } from 'zustand'
import { getOrgConfig, BASE_URL } from '../api/api'

// Navigation sections and pages for the landing portal
export const NAV = {
  INSIGHTS_DASHBOARD:      'insights/dashboard',
  INSIGHTS_REPORTS:        'insights/reports',
  INSIGHTS_AUDIT:          'insights/audit',
  OBSERVABILITY_LIVE:      'observability/live',
  OBSERVABILITY_INSIGHTS:  'observability/insights',
  PROCESS:                 'process/workflows',
  PROCESS_RUNS:            'process/runs',
  PROCESS_PROJECTS:        'process/projects',
  MANAGE_TOOLS:            'manage/tools',
  MANAGE_AGENTS:           'manage/agents',
  MANAGE_TEMPLATES:        'manage/templates',
  MANAGE_DATA_MODELS:      'manage/data-models',
  MANAGE_USERS:            'manage/users',
  MANAGE_GROUPS:           'manage/groups',
  MANAGE_PROJECTS:         'manage/projects',
  MANAGE_REVIEWS:          'manage/reviews',
  MANAGE_DASHBOARD_REPORTS:'manage/dashboard-reports',
}

// Apply persisted font size on module load
const _initFontSize = localStorage.getItem('wf-font-size') || 'medium'
document.documentElement.setAttribute('data-font-size', _initFontSize)

const _initNotifPrefs = (() => {
  try { return JSON.parse(localStorage.getItem('wf-notif-prefs') || 'null') || {} }
  catch { return {} }
})()

const usePortalStore = create((set) => ({
  // ── View & navigation ────────────────────────────────────────
  appView:      'login',   // 'login' | 'landing' | 'studio'
  currentPage:  NAV.INSIGHTS_DASHBOARD,
  sidebarCollapsed: false,
  notification: null,
  reportActiveTab: null,
  activeRunWorkflow: null, // { id, name } | null — set when launching a run from ProcessList

  // ── User preferences (persisted to localStorage) ─────────────
  defaultLandingPage: localStorage.getItem('wf-default-page') || NAV.INSIGHTS_DASHBOARD,
  fontSize: _initFontSize,
  notifPrefs: _initNotifPrefs,

  // ── Organization branding (loaded from backend) ─────────────
  org: { name: 'Incepta', domain: 'incepta.com', hasLogo: false, logoUrl: null },

  async loadOrgConfig() {
    try {
      const cfg = await getOrgConfig()
      const org = {
        name: cfg.org_name || 'Incepta',
        domain: cfg.org_domain || '',
        hasLogo: !!cfg.has_logo,
        logoUrl: cfg.has_logo && cfg.logo_url ? `${BASE_URL}${cfg.logo_url}` : null,
      }
      set({ org })
      // Reflect branding in the browser tab + favicon.
      document.title = `${org.name} – Workflow Management Platform`
      if (org.logoUrl) {
        let link = document.querySelector("link[rel='icon']")
        if (!link) {
          link = document.createElement('link')
          link.rel = 'icon'
          document.head.appendChild(link)
        }
        link.href = org.logoUrl
      }
    } catch (_) {
      // Backend unreachable — keep sensible defaults.
    }
  },

  // ── Actions ──────────────────────────────────────────────────
  setAppView:    (view) => set({ appView: view }),
  setCurrentPage:(page) => set({ currentPage: page }),
  setReportTab:  (tab)  => set({ reportActiveTab: tab }),
  toggleSidebar: ()     => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  setDefaultLandingPage(page) {
    localStorage.setItem('wf-default-page', page)
    set({ defaultLandingPage: page })
  },

  setFontSize(size) {
    localStorage.setItem('wf-font-size', size)
    document.documentElement.setAttribute('data-font-size', size)
    set({ fontSize: size })
  },

  setNotifPrefs(prefs) {
    localStorage.setItem('wf-notif-prefs', JSON.stringify(prefs))
    set({ notifPrefs: prefs })
  },

  notify(msg, type = 'success') {
    set({ notification: { msg, type, id: Date.now() } })
    setTimeout(() => set({ notification: null }), 3500)
  },

  navigateToRuns(workflow = null) {
    set({ currentPage: NAV.PROCESS_RUNS, activeRunWorkflow: workflow })
  },

  clearActiveRun() {
    set({ activeRunWorkflow: null })
  },

  launchStudio() {
    set({ appView: 'studio' })
  },

  returnToPortal() {
    set({ appView: 'landing' })
  },
}))

export default usePortalStore
