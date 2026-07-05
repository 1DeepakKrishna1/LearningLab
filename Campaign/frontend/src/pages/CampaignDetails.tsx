import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Button, Card, CardContent, Divider, Grid, Stack, TextField, Typography,
} from '@mui/material';
import { useCampaign, useCampaignAction, useCampaignMetrics } from '../api/hooks';
import { PageHeader, Loading, StatusChip, ErrorState } from '../components/shared';
import { useAuth } from '../store/auth';
import { apiErrorMessage } from '../api/client';

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <Grid item xs={6} sm={3}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="h5" fontWeight={700}>{value}</Typography>
    </Grid>
  );
}

export default function CampaignDetails() {
  const { id } = useParams();
  const cid = Number(id);
  const navigate = useNavigate();
  const { data: c, isLoading, error } = useCampaign(cid);
  const metrics = useCampaignMetrics(cid);
  const action = useCampaignAction();
  const canEdit = useAuth((s) => s.hasRole('admin', 'marketer'));
  const [reason, setReason] = useState('');

  if (isLoading) return <Loading />;
  if (error || !c) return <ErrorState message={apiErrorMessage(error)} />;

  const run = (a: string, body?: unknown) => action.mutate({ id: cid, action: a, body });

  const actions: React.ReactNode[] = [];
  if (canEdit) {
    if (c.status === 'draft') actions.push(<Button key="submit" variant="contained" onClick={() => run('submit')}>Submit for Approval</Button>);
    if (c.status === 'pending_approval') {
      actions.push(<Button key="approve" variant="contained" color="success" onClick={() => run('approve', { approved: true })}>Approve</Button>);
      actions.push(<Button key="reject" variant="outlined" color="error" onClick={() => run('approve', { approved: false, reason })}>Reject</Button>);
    }
    if (c.status === 'approved') {
      actions.push(<Button key="send" variant="contained" onClick={() => run('schedule', { scheduled_at: null })}>Send Now</Button>);
    }
    if (c.status === 'scheduled' || c.status === 'sending') actions.push(<Button key="pause" variant="outlined" onClick={() => run('pause')}>Pause</Button>);
    if (c.status === 'paused') actions.push(<Button key="resume" variant="contained" onClick={() => run('resume')}>Resume</Button>);
    if (!['completed', 'cancelled', 'archived'].includes(c.status)) actions.push(<Button key="cancel" variant="text" color="error" onClick={() => run('cancel')}>Cancel</Button>);
    if (['completed', 'cancelled', 'failed', 'paused'].includes(c.status)) actions.push(<Button key="archive" variant="text" onClick={() => run('archive')}>Archive</Button>);
    if (['draft', 'pending_approval'].includes(c.status)) actions.push(<Button key="edit" variant="outlined" onClick={() => navigate(`/campaigns/${cid}/edit`)}>Edit</Button>);
  }

  const m = metrics.data;

  return (
    <Box>
      <PageHeader title={c.name} subtitle={c.description || 'Campaign details'}
        action={<Stack direction="row" spacing={1} flexWrap="wrap">{actions}</Stack>} />

      {action.error && <ErrorState message={apiErrorMessage(action.error)} />}

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom>Details</Typography>
            <Stack spacing={1.2}>
              <Stack direction="row" justifyContent="space-between"><span>Status</span><StatusChip status={c.status} /></Stack>
              <Stack direction="row" justifyContent="space-between"><span>Type</span><b>{c.type.replace(/_/g, ' ')}</b></Stack>
              <Stack direction="row" justifyContent="space-between"><span>Channel</span><b>{c.channel ?? '—'}</b></Stack>
              <Stack direction="row" justifyContent="space-between"><span>Scheduled</span><b>{c.scheduled_at ? new Date(c.scheduled_at).toLocaleString() : '—'}</b></Stack>
              <Stack direction="row" justifyContent="space-between"><span>Timezone</span><b>{c.timezone}</b></Stack>
            </Stack>
            {c.rejection_reason && <Typography color="error" sx={{ mt: 2 }}>Rejected: {c.rejection_reason}</Typography>}
            {canEdit && c.status === 'pending_approval' && (
              <TextField sx={{ mt: 2 }} fullWidth size="small" label="Rejection reason"
                value={reason} onChange={(e) => setReason(e.target.value)} />
            )}
          </CardContent></Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom>Performance</Typography>
            <Divider sx={{ mb: 2 }} />
            <Grid container spacing={2}>
              <Metric label="Sent" value={m?.sent ?? 0} />
              <Metric label="Delivered" value={m?.delivered ?? 0} />
              <Metric label="Opened" value={m?.opened ?? 0} />
              <Metric label="Clicked" value={m?.clicked ?? 0} />
              <Metric label="Delivery Rate" value={`${Math.round((m?.delivery_rate ?? 0) * 100)}%`} />
              <Metric label="Open Rate" value={`${Math.round((m?.open_rate ?? 0) * 100)}%`} />
              <Metric label="Click Rate" value={`${Math.round((m?.click_rate ?? 0) * 100)}%`} />
              <Metric label="Bounced" value={m?.bounced ?? 0} />
            </Grid>
          </CardContent></Card>
        </Grid>
      </Grid>
    </Box>
  );
}
