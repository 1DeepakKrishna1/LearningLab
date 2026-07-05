import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Card, CardContent, TextField, Typography, Alert } from "@mui/material";
import { AxiosError } from "axios";
import { useAuth } from "../store/auth";

function describeError(err: unknown): string {
  const ax = err as AxiosError<{ detail?: string }>;
  if (ax?.isAxiosError) {
    // No response → the request never reached FastAPI (proxy/backend down).
    if (!ax.response) {
      return "Cannot reach the backend. Is it running on http://localhost:8000? " +
        "Start it with: uvicorn app.main:app --reload";
    }
    if (ax.response.status === 401) return "Invalid email or password.";
    const detail = ax.response.data?.detail;
    // A 500 with no JSON detail is almost always the Vite proxy failing to reach
    // the backend (FastAPI errors return JSON with a `detail`).
    if (ax.response.status === 500 && !detail) {
      return "Cannot reach the backend on http://localhost:8000. " +
        "Start it with: uvicorn app.main:app --reload (run from platform/backend).";
    }
    return `Server error (${ax.response.status})${detail ? `: ${detail}` : ""}.`;
  }
  return "Login failed. Please try again.";
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@clawflow.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(describeError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", placeItems: "center", height: "100vh",
      background: "linear-gradient(135deg,#1e1b4b,#4F46E5)" }}>
      <Card sx={{ width: 380 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>🦅 ClawFlow</Typography>
          <Typography sx={{ mb: 3, color: "text.secondary" }}>
            Agentic Workflow Automation Platform
          </Typography>
          <form onSubmit={submit}>
            <TextField fullWidth label="Email" margin="normal" value={email}
              onChange={(e) => setEmail(e.target.value)} />
            <TextField fullWidth label="Password" type="password" margin="normal"
              value={password} onChange={(e) => setPassword(e.target.value)} />
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
            <Button fullWidth variant="contained" type="submit" disabled={busy}
              sx={{ mt: 3 }}>
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
}
