import { useEffect, useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, Stack, Typography, TextField,
} from "@mui/material";
import { Check, X, Edit3, ArrowUpCircle } from "lucide-react";
import { Api } from "../api/client";
import type { Approval } from "../api/types";

export default function Approvals() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [comments, setComments] = useState<Record<string, string>>({});

  const load = () => Api.approvals().then(setApprovals).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  const decide = async (id: string, decision: string) => {
    await Api.respondApproval(id, decision, comments[id]);
    load();
  };

  const pending = approvals.filter((a) => a.status === "pending");
  const decided = approvals.filter((a) => a.status !== "pending");

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>Approvals</Typography>

      <Typography variant="h6" sx={{ mb: 1 }}>Pending ({pending.length})</Typography>
      <Stack spacing={2} sx={{ mb: 4 }}>
        {pending.map((a) => (
          <Card key={a.id}>
            <CardContent>
              <Typography variant="h6">{a.title}</Typography>
              <Typography variant="body2" color="text.secondary">{a.description}</Typography>
              <Stack direction="row" spacing={1} sx={{ my: 1 }}>
                <Chip size="small" label={`channel: ${a.channel}`} />
                <Chip size="small" label={`exec: ${a.execution_id.slice(0, 8)}`} />
              </Stack>
              <TextField fullWidth size="small" placeholder="Comment (optional)" sx={{ mb: 1 }}
                value={comments[a.id] || ""}
                onChange={(e) => setComments({ ...comments, [a.id]: e.target.value })} />
              <Stack direction="row" spacing={1}>
                <Button size="small" color="success" variant="contained"
                  startIcon={<Check size={16} />} onClick={() => decide(a.id, "approved")}>Approve</Button>
                <Button size="small" color="error" variant="outlined"
                  startIcon={<X size={16} />} onClick={() => decide(a.id, "rejected")}>Reject</Button>
                <Button size="small" startIcon={<Edit3 size={16} />}
                  onClick={() => decide(a.id, "changes_requested")}>Request Changes</Button>
                <Button size="small" startIcon={<ArrowUpCircle size={16} />}
                  onClick={() => decide(a.id, "escalated")}>Escalate</Button>
              </Stack>
            </CardContent>
          </Card>
        ))}
        {pending.length === 0 && <Typography color="text.secondary">No pending approvals.</Typography>}
      </Stack>

      <Typography variant="h6" sx={{ mb: 1 }}>History</Typography>
      <Stack spacing={1}>
        {decided.map((a) => (
          <Card key={a.id} variant="outlined">
            <CardContent sx={{ py: 1, display: "flex", justifyContent: "space-between" }}>
              <Typography>{a.title}</Typography>
              <Chip size="small" label={a.status}
                color={a.status === "approved" ? "success" : a.status === "rejected" ? "error" : "default"} />
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
}
