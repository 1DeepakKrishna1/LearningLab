import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";

import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import ProductAdminHome from "./pages/product/ProductAdminHome.jsx";
import SystemCreate from "./pages/product/SystemCreate.jsx";
import SystemDetail from "./pages/product/SystemDetail.jsx";
import SystemAdminHome from "./pages/sysadmin/SystemAdminHome.jsx";
import Members from "./pages/sysadmin/Members.jsx";
import Options from "./pages/sysadmin/Options.jsx";
import Reports from "./pages/sysadmin/Reports.jsx";
import AILogs from "./pages/sysadmin/AILogs.jsx";
import ApplicantHome from "./pages/applicant/ApplicantHome.jsx";
import ApplicationDetail from "./pages/applicant/ApplicationDetail.jsx";
import StaffHome from "./pages/staff/StaffHome.jsx";

function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  const dest = {
    product_admin: "/product",
    system_admin: "/admin",
    applicant: "/apply",
  }[user.role] || "/staff";
  return <Navigate to={dest} replace />;
}

const ADMINS = ["product_admin", "system_admin"];
const STAFF = [
  "verifier", "evaluator", "allocation_authority", "payment_agency",
  "auditor", "support", "institution", "reporting_authority",
];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Home />} />

      {/* Product Admin */}
      <Route path="/product" element={<ProtectedRoute roles={["product_admin"]}><ProductAdminHome /></ProtectedRoute>} />
      <Route path="/product/systems/new" element={<ProtectedRoute roles={["product_admin"]}><SystemCreate /></ProtectedRoute>} />
      <Route path="/product/systems/:id" element={<ProtectedRoute roles={["product_admin"]}><SystemDetail /></ProtectedRoute>} />

      {/* System Admin (and product admin can view) */}
      <Route path="/admin" element={<ProtectedRoute roles={ADMINS}><SystemAdminHome /></ProtectedRoute>} />
      <Route path="/admin/members" element={<ProtectedRoute roles={ADMINS}><Members /></ProtectedRoute>} />
      <Route path="/admin/options" element={<ProtectedRoute roles={ADMINS}><Options /></ProtectedRoute>} />
      <Route path="/admin/reports" element={<ProtectedRoute roles={[...ADMINS, "auditor", "reporting_authority", "allocation_authority"]}><Reports /></ProtectedRoute>} />
      <Route path="/admin/ai-logs" element={<ProtectedRoute roles={[...ADMINS, "auditor", "reporting_authority"]}><AILogs /></ProtectedRoute>} />

      {/* Applicant */}
      <Route path="/apply" element={<ProtectedRoute roles={["applicant"]}><ApplicantHome /></ProtectedRoute>} />
      <Route path="/apply/:appId" element={<ProtectedRoute roles={["applicant"]}><ApplicationDetail /></ProtectedRoute>} />

      {/* Staff */}
      <Route path="/staff" element={<ProtectedRoute roles={STAFF}><StaffHome /></ProtectedRoute>} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
