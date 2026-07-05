import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const ROLE_LABELS = {
  product_admin: "Product Admin",
  system_admin: "System Admin",
  applicant: "Applicant",
  verifier: "Verifier",
  evaluator: "Evaluator",
  allocation_authority: "Allocation Authority",
  payment_agency: "Payment Agency",
  auditor: "Auditor",
  support: "Support",
  institution: "Institution",
  reporting_authority: "Reporting Authority",
};

function navFor(role) {
  switch (role) {
    case "product_admin":
      return [
        ["/product", "Systems Overview"],
        ["/product/systems/new", "Create System"],
      ];
    case "system_admin":
      return [
        ["/admin", "Configure System"],
        ["/admin/members", "Stakeholders"],
        ["/admin/options", "Allocation Options"],
        ["/admin/reports", "Reports & Audit"],
        ["/admin/ai-logs", "AI Activity"],
      ];
    case "applicant":
      return [["/apply", "My Applications"]];
    case "verifier":
      return [["/staff", "Verification Queue"]];
    case "evaluator":
      return [["/staff", "Evaluation Queue"]];
    case "allocation_authority":
      return [
        ["/staff", "Ranking & Allocation"],
        ["/admin/reports", "Reports"],
      ];
    case "auditor":
      return [
        ["/admin/reports", "Audit & Reports"],
        ["/admin/ai-logs", "AI Activity"],
      ];
    case "reporting_authority":
      return [
        ["/admin/reports", "Reports"],
        ["/staff", "Merit List"],
      ];
    default:
      return [["/staff", "Workspace"]];
  }
}

export default function Layout({ children, title }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  if (!user) return null;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">i<span>Alloc</span></div>
        <div className="role-chip">{ROLE_LABELS[user.role] || user.role}</div>
        <nav>
          {navFor(user.role).map(([to, label]) => (
            <NavLink key={to} to={to} end>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <div className="who">
          {user.full_name}
          <br />
          <span className="muted">{user.email}</span>
        </div>
        <button
          className="secondary"
          onClick={() => {
            logout();
            nav("/login");
          }}
        >
          Sign out
        </button>
      </aside>
      <main className="main">
        {title && (
          <div className="topbar">
            <h1>{title}</h1>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
