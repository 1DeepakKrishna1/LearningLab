import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Skeleton,
  Alert,
  Tabs,
  Tab,
  Tooltip,
  Divider,
  LinearProgress,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import StorageIcon from '@mui/icons-material/Storage';
import InsightsTwoToneIcon from '@mui/icons-material/InsightsTwoTone';
import TableViewIcon from '@mui/icons-material/TableView';
import RefreshIcon from '@mui/icons-material/Refresh';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import DataUpload from '../components/DataUpload/DataUpload';
import MetadataView from '../components/Metadata/MetadataView';
import DataTable from '../components/DataTable/DataTable';
import { useDatasets, useDataset } from '../hooks/useDatasets';
import type { DatasetListItem, Dataset } from '../types';
import { formatDate, formatFileSize, formatRelativeTime } from '../utils/format';

// ─── Status Chip ──────────────────────────────────────────────────────────────

const StatusChip: React.FC<{ status: DatasetListItem['status'] }> = ({ status }) => {
  const config = {
    ready: { label: 'Ready', color: 'success' as const },
    processing: { label: 'Processing', color: 'warning' as const },
    uploading: { label: 'Uploading', color: 'info' as const },
    error: { label: 'Error', color: 'error' as const },
  };
  const c = config[status] || { label: status, color: 'default' as const };
  return (
    <Chip
      label={c.label}
      size="small"
      color={c.color}
      variant="filled"
      sx={{ fontWeight: 600, fontSize: '0.75rem' }}
    />
  );
};

// ─── Dataset Card ─────────────────────────────────────────────────────────────

interface DatasetCardProps {
  dataset: DatasetListItem;
  onView: (dataset: DatasetListItem) => void;
  onDelete: (dataset: DatasetListItem) => void;
  onQuery: (dataset: DatasetListItem) => void;
}

