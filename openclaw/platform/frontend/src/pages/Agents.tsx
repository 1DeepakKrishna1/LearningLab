import { useEffect, useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, Grid, Stack, Typography,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, MenuItem,
  Autocomplete, IconButton,
} from "@mui/material";
import { Plus, Trash2 } from "lucide-react";
import { Api } from "../api/client";
import type { Agent, ToolManifest } from "../api/types";

const ROLES = ["supervisor", "planner", "executor", "researcher", "reviewer", "custom"];

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<ToolManifest[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Partial<Agent>>({ role: "executor", tools: [], temperature: 0 });

  const load = () => Api.agents().then(setAgents).catch(() => {});
  useEffect(() => {
    load();
    Api.tools().then(setTools).catch(() => {});
  }, []);

  const create = async () => {
    await Api.createAgent(form);
    setOpen(false);
    setForm({ role: "executor", tools: [], temperature: 0 });
    load();
  };

  const remove = async (id: string) => { await Api.deleteAgent(id); load(); };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>Agent Manager</Typography>
        <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setOpen(true)}>
          New Agent
        </Button>
      </Stack>

      <Grid container spacing={2}>
        {agents.map((a) => (
          <Grid item xs={12} md={4} key={a.agent_id}>
            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between">
                  <Typography variant="h6">{a.name}</Typography>
                  <IconButton size="small" onClick={() => remove(a.agent_id)}><Trash2 size={16} /></IconButton>
                </Stack>
                <Chip size="small" label={a.role} sx={{ mb: 1 }} />
                <Typography variant="body2" color="text.secondary">{a.description}</Typography>
                <Typography variant="caption" sx={{ mt: 1, display: "block" }}>
                  Model: {a.model || "default"} · {a.tools.length} tools
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {agents.length === 0 && (
          <Grid item xs={12}><Typography color="text.secondary">No agents configured.</Typography></Grid>
        )}
      </Grid>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New Agent</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="Name" margin="normal"
            value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <TextField fullWidth label="Description" margin="normal"
            value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <TextField select fullWidth label="Role" margin="normal" value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
          </TextField>
          <TextField fullWidth label="Model (optional)" margin="normal"
            placeholder="claude-sonnet-4-6"
            value={form.model || ""} onChange={(e) => setForm({ ...form, model: e.target.value })} />
          <Autocomplete multiple options={tools.map((t) => t.id)}
            value={form.tools || []}
            onChange={(_, v) => setForm({ ...form, tools: v })}
            renderInput={(p) => <TextField {...p} label="Tools" margin="normal" />} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!form.name} onClick={create}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
