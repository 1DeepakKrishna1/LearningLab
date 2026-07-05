import { useEffect, useState } from "react";
import {
  Box, Card, CardContent, Chip, Typography, Table, TableBody, TableCell,
  TableHead, TableRow, Button, Collapse, IconButton,
} from "@mui/material";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Api } from "../api/client";
import type { Execution } from "../api/types";

const STATUS_COLOR: Record<string, any> = {
  running: "info", completed: "success", failed: "error",
  waiting_approval: "warning", paused: "warning", cancelled: "default", pending: "default",
};

function Row({ ex }: { ex: Execution }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <TableRow hover>
        <TableCell>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </IconButton>
        </TableCell>
        <TableCell>{ex.workflow_name}</TableCell>
        <TableCell><Chip size="small" color={STATUS_COLOR[ex.status]} label={ex.status} /></TableCell>
        <TableCell>{ex.node_runs.length}</TableCell>
        <TableCell>{ex.started_at?.slice(0, 19).replace("T", " ") || "—"}</TableCell>
        <TableCell><code style={{ fontSize: 11 }}>{ex.id.slice(0, 8)}</code></TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={6} sx={{ p: 0, border: 0 }}>
          <Collapse in={open} unmountOnExit>
            <Box sx={{ p: 2, bgcolor: "#f8fafc" }}>
              {ex.error && <Typography color="error" sx={{ mb: 1 }}>{ex.error}</Typography>}
              {ex.node_runs.map((r) => (
                <Box key={r.node_id} sx={{ display: "flex", gap: 2, py: 0.3 }}>
                  <Chip size="small" color={STATUS_COLOR[r.status] || "default"} label={r.status} />
                  <Typography sx={{ fontWeight: 600 }}>{r.label || r.node_id}</Typography>
                  <Typography variant="body2" color="text.secondary">{r.node_type}</Typography>
                  {r.error && <Typography variant="body2" color="error">{r.error}</Typography>}
                </Box>
              ))}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export default function Executions() {
  const [executions, setExecutions] = useState<Execution[]>([]);

  useEffect(() => {
    const load = () => Api.executions().then(setExecutions).catch(() => {});
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>Workflow Executions</Typography>
      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell />
                <TableCell>Workflow</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Nodes</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>ID</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {executions.map((ex) => <Row key={ex.id} ex={ex} />)}
            </TableBody>
          </Table>
          {executions.length === 0 && (
            <Typography color="text.secondary" sx={{ p: 2 }}>No executions yet.</Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
