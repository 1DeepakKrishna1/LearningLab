import { useEffect, useMemo, useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, Grid, Stack, TextField, Typography,
  Dialog, DialogTitle, DialogContent, DialogActions, Table, TableBody, TableCell, TableRow,
} from "@mui/material";
import { RefreshCw } from "lucide-react";
import { Api } from "../api/client";
import type { ToolManifest } from "../api/types";

export default function ToolLibrary() {
  const [tools, setTools] = useState<ToolManifest[]>([]);
  const [q, setQ] = useState("");
  const [detail, setDetail] = useState<ToolManifest | null>(null);

  const load = () => Api.tools().then(setTools).catch(() => {});
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const s = q.toLowerCase();
    return tools.filter((t) => t.id.includes(s) || t.display_name.toLowerCase().includes(s)
      || t.description.toLowerCase().includes(s));
  }, [tools, q]);

  const byCategory = useMemo(() => {
    const m: Record<string, ToolManifest[]> = {};
    filtered.forEach((t) => (m[t.category] ??= []).push(t));
    return m;
  }, [filtered]);

  const refresh = async () => { await Api.refreshTools(); load(); };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Tool Library <Chip label={`${tools.length} tools`} sx={{ ml: 1 }} />
        </Typography>
        <Button variant="outlined" startIcon={<RefreshCw size={16} />} onClick={refresh}>
          Rescan Library
        </Button>
      </Stack>
      <TextField fullWidth size="small" placeholder="Search tools…" sx={{ mb: 2 }}
        value={q} onChange={(e) => setQ(e.target.value)} />

      {Object.entries(byCategory).map(([cat, items]) => (
        <Box key={cat} sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 1, textTransform: "capitalize" }}>
            {cat.replace("_", " ")} <Chip size="small" label={items.length} />
          </Typography>
          <Grid container spacing={1.5}>
            {items.map((t) => (
              <Grid item xs={12} md={4} key={t.id}>
                <Card sx={{ cursor: "pointer", borderLeft: `4px solid ${t.color}` }}
                  onClick={() => setDetail(t)}>
                  <CardContent sx={{ py: 1.5 }}>
                    <Typography sx={{ fontWeight: 600 }}>{t.display_name}</Typography>
                    <Typography variant="caption" color="text.secondary"
                      sx={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                      {t.description}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}

      <Dialog open={!!detail} onClose={() => setDetail(null)} fullWidth maxWidth="md">
        {detail && (
          <>
            <DialogTitle>{detail.display_name} <code style={{ fontSize: 13 }}>({detail.id})</code></DialogTitle>
            <DialogContent>
              <Typography sx={{ mb: 2 }}>{detail.description}</Typography>
              <Typography variant="subtitle2">Parameters</Typography>
              <Table size="small">
                <TableBody>
                  {detail.parameters.map((p) => (
                    <TableRow key={p.name}>
                      <TableCell sx={{ fontWeight: 600 }}>{p.name}{p.required ? " *" : ""}</TableCell>
                      <TableCell><code>{p.type}</code></TableCell>
                      <TableCell>{p.description}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
                impl: {detail.impl_path}
              </Typography>
            </DialogContent>
            <DialogActions><Button onClick={() => setDetail(null)}>Close</Button></DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}
