import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert, Box, Button, Card, CardContent, MenuItem, Step, StepLabel, Stepper,
  Stack, TextField, Typography,
} from '@mui/material';
import { useCampaign, useSaveCampaign, useTemplates, useSegments } from '../api/hooks';
import { PageHeader, Loading } from '../components/shared';
import { apiErrorMessage } from '../api/client';
import type { CampaignType, Channel } from '../types';

const STEPS = ['Basics', 'Channel & Template', 'Audience', 'Schedule', 'Review'];

interface Draft {
  name: string; description: string; type: CampaignType; channel: Channel;
  template_id?: number; segment_id?: number; scheduled_at?: string; timezone: string;
}

export default function CampaignBuilder() {
  const { id } = useParams();
  const editing = !!id;
  const navigate = useNavigate();
  const existing = useCampaign(editing ? Number(id) : undefined);
  const save = useSaveCampaign();
  const templates = useTemplates({ page_size: 200 });
  const segments = useSegments();

  const [active, setActive] = useState(0);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState<Draft>({
    name: '', description: '', type: 'one_time', channel: 'email', timezone: 'UTC',
  });

  useEffect(() => {
    if (existing.data) {
      const c = existing.data;
      setDraft({
        name: c.name, description: c.description, type: c.type, channel: c.channel ?? 'email',
        template_id: c.template_id ?? undefined, segment_id: c.segment_id ?? undefined,
        scheduled_at: c.scheduled_at ?? undefined, timezone: c.timezone,
      });
    }
  }, [existing.data]);

  if (editing && existing.isLoading) return <Loading />;

  const set = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }));
  const channelTemplates = (templates.data?.items ?? []).filter((t) => t.channel === draft.channel);

  const submit = async () => {
    setError('');
    try {
      const body = {
        name: draft.name, description: draft.description, type: draft.type, channel: draft.channel,
        template_id: draft.template_id ?? null, segment_id: draft.segment_id ?? null,
        scheduled_at: draft.scheduled_at || null, timezone: draft.timezone, steps: [],
      };
      const saved = await save.mutateAsync({ id: editing ? Number(id) : undefined, body });
      navigate(`/campaigns/${(saved as { id: number }).id}`);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  return (
    <Box>
      <PageHeader title={editing ? 'Edit Campaign' : 'New Campaign'} />
      <Stepper activeStep={active} sx={{ mb: 4 }} alternativeLabel>
        {STEPS.map((s) => <Step key={s}><StepLabel>{s}</StepLabel></Step>)}
      </Stepper>
      <Card>
        <CardContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          {active === 0 && (
            <Stack spacing={2} sx={{ maxWidth: 520 }}>
              <TextField label="Campaign name" value={draft.name} onChange={(e) => set({ name: e.target.value })} required fullWidth />
              <TextField label="Description" value={draft.description} onChange={(e) => set({ description: e.target.value })} multiline rows={2} fullWidth />
              <TextField select label="Type" value={draft.type} onChange={(e) => set({ type: e.target.value as CampaignType })} fullWidth>
                <MenuItem value="one_time">One-Time</MenuItem>
                <MenuItem value="recurring">Recurring</MenuItem>
                <MenuItem value="drip">Drip</MenuItem>
                <MenuItem value="multi_channel">Multi-Channel</MenuItem>
              </TextField>
            </Stack>
          )}

          {active === 1 && (
            <Stack spacing={2} sx={{ maxWidth: 520 }}>
              <TextField select label="Channel" value={draft.channel} onChange={(e) => set({ channel: e.target.value as Channel, template_id: undefined })} fullWidth>
                <MenuItem value="email">Email</MenuItem>
                <MenuItem value="sms">SMS</MenuItem>
                <MenuItem value="push">Push</MenuItem>
              </TextField>
              <TextField select label="Template" value={draft.template_id ?? ''} onChange={(e) => set({ template_id: Number(e.target.value) })} fullWidth
                helperText={channelTemplates.length ? '' : 'No templates for this channel yet — create one in Templates.'}>
                {channelTemplates.map((t) => <MenuItem key={t.id} value={t.id}>{t.name}</MenuItem>)}
              </TextField>
            </Stack>
          )}

          {active === 2 && (
            <Stack spacing={2} sx={{ maxWidth: 520 }}>
              <TextField select label="Segment (audience)" value={draft.segment_id ?? ''} onChange={(e) => set({ segment_id: Number(e.target.value) })} fullWidth
                helperText="Leave empty to target all active contacts.">
                <MenuItem value="">All active contacts</MenuItem>
                {(segments.data ?? []).map((s) => (
                  <MenuItem key={s.id} value={s.id}>{s.name} ({s.cached_count ?? '?'} contacts)</MenuItem>
                ))}
              </TextField>
            </Stack>
          )}

          {active === 3 && (
            <Stack spacing={2} sx={{ maxWidth: 520 }}>
              <TextField type="datetime-local" label="Scheduled at (leave empty for immediate)"
                InputLabelProps={{ shrink: true }} value={draft.scheduled_at?.slice(0, 16) ?? ''}
                onChange={(e) => set({ scheduled_at: e.target.value })} fullWidth />
              <TextField label="Timezone" value={draft.timezone} onChange={(e) => set({ timezone: e.target.value })} fullWidth />
            </Stack>
          )}

          {active === 4 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Review</Typography>
              <Stack spacing={1}>
                <Typography><b>Name:</b> {draft.name}</Typography>
                <Typography><b>Type:</b> {draft.type}</Typography>
                <Typography><b>Channel:</b> {draft.channel}</Typography>
                <Typography><b>Template:</b> {channelTemplates.find((t) => t.id === draft.template_id)?.name ?? '—'}</Typography>
                <Typography><b>Segment:</b> {segments.data?.find((s) => s.id === draft.segment_id)?.name ?? 'All active contacts'}</Typography>
                <Typography><b>Schedule:</b> {draft.scheduled_at || 'Immediate (on send)'}</Typography>
              </Stack>
              <Alert severity="info" sx={{ mt: 2 }}>
                Saving creates the campaign in <b>Draft</b>. Submit it for approval and schedule it from the campaign details page.
              </Alert>
            </Box>
          )}

          <Stack direction="row" justifyContent="space-between" sx={{ mt: 4 }}>
            <Button disabled={active === 0} onClick={() => setActive((a) => a - 1)}>Back</Button>
            {active < STEPS.length - 1 ? (
              <Button variant="contained" disabled={active === 0 && !draft.name} onClick={() => setActive((a) => a + 1)}>Next</Button>
            ) : (
              <Button variant="contained" onClick={submit} disabled={save.isPending}>
                {editing ? 'Save Changes' : 'Create Campaign'}
              </Button>
            )}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
