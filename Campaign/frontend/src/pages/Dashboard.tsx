import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Card, CardContent, Grid, Stack, Typography } from '@mui/material';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useOverview, useTimeseries, useCampaigns } from '../api/hooks';
import { PageHeader, Loading, ErrorState, StatusChip } from '../components/shared';
import { apiErrorMessage } from '../api/client';

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography variant="h4" fontWeight={700}>{value}</Typography>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const overview = useOverview();
  const series = useTimeseries();
  const recent = useCampaigns({ page_size: 5 });

  if (overview.isLoading) return <Loading />;
  if (overview.error) return <ErrorState message={apiErrorMessage(overview.error)} />;
  const o = overview.data!;

  return (
    <Box>
      <PageHeader title="Dashboard" subtitle="Overview of your campaign performance"
        action={<Button component={RouterLink} to="/campaigns/new" variant="contained">New Campaign</Button>} />
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}><StatCard label="Total Campaigns" value={o.total_campaigns} /></Grid>
        <Grid item xs={6} md={3}><StatCard label="Active" value={o.active_campaigns} /></Grid>
        <Grid item xs={6} md={3}><StatCard label="Contacts" value={o.total_contacts} /></Grid>
        <Grid item xs={6} md={3}><StatCard label="Messages Sent" value={o.sent} /></Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Engagement (last 30 days)</Typography>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={series.data ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={11} />
                  <YAxis fontSize={11} allowDecimals={false} />
                  <Tooltip />
                  <Area type="monotone" dataKey="delivered" stroke="#1976d2" fill="#1976d2" fillOpacity={0.15} />
                  <Area type="monotone" dataKey="opened" stroke="#2e7d32" fill="#2e7d32" fillOpacity={0.15} />
                  <Area type="monotone" dataKey="clicked" stroke="#ed6c02" fill="#ed6c02" fillOpacity={0.15} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Recent Campaigns</Typography>
              <Stack spacing={1.5}>
                {(recent.data?.items ?? []).map((c) => (
                  <Stack key={c.id} direction="row" justifyContent="space-between" alignItems="center"
                    component={RouterLink} to={`/campaigns/${c.id}`}
                    sx={{ textDecoration: 'none', color: 'inherit' }}>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 150 }}>{c.name}</Typography>
                    <StatusChip status={c.status} />
                  </Stack>
                ))}
                {recent.data?.items.length === 0 && (
                  <Typography variant="body2" color="text.secondary">No campaigns yet.</Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