const DatasetCard: React.FC<DatasetCardProps> = ({ dataset, onView, onDelete, onQuery }) => (
  <Card
    sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      cursor: 'pointer',
      '&:hover': { transform: 'translateY(-2px)', transition: 'transform 0.15s ease' },
      transition: 'transform 0.15s ease',
    }}
    onClick={() => onView(dataset)}
  >
    <CardContent sx={{ flexGrow: 1, p: 2.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
          <StorageIcon sx={{ color: 'primary.main', flexShrink: 0 }} />
          <Typography
            variant="subtitle1"
            fontWeight={700}
            sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {dataset.name}
          </Typography>
        </Box>
        <StatusChip status={dataset.status} />
      </Box>

      <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
        {dataset.filename}
      </Typography>

      {dataset.status === 'processing' && (
        <LinearProgress sx={{ mb: 1.5, height: 4, borderRadius: 2 }} />
      )}

      <Grid container spacing={1}>
        {[
          { label: 'Rows', value: (dataset.row_count ?? 0).toLocaleString() },
          { label: 'Columns', value: dataset.column_count },
          { label: 'Size', value: formatFileSize(dataset.file_size) },
          { label: 'Type', value: dataset.file_type?.toUpperCase() || '—' },
        ].map(({ label, value }) => (
          <Grid item xs={6} key={label}>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {value}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </CardContent>

    <Divider />

    <CardActions sx={{ px: 2, py: 1.25, justifyContent: 'space-between' }}>
      <Typography variant="caption" color="text.secondary">
        {formatRelativeTime(dataset.created_at)}
      </Typography>
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        <Tooltip title="Query this dataset">
          <IconButton
            size="small"
            color="primary"
            onClick={(e) => { e.stopPropagation(); onQuery(dataset); }}
            disabled={dataset.status !== 'ready'}
          >
            <InsightsTwoToneIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Delete dataset">
          <IconButton
            size="small"
            color="error"
            onClick={(e) => { e.stopPropagation(); onDelete(dataset); }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </CardActions>
  </Card>
);

// ─── Dataset Detail Dialog ────────────────────────────────────────────────────

interface DatasetDetailDialogProps {
  datasetItem: DatasetListItem | null;
  onClose: () => void;
  onDelete: (dataset: DatasetListItem) => void;
  onQuery: (id: string) => void;
}

const DatasetDetailDialog: React.FC<DatasetDetailDialogProps> = ({
  datasetItem,
  onClose,
  onDelete,
  onQuery,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const { dataset, loading } = useDataset(datasetItem?.id ?? null);

  if (!datasetItem) return null;

  return (
    <Dialog
      open={Boolean(datasetItem)}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{ sx: { borderRadius: 3, height: '80vh' } }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5, pb: 1 }}>
        <StorageIcon color="primary" />
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" fontWeight={700}>
            {datasetItem.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {datasetItem.filename} · {formatFileSize(datasetItem.file_size)} · Created{' '}
            {formatDate(datasetItem.created_at)}
          </Typography>
        </Box>
        <StatusChip status={datasetItem.status} />
      </DialogTitle>

      <Box sx={{ px: 3 }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
          <Tab label="Column Metadata" icon={<InsightsTwoToneIcon />} iconPosition="start" />
          <Tab
            label="Preview Data"
            icon={<TableViewIcon />}
            iconPosition="start"
            disabled={!dataset?.preview_data}
          />
        </Tabs>
      </Box>

      <Divider />

      <DialogContent sx={{ p: 3, overflow: 'auto' }}>
        {loading ? (
          <Box>
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} height={80} sx={{ mb: 1, borderRadius: 2 }} />
            ))}
          </Box>
        ) : dataset ? (
          <>
            {activeTab === 0 && <MetadataView dataset={dataset} />}
            {activeTab === 1 && dataset.preview_data && (
              <DataTable
                columns={dataset.columns.map((c) => ({ name: c.name, dtype: c.dtype }))}
                data={dataset.preview_data}
                compact
                showExport={false}
              />
            )}
          </>
        ) : (
          <Alert severity="error">Failed to load dataset details</Alert>
        )}
      </DialogContent>

      <Divider />

      <DialogActions sx={{ px: 3, py: 2, gap: 1 }}>
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteOutlineIcon />}
          onClick={() => { onClose(); onDelete(datasetItem); }}
        >
          Delete
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          startIcon={<OpenInNewIcon />}
          onClick={() => { onClose(); onQuery(datasetItem.id); }}
          disabled={datasetItem.status !== 'ready'}
        >
          Query Dataset
        </Button>
      </DialogActions>
    </Dialog>
  );
};

// ─── Main Page ─────────────────────────────────────────────────────────────────

const DatasetsPage: React.FC = () => {
  const navigate = useNavigate();
  const { datasets, loading, error, refresh, deleteDataset } = useDatasets();

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [detailDataset, setDetailDataset] = useState<DatasetListItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DatasetListItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleUploadSuccess = (dataset: Dataset) => {
    setUploadDialogOpen(false);
    refresh();
    navigate(`/query?dataset=${dataset.id}`);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteDataset(deleteTarget.id);
      setDeleteTarget(null);
    } catch {
      // error handled in hook
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 3,
          flexWrap: 'wrap',
          gap: 1,
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Datasets
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {datasets.length} dataset{datasets.length !== 1 ? 's' : ''} available
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={refresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<CloudUploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Upload Dataset
          </Button>
        </Box>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} action={<Button size="small" onClick={refresh}>Retry</Button>}>
          {error}
        </Alert>
      )}

      {/* Content */}
      {loading ? (
        <Grid container spacing={2.5}>
          {[...Array(6)].map((_, i) => (
            <Grid item xs={12} sm={6} md={4} key={i}>
              <Skeleton variant="rectangular" height={220} sx={{ borderRadius: 3 }} />
            </Grid>
          ))}
        </Grid>
      ) : datasets.length === 0 ? (
        <Box
          sx={{
            textAlign: 'center',
            py: 10,
            border: '2px dashed',
            borderColor: 'divider',
            borderRadius: 3,
          }}
        >
          <StorageIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No datasets yet
          </Typography>
          <Typography variant="body2" color="text.disabled" mb={3}>
            Upload a CSV or Excel file to get started with NLP queries
          </Typography>
          <Button
            variant="contained"
            startIcon={<CloudUploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
            size="large"
          >
            Upload Your First Dataset
          </Button>
        </Box>
      ) : (
        <Grid container spacing={2.5}>
          {datasets.map((dataset) => (
            <Grid item xs={12} sm={6} md={4} key={dataset.id}>
              <DatasetCard
                dataset={dataset}
                onView={setDetailDataset}
                onDelete={setDeleteTarget}
                onQuery={(d) => navigate(`/query?dataset=${d.id}`)}
              />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Upload Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle>Upload New Dataset</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <DataUpload
            onSuccess={handleUploadSuccess}
            onClose={() => setUploadDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <DatasetDetailDialog
        datasetItem={detailDataset}
        onClose={() => setDetailDataset(null)}
        onDelete={setDeleteTarget}
        onQuery={(id) => navigate(`/query?dataset=${id}`)}
      />

      {/* Delete Confirm Dialog */}
      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle>Delete Dataset</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete <strong>"{deleteTarget?.name}"</strong>? This action
            cannot be undone. All associated queries and widgets referencing this dataset may break.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DatasetsPage;
