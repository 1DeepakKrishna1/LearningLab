import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Button, Card, CardContent, Chip, Grid, Typography, Stack,
  Dialog, DialogTitle, DialogContent, TextField, DialogActions, IconButton,
} from "@mui/material";
import { Plus, Sparkles, Trash2 } from "lucide-react";
import { Api } from "../api/client";
import type { Workflow } from "../api/types";

export default function WorkflowList() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => Api.workflows().then(setWorkflows).catch(() => {});
  useEffect(() => { load(); }, []);

  const generate = async () => {
    setBusy(true);
    try {
      const wf = await Api.generateWorkflow(prompt);
      setAiOpen(false);
      setPrompt("");
      navigate(`/workflows/${wf.id}`);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await Api.deleteWorkflow(id);
    load();
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>Workflows</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<Sparkles size={16} />} onClick={() => setAiOpen(true)}>
            AI Builder
          </Button>
          <Button variant="contained" startIcon={<Plus size={16} />}
            onClick={() => navigate("/workflows/new")}>New Workflow</Button>
        </Stack>
      </Stack>

      <Grid container spacing={2}>
        {workflows.map((wf) => (
          <Grid item xs={12} md={4} key={wf.id}>
            <Card sx={{ cursor: "pointer", "&:hover": { boxShadow: 4 } }}
              onClick={() => navigate(`/workflows/${wf.id}`)}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="start">
                  <Typography variant="h6">{wf.name}</Typography>
                  <IconButton size="small" onClick={(e) => remove(wf.id, e)}><Trash2 size={16} /></IconButton>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ minHeight: 40 }}>
                  {wf.description || "No description"}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  <Chip size="small" label={wf.status} />
                  <Chip size="small" label={`v${wf.version}`} />
                  <Chip size="small" label={`${wf.nodes.length} nodes`} />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {workflows.length === 0 && (
          <Grid item xs={12}><Typography color="text.secondary">No workflows yet.</Typography></Grid>
        )}
      </Grid>

      <Dialog open={aiOpen} onClose={() => setAiOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>AI Workflow Builder</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Describe the workflow in plain English. The AI builder discovers tools and
            generates the graph automatically.
          </Typography>
          <TextField autoFocus fullWidth multiline minRows={3}
            placeholder="e.g. Read email attachments and store invoices in Excel"
            value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAiOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={busy || !prompt.trim()} onClick={generate}>
            {busy ? "Generating…" : "Generate"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
