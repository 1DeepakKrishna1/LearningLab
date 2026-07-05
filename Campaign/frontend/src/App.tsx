import { useEffect } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useAuth } from './store/auth';
import { Layout } from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CampaignList from './pages/CampaignList';
import CampaignBuilder from './pages/CampaignBuilder';
import CampaignDetails from './pages/CampaignDetails';
import CampaignCalendar from './pages/CampaignCalendar';
import TemplateLibrary from './pages/TemplateLibrary';
import ContactManagement from './pages/ContactManagement';
import SegmentBuilder from './pages/SegmentBuilder';
import Analytics from './pages/Analytics';
import Reports from './pages/Reports';
import UserManagement from './pages/UserManagement';
import ProviderConfiguration from './pages/ProviderConfiguration';
import AuditLogs from './pages/AuditLogs';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, initialized } = useAuth();
  const location = useLocation();
  if (!initialized) {
    return (
      <Box sx={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

export default function App() {
  const loadMe = useAuth((s) => s.loadMe);
  useEffect(() => { void loadMe(); }, [loadMe]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/campaigns" element={<CampaignList />} />
                <Route path="/campaigns/new" element={<CampaignBuilder />} />
                <Route path="/campaigns/:id/edit" element={<CampaignBuilder />} />
                <Route path="/campaigns/:id" element={<CampaignDetails />} />
                <Route path="/calendar" element={<CampaignCalendar />} />
                <Route path="/templates" element={<TemplateLibrary />} />
                <Route path="/contacts" element={<ContactManagement />} />
                <Route path="/segments" element={<SegmentBuilder />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/users" element={<UserManagement />} />
                <Route path="/providers" element={<ProviderConfiguration />} />
                <Route path="/audit" element={<AuditLogs />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
