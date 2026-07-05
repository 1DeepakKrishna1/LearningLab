import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Card, Paper, TextField, Typography, Chip } from "@mui/material";
import { Send } from "lucide-react";
import { Api } from "../api/client";

interface Msg { role: "user" | "bot"; text: string; action?: string; data?: any; }

export default function Chatbot() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Msg[]>([
    { role: "bot", text: "Hi! I can build and run workflows for you. Try: \"Create a workflow that reads email attachments and stores invoices in Excel\"." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim()) return;
    const text = input;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const res = await Api.chat(text);
      setMessages((m) => [...m, { role: "bot", text: res.reply, action: res.action, data: res.data }]);
    } catch {
      setMessages((m) => [...m, { role: "bot", text: "Something went wrong." }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: "auto" }}>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 2 }}>AI Chatbot</Typography>
      <Card sx={{ height: "calc(100vh - 260px)", display: "flex", flexDirection: "column", p: 2 }}>
        <Box sx={{ flexGrow: 1, overflow: "auto", display: "flex", flexDirection: "column", gap: 1.5 }}>
          {messages.map((m, i) => (
            <Box key={i} sx={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
              <Paper sx={{
                p: 1.5, maxWidth: "75%",
                bgcolor: m.role === "user" ? "#6366F1" : "#f1f5f9",
                color: m.role === "user" ? "#fff" : "inherit",
                whiteSpace: "pre-wrap",
              }}>
                <Typography variant="body2">{m.text}</Typography>
                {m.action === "workflow_created" && m.data?.workflow_id && (
                  <Button size="small" variant="contained" sx={{ mt: 1 }}
                    onClick={() => navigate(`/workflows/${m.data.workflow_id}`)}>
                    Open in Builder
                  </Button>
                )}
                {m.action && <Chip size="small" label={m.action} sx={{ mt: 1 }} />}
              </Paper>
            </Box>
          ))}
          <div ref={endRef} />
        </Box>
        <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
          <TextField fullWidth size="small" placeholder="Ask me to build or run a workflow…"
            value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !busy && send()} />
          <Button variant="contained" disabled={busy} onClick={send} startIcon={<Send size={16} />}>
            Send
          </Button>
        </Box>
      </Card>
    </Box>
  );
}
