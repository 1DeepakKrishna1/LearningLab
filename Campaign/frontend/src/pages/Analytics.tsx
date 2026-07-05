import { useState } from 'react';
import { Box, Card, CardContent, Grid, MenuItem, TextField, Typography } from '@mui/material';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useCampaigns, useCampaignMetrics, useTimeseries } from '../api/hooks';
import { PageHeader, Loading } from '../components/shared';

const COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#9c27b0', '#d32f2f'];

export default function Analytics() {
  const campaigns = useCampaigns({ page_size: 200 });
  const [campaignId, setCampaignId] = useState<number | ''>('');
  const series = useTimeseries(campaignId || undefined);
  const metrics = useCampaignMetrics(campaignId || undefined);

  if (campaigns.isLoading) return <Loading />;

  const funnel = metrics.data ? [
    { name: 'Sent', value: metrics.data.sent },
    { name: 'Delivered', value: metrics.data.delivered },
    { name: 'Opened', value: metrics.data.opened },
    { name: 'Clicked', value: metrics.data.clicked },
  ] : [];

  const rates = metrics.data ? [
    { name: 'Delivery', value: Math.round(metrics.data.delivery_rate * 100) },
    { name: 'Open', value: Math.round(metrics.data.open_rate * 100) },
    { name: 'Click', value: Math.round(metrics.data.click_rate * 100) },
    { name: 'Bounce', value: Math.round(metrics.data.bounce_rate * 100) },
  ] : [];

  return (
    <Box>
      <PageHeader title="Analytics" subtitle="Campaign and channel performance" />
      <TextField select size="small" label="Campaign" value={campaignId} sx={{ minWidth: 260, mb: 2 }}
        onChange={(e) => setCampaignId(e.target.value === '' ? '' : Number(e.target.value))}>
        <MenuItem value="">All campaigns (timeseries)</MenuItem>
        {(campaigns.data?.items ?? []).map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
      </TextField>

      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <Card><CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Engagement over time</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={series.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" fontSize={11} /><YAxis fontSize={11} allowDecimals={false} />
                <Tooltip /><Legend />
                <Line type="monotone" dataKey="delivered" stroke="#1976d2" />
                <Line type="monotone" dataKey="opened" stroke="#2e7d32" />
                <Line type="monotone" dataKey="clicked" stroke="#ed6c02" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={5}>
          <Card><CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Conversion funnel</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={funnel} dataKey="value" nameKey="name" outerRadius={100} label>
                  {funnel.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip /><Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12}>
          <Card><CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Key rates (%)</Typography>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={rates}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" fontSize={12} /><YAxis fontSize={12} />
                <Tooltip /><Bar dataKey="value" fill="#1976d2" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent></Card>
        </Grid>
      </Grid>
    </Box>
  );
}
