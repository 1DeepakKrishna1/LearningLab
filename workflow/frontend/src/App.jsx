import React, { useEffect, useState } from 'react'
import { ReactFlowProvider } from 'reactflow'

import useAuthStore from './store/authStore'
import usePortalStore from './store/portalStore'
import useStore from './store/workflowStore'
import { installAutoInstrumentation, trackEvent } from './api/obs'

import LoginPage from './pages/LoginPage'
import LandingPage from './pages/LandingPage'

// Studio components (original app)
import Toolbar from './components/Toolbar'
import LibraryPanel from './components/LibraryPanel'
import WorkflowCanvas from './components/WorkflowCanvas'
import PropertiesPanel from './components/PropertiesPanel'
import AIAssistant from './components/AIAssistant'
import ExecutionPanel from './components/ExecutionPanel'
import HumanInputModal from './components/HumanInputModal'

function Studio() {
  const { loadLibrary, loadUserWorkflows, theme, loadWorkflow } = useStore()
  const [showLeft, setShowLeft] = useState(true)
  const [showRight, setShowRight] = useState(true)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    loadLibrary()
    loadUserWorkflows().then(() => {
      // Open a specific workflow if requested from the portal
      try {
        const req = JSON.parse(localStorage.getItem('wf-open-workflow') || 'null')
        if (req?.workflowId) {
          loadWorkflow(req.workflowId)
          localStorage.removeItem('wf-open-workflow')
        }
      } catch (_) {}
    })
  }, [])

  return (
    <div className="h-screen flex flex-col bg-slate-950 overflow-hidden">
      <Toolbar />
      <div className="flex flex-1 overflow-hidden">
        <LibraryPanel collapsed={!showLeft} onToggle={() => setShowLeft(v => !v)} />
        <ReactFlowProvider>
          <main className="flex-1 flex flex-col overflow-hidden">
            <WorkflowCanvas />
            <ExecutionPanel />
          </main>
        </ReactFlowProvider>
        <PropertiesPanel collapsed={!showRight} onToggle={() => setShowRight(v => !v)} />
      </div>
      <AIAssistant />
      <HumanInputModal />
    </div>
  )
}

export default function App() {
  const { init, isAuthenticated } = useAuthStore()
  const { appView, setAppView, currentPage, loadOrgConfig } = usePortalStore()
  const { theme } = useStore()

  useEffect(() => {
    // Apply persisted theme
    document.documentElement.setAttribute('data-theme', theme)
    // Load org branding (name/logo) from backend
    loadOrgConfig()
    // Restore auth session
    init()
    // Initialize frontend observability (global error/perf capture + flush loop)
    installAutoInstrumentation()
  }, [])

  // Track page navigation events for the Live Monitor / Insights timeline.
  useEffect(() => {
    trackEvent('nav', `view:${appView}/${currentPage || ''}`, {
      attributes: { app_view: appView, page: currentPage },
    })
  }, [appView, currentPage])

  useEffect(() => {
    // If auth state changes externally (e.g. token expired), redirect to login
    if (!isAuthenticated() && appView !== 'login') {
      setAppView('login')
    }
    // After successful auth init, go to landing with the user's preferred page
    if (isAuthenticated() && appView === 'login') {
      const { defaultLandingPage, setCurrentPage } = usePortalStore.getState()
      setCurrentPage(defaultLandingPage)
      setAppView('landing')
    }
  }, [isAuthenticated()])

  if (appView === 'login') return <LoginPage />
  if (appView === 'studio') return <Studio />
  return <LandingPage />
}
