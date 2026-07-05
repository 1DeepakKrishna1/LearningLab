import { useEffect, useState } from "react";
import { Box, Card, CardContent, Grid, Typography, Chip, LinearProgress } from "@mui/material";
import { Api } from "../api/client";
import type { Dashboard as DashboardData } from "../api/types";

function Stat({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography variant="h4" sx={{ fontWeight: 700, color }}>{value}</Typography>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    const load = () => Api.dashboard().then(setData).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  if (!data) return <LinearProgress />;
  const e = data.executions;

  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 3 }}>Dashboard</Typography>
      <Grid container spacing={2}>
        <Grid item xs={6} md={3}><Stat label="Running" value={e.running} color="#2563EB" /></Grid>
        <Grid item xs={6} md={3}><Stat label="Completed" value={e.completed} color="#16A34A" /></Grid>
        <Grid item xs={6} md={3}><Stat label="Failed" value={e.failed} color="#DC2626" /></Grid>
        <Grid item xs={6} md={3}><Stat label="Waiting Approval" value={e.waiting_approval} color="#D97706" /></Grid>
        <Grid item xs={6} md={3}><Stat label="Queue Depth" value={data.queue_depth} color="#7C3AED" /></Grid>
        <Grid item xs={6} md={3}><Stat label="Active Agents" value={data.active_agents} color="#0EA5E9" /></Grid>
        <Grid item xs={6} md={3}><Stat label="Tools Registered" value={data.tools.registered} color="#6366F1" /></Grid>
        <Grid item xs={6} md={3}><Stat label="Tool Categories" value={data.tools.categories} color="#EC4899" /></Grid>
      </Grid>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Top Tool Usage</Typography>
          {data.tool_usage.length === 0 && (
            <Typography color="text.secondary">No tool calls recorded yet.</Typography>
          )}
          {data.tool_usage.map(([tool, count]) => (
            <Box key={tool} sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}>
              <Typography>{tool}</Typography>
              <Chip size="small" label={count} />
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  );
}
