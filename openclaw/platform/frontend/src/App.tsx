import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { CircularProgress, Box } from "@mui/material";
import { useAuth } from "./store/auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import WorkflowList from "./pages/WorkflowList";
import WorkflowBuilder from "./pages/WorkflowBuilder";
import Executions from "./pages/Executions";
import Agents from "./pages/Agents";
import ToolLibrary from "./pages/ToolLibrary";
import Approvals from "./pages/Approvals";
import AuditLogs from "./pages/AuditLogs";
import Settings from "./pages/Settings";
import Chatbot from "./pages/Chatbot";

export default function App() {
  const { user, loading, restore } = useAuth();

  useEffect(() => {
    restore();
  }, [restore]);

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", height: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/workflows" element={<WorkflowList />} />
        <Route path="/workflows/:id" element={<WorkflowBuilder />} />
        <Route path="/executions" element={<Executions />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/tools" element={<ToolLibrary />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/audit" element={<AuditLogs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/chatbot" element={<Chatbot />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
      <Route path="/login" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
