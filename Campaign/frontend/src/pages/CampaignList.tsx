import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Box, Button, Card, IconButton, MenuItem, Stack, TextField, Tooltip,
} from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { useCampaigns, useCampaignAction, useDeleteCampaign } from '../api/hooks';
import { PageHeader, StatusChip, ErrorState, ConfirmDialog } from '../components/shared';
import { useAuth } from '../store/auth';
import { apiErrorMessage } from '../api/client';

const STATUSES = ['draft', 'pending_approval', 'approved', 'scheduled', 'sending',
  'completed', 'failed', 'paused', 'cancelled', 'archived'];

export default function CampaignList() {
  const [status, setStatus] = useState('');
  const [q, setQ] = useState('');
  const [toDelete, setToDelete] = useState<number | null>(null);
  const navigate = useNavigate();
  const canEdit = useAuth((s) => s.hasRole('admin', 'marketer'));

  const { data, isLoading, error } = useCampaigns({ status: status || undefined, q: q || undefined, page_size: 100 });
  const action = useCampaignAction();
  const del = useDeleteCampaign();

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 180 },
    { field: 'type', headerName: 'Type', width: 130, valueFormatter: (v) => String(v).replace(/_/g, ' ') },
    { field: 'channel', headerName: 'Channel', width: 100 },
    { field: 'status', headerName: 'Status', width: 150, renderCell: (p) => <StatusChip status={p.value} /> },
    { field: 'updated_at', headerName: 'Updated', width: 170,
      valueFormatter: (v) => v ? new Date(v as string).toLocaleString() : '' },
    {
      field: 'actions', headerName: 'Actions', width: 170, sortable: false, filterable: false,
      renderCell: (p) => (
        <Stack direction="row">
          <Tooltip title="View"><IconButton size="small" component={RouterLink} to={`/campaigns/${p.row.id}`}><VisibilityIcon fontSize="small" /></IconButton></Tooltip>
          {canEdit && <Tooltip title="Edit"><IconButton size="small" onClick={() => navigate(`/campaigns/${p.row.id}/edit`)}><EditIcon fontSize="small" /></IconButton></Tooltip>}
          {canEdit && <Tooltip title="Duplicate"><IconButton size="small" onClick={() => action.mutate({ id: p.row.id, action: 'duplicate' })}><ContentCopyIcon fontSize="small" /></IconButton></Tooltip>}
          {canEdit && <Tooltip title="Delete"><IconButton size="small" color="error" onClick={() => setToDelete(p.row.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>}
        </Stack>
      ),
    },
  ];

  return (
    <Box>
      <PageHeader title="Campaigns" subtitle="Create and manage omnichannel campaigns"
        action={canEdit && <Button component={RouterLink} to="/campaigns/new" variant="contained">New Campaign</Button>} />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <TextField size="small" label="Search" value={q} onChange={(e) => setQ(e.target.value)} sx={{ minWidth: 220 }} />
        <TextField size="small" select label="Status" value={status} onChange={(e) => setStatus(e.target.value)} sx={{ minWidth: 200 }}>
          <MenuItem value="">All</MenuItem>
          {STATUSES.map((s) => <MenuItem key={s} value={s}>{s.replace(/_/g, ' ')}</MenuItem>)}
        </TextField>
      </Stack>
      {error && <ErrorState message={apiErrorMessage(error)} />}
      <Card>
        <DataGrid
          autoHeight rows={data?.items ?? []} columns={columns} loading={isLoading}
          disableRowSelectionOnClick pageSizeOptions={[10, 25, 50]}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
          sx={{ border: 0 }}
        />
      </Card>
      <ConfirmDialog
        open={toDelete !== null} title="Delete campaign?"
        message="This permanently removes the campaign and its deliveries." danger confirmText="Delete"
        onClose={() => setToDelete(null)}
        onConfirm={() => toDelete && del.mutate(toDelete)}
      />
    </Box>
  );
}
