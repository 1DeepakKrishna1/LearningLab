import { useState } from 'react';
import { Box, Card, TextField } from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import { useAuditLogs } from '../api/hooks';
import { PageHeader, ErrorState } from '../components/shared';
import { apiErrorMessage } from '../api/client';

const columns: GridColDef[] = [
  { field: 'created_at', headerName: 'Time', width: 180, valueFormatter: (v) => v ? new Date(v as string).toLocaleString() : '' },
  { field: 'user_email', headerName: 'User', width: 200 },
  { field: 'action', headerName: 'Action', width: 200 },
  { field: 'entity_type', headerName: 'Entity', width: 130 },
  { field: 'entity_id', headerName: 'ID', width: 90 },
  { field: 'ip_address', headerName: 'IP', width: 140 },
];

export default function AuditLogs() {
  const [action, setAction] = useState('');
  const { data, isLoading, error } = useAuditLogs({ action: action || undefined, page_size: 100 });

  return (
    <Box>
      <PageHeader title="Audit Logs" subtitle="User actions, campaign changes, logins (Admin only)" />
      <TextField size="small" label="Filter by action (e.g. campaign.create)" value={action}
        onChange={(e) => setAction(e.target.value)} sx={{ mb: 2, minWidth: 320 }} />
      {error && <ErrorState message={apiErrorMessage(error)} />}
      <Card>
        <DataGrid autoHeight rows={data?.items ?? []} columns={columns} loading={isLoading}
          disableRowSelectionOnClick pageSizeOptions={[25, 50, 100]}
          initialState={{ pagination: { paginationModel: { pageSize: 25 } } }} sx={{ border: 0 }} />
      </Card>
    </Box>
  );
}
