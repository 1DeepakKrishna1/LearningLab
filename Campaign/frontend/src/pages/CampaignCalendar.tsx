import { Link as RouterLink } from 'react-router-dom';
import { Box, Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import { useCampaigns } from '../api/hooks';
import { PageHeader, Loading, EmptyState, StatusChip } from '../components/shared';

// Lightweight month grouping of scheduled campaigns (no extra calendar dep).
export default function CampaignCalendar() {
  const { data, isLoading } = useCampaigns({ page_size: 200 });
  if (isLoading) return <Loading />;

  const scheduled = (data?.items ?? []).filter((c) => c.scheduled_at || c.next_run_at);
  const byMonth = new Map<string, typeof scheduled>();
  for (const c of scheduled) {
    const d = new Date((c.scheduled_at ?? c.next_run_at)!);
    const key = d.toLocaleString(undefined, { month: 'long', year: 'numeric' });
    byMonth.set(key, [...(byMonth.get(key) ?? []), c]);
  }

  return (
    <Box>
      <PageHeader title="Campaign Calendar" subtitle="Scheduled and recurring sends" />
      {scheduled.length === 0 ? (
        <EmptyState title="No scheduled campaigns" hint="Schedule a campaign to see it here." />
      ) : (
        <Stack spacing={2}>
          {[...byMonth.entries()].map(([month, items]) => (
            <Card key={month}><CardContent>
              <Typography variant="h6" sx={{ mb: 1 }}>{month}</Typography>
              <Stack spacing={1}>
                {items.sort((a, b) => (a.scheduled_at ?? '').localeCompare(b.scheduled_at ?? '')).map((c) => (
                  <Stack key={c.id} direction="row" spacing={2} alignItems="center"
                    component={RouterLink} to={`/campaigns/${c.id}`} sx={{ textDecoration: 'none', color: 'inherit' }}>
                    <Chip size="small" label={new Date((c.scheduled_at ?? c.next_run_at)!).toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })} />
                    <Typography sx={{ flexGrow: 1 }}>{c.name}</Typography>
                    <StatusChip status={c.status} />
                  </Stack>
                ))}
              </Stack>
            </CardContent></Card>
          ))}
        </Stack>
      )}
    </Box>
  );
}
