import React, { useEffect } from 'react'
import TopBar from '../components/portal/TopBar'
import Sidebar from '../components/portal/Sidebar'
import Notification from '../components/portal/Notification'
import usePortalStore, { NAV } from '../store/portalStore'

// Insights
import Dashboard from './insights/Dashboard'
import Reports from './insights/Reports'
import AuditLogs from './insights/AuditLogs'

// Observability
import LiveMonitor from './observability/LiveMonitor'
import ObservabilityDashboard from './observability/ObservabilityDashboard'

// Process
import ProcessList from './process/ProcessList'
import RunsPage from './process/RunsPage'
import ProjectsList from './process/ProjectsList'

// Manage
import ToolsManager from './manage/ToolsManager'
import AgentsManager from './manage/AgentsManager'
import TemplatesManager from './manage/TemplatesManager'
import DataModelsManager from './manage/DataModelsManager'
import UsersManager from './manage/UsersManager'
import GroupsManager from './manage/GroupsManager'
import ProjectsManager from './manage/ProjectsManager'
import ReviewsManager from './manage/ReviewsManager'
import DashboardReportsManager from './manage/DashboardReportsManager'

const PAGE_MAP = {
  [NAV.INSIGHTS_DASHBOARD]: Dashboard,
  [NAV.INSIGHTS_REPORTS]: Reports,
  [NAV.INSIGHTS_AUDIT]: AuditLogs,
  [NAV.OBSERVABILITY_LIVE]: LiveMonitor,
  [NAV.OBSERVABILITY_INSIGHTS]: ObservabilityDashboard,
  [NAV.PROCESS]: ProcessList,
  [NAV.PROCESS_RUNS]: RunsPage,
  [NAV.PROCESS_PROJECTS]: ProjectsList,
  [NAV.MANAGE_TOOLS]: ToolsManager,
  [NAV.MANAGE_AGENTS]: AgentsManager,
  [NAV.MANAGE_TEMPLATES]: TemplatesManager,
  [NAV.MANAGE_DATA_MODELS]: DataModelsManager,
  [NAV.MANAGE_USERS]: UsersManager,
  [NAV.MANAGE_GROUPS]: GroupsManager,
  [NAV.MANAGE_PROJECTS]: ProjectsManager,
  [NAV.MANAGE_REVIEWS]: ReviewsManager,
  [NAV.MANAGE_DASHBOARD_REPORTS]: DashboardReportsManager,
}

export default function LandingPage() {
  const { currentPage, sidebarCollapsed } = usePortalStore()
  const PageComponent = PAGE_MAP[currentPage] || Dashboard

  const sidebarW = sidebarCollapsed ? 60 : 240

  return (
    <div className="h-screen flex flex-col bg-slate-950 overflow-hidden">
      <TopBar />
      <div className="flex flex-1 overflow-hidden" style={{ paddingTop: 56 }}>
        {/* Sidebar */}
        <div style={{ width: sidebarW, flexShrink: 0, transition: 'width 0.2s ease' }}>
          <Sidebar />
        </div>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto bg-slate-950 p-6">
          <PageComponent />
        </main>
      </div>

      <Notification />
    </div>
  )
}
