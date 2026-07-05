import { Box, Button, Card, Chip, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import { useProviders, useProviderHealth } from '../api/hooks';
import { PageHeader, Loading } from '../components/shared';

export default function ProviderConfiguration() {
  const { data, isLoading } = useProviders();
  const health = useProviderHealth();

  if (isLoading) return <Loading />;

  return (
    <Box>
      <PageHeader title="Provider Configuration" subtitle="Email, SMS & push delivery providers" />
      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell><TableCell>Channel</TableCell><TableCell>Type</TableCell>
              <TableCell>Mode</TableCell><TableCell>Default</TableCell><TableCell>Health</TableCell><TableCell /></TableRow>
          </TableHead>
          <TableBody>
            {(data ?? []).map((p) => (
              <TableRow key={p.id} hover>
                <TableCell>{p.name}</TableCell>
                <TableCell><Chip size="small" label={p.channel} /></TableCell>
                <TableCell>{p.provider_type}</TableCell>
                <TableCell><Chip size="small" color={p.mode === 'live' ? 'success' : 'default'} label={p.mode} /></TableCell>
                <TableCell>{p.is_default ? '✓' : ''}</TableCell>
                <TableCell>
                  {p.last_health_status
                    ? <Chip size="small" color={p.last_health_status === 'healthy' ? 'success' : 'error'} label={p.last_health_status} />
                    : <Typography variant="caption" color="text.secondary">unknown</Typography>}
                </TableCell>
                <TableCell align="right">
                  <Button size="small" startIcon={<HealthAndSafetyIcon />} disabled={health.isPending}
                    onClick={() => health.mutate(p.id)}>Check</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
      <Stack sx={{ mt: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Providers default to <b>console</b> (sandbox) mode — messages are logged, not sent, and
          synthetic delivery/open/click events are generated for analytics. To send for real, add
          credentials in <code>data/providers/&lt;type&gt;.json</code> and switch the provider to
          <b> live</b> mode via <code>PATCH /api/v1/providers/&#123;id&#125;</code>.
        </Typography>
      </Stack>
    </Box>
  );
}
