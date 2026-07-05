import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import { apiError } from "../api/client.js";

const DEMO = [
  ["Product Admin", "product.admin@ialloc.io"],
  ["System Admin", "nta.admin@ialloc.io"],
  ["Applicant", "applicant@ialloc.io"],
  ["Verifier", "verifier@ialloc.io"],
  ["Evaluator", "evaluator@ialloc.io"],
  ["Allocator", "allocator@ialloc.io"],
  ["Auditor", "auditor@ialloc.io"],
];

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("Admin@123");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(email, password);
      nav("/");
    } catch (e2) {
      setErr(apiError(e2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <h1>i<span>Alloc</span></h1>
        <div className="sub">Generalized allocation & enrollment platform</div>
        <form onSubmit={submit}>
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          <label>Password</label>
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        </form>
        {err && <div className="error">{err}</div>}
        <div style={{ marginTop: 14, fontSize: 13 }}>
          New applicant? <Link to="/register">Register here</Link>
        </div>
        <div className="demo-creds">
          Demo logins (password <code>Admin@123</code>):
          <div style={{ marginTop: 6, lineHeight: 1.9 }}>
            {DEMO.map(([role, e]) => (
              <div key={e}>
                {role}: <code onClick={() => setEmail(e)}>{e}</code>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
