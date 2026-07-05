import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Grid, Paper, Typography, Button, IconButton, Tooltip,
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, Select, FormControl, InputLabel,
  Chip, CircularProgress, Alert, Skeleton, Card, CardContent,
  CardActionArea, CardActions, Snackbar, Divider,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import DashboardIcon from '@mui/icons-material/Dashboard';
import GridViewIcon from '@mui/icons-material/GridView';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';

import ChartRenderer from '../components/Charts/ChartRenderer';
import DataTable from '../components/DataTable/DataTable';
import { useDatasets } from '../hooks/useDatasets';
import {
  getDashboards, getDashboard, createDashboard, deleteDashboard,
  generateDashboardFromNLP, deleteReport,
} from '../services/api';
import type { Dashboard, DashboardListItem, ChartType } from '../types';

// Widget data fetched from the backend
interface WidgetData {
  widgetId: string;
  data: Record<string, unknown>[];
  loading: boolean;
  error?: string;
}

const DashboardPage: React.FC = () => {
  const { id: routeId } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { datasets } = useDatasets();

  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);
  const [activeDashboard, setActiveDashboard] = useState<Dashboard | null>(null);
  const [widgetData, setWidgetData] = useState<Record<string, WidgetData>>({});
  const [loading, setLoading] = useState(true);
  const [dashLoading, setDashLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  // Dialogs
  const [createOpen, setCreateOpen] = useState(false);
  const [nlpOpen, setNlpOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Create form
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDatasetId, setNewDatasetId] = useState('');
  const [creating, setCreating] = useState(false);

  // NLP form
  const [nlpPrompt, setNlpPrompt] = useState('');
  const [nlpDatasetId, setNlpDatasetId] = useState('');
  const [nlpName, setNlpName] = useState('');
  const [nlpLoading, setNlpLoading] = useState(false);

  const readyDatasets = datasets.filter((d) => d.status === 'ready');

  const fetchDashboards = useCallback(async () => {
    try {
      const list = await getDashboards();
      setDashboards(list as unknown as DashboardListItem[]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDashboards(); }, [fetchDashboards]);

  useEffect(() => {
    if (routeId) loadDashboard(routeId);
  }, [routeId]);

  const loadDashboard = async (id: string) => {
    setDashLoading(true);
    setWidgetData({});
    try {
      const dash = await getDashboard(id);
      setActiveDashboard(dash as unknown as Dashboard);
      // Fetch data for each widget
      dash.widgets?.forEach((w: any) => fetchWidgetData(w));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDashLoading(false);
    }
  };

  const fetchWidgetData = async (widget: any) => {
    setWidgetData((prev) => ({ ...prev, [widget.id]: { widgetId: widget.id, data: [], loading: true } }));
    try {
      const res = await fetch(`http://localhost:8000/api/v1/dashboards/${widget.dashboard_id}/widgets/${widget.id}/data`, { method: 'POST' });
      const json = await res.json();
      setWidgetData((prev) => ({
        ...prev,
        [widget.id]: { widgetId: widget.id, data: json.data || [], loading: false },
      }));
    } catch (err: any) {
      setWidgetData((prev) => ({
        ...prev,
        [widget.id]: { widgetId: widget.id, data: [], loading: false, error: err.message },
      }));
    }
  };

  const handleCreateDashboard = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const dash = await createDashboard({ name: newName, description: newDesc || undefined, dataset_id: newDatasetId || undefined } as any);
      setSnackbar('Dashboard created');
      setCreateOpen(false);
      setNewName(''); setNewDesc(''); setNewDatasetId('');
      await fetchDashboards();
      navigate(`/dashboards/${(dash as any).id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleGenerateNLP = async () => {
    if (!nlpPrompt.trim() || !nlpDatasetId) return;
    setNlpLoading(true);
    try {
      const dash = await generateDashboardFromNLP(nlpPrompt, nlpDatasetId, nlpName || undefined);
      setSnackbar('Dashboard generated successfully');
      setNlpOpen(false);
      setNlpPrompt(''); setNlpDatasetId(''); setNlpName('');
      await fetchDashboards();
      navigate(`/dashboards/${(dash as any).id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setNlpLoading(false);
    }
  };

  const handleDeleteDashboard = async () => {
    if (!deleteId) return;
    try {
      await deleteDashboard(deleteId);
      setSnackbar('Dashboard deleted');
      setDeleteId(null);
      if (activeDashboard?.id === deleteId) {
        setActiveDashboard(null);
        navigate('/dashboards');
      }
      await fetchDashboards();
    } catch (err: any) {
      setError(err.message);
    }
  };

  // ── Dashboard list view ──────────────────────────────────────────────────
  if (!routeId) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h4" fontWeight={700}>Dashboards</Typography>
            <Typography variant="body2" color="text.secondary">
              Create and manage interactive data dashboards
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={<AutoAwesomeIcon />}
            onClick={() => setNlpOpen(true)}
          >
            Generate with AI
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateOpen(true)}
          >
            New Dashboard
          </Button>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

        {loading ? (
          <Grid container spacing={2}>
            {[1, 2, 3].map((i) => (
              <Grid item xs={12} sm={6} md={4} key={i}>
                <Skeleton variant="rectangular" height={160} sx={{ borderRadius: 2 }} />
              </Grid>
            ))}
          </Grid>
        ) : dashboards.length === 0 ? (
          <Paper sx={{ p: 8, textAlign: 'center', border: '2px dashed', borderColor: 'divider', backgroundColor: 'transparent' }}>
            <GridViewIcon sx={{ fontSize: 56, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>No dashboards yet</Typography>
            <Typography variant="body2" color="text.disabled" sx={{ mb: 3 }}>
              Create one manually or let AI generate it from a prompt.
            </Typography>
            <Button variant="contained" startIcon={<AutoAwesomeIcon />} onClick={() => setNlpOpen(true)}>
              Generate with AI
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={2}>
            {dashboards.map((d) => (
              <Grid item xs={12} sm={6} md={4} key={d.id}>
                <Card sx={{ height: '100%' }}>
                  <CardActionArea onClick={() => navigate(`/dashboards/${d.id}`)} sx={{ p: 2, pb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1 }}>
                      <DashboardIcon color="primary" />
                      <Typography variant="h6" fontWeight={600} noWrap>{d.name}</Typography>
                    </Box>
                    {(d as any).description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }} noWrap>
                        {(d as any).description}
                      </Typography>
                    )}
                    <Typography variant="caption" color="text.secondary">
                      {new Date((d as any).created_at).toLocaleDateString()}
                    </Typography>
                  </CardActionArea>
                  <CardActions sx={{ pt: 0, justifyContent: 'flex-end' }}>
                    <Tooltip title="Delete">
                      <IconButton size="small" color="error" onClick={() => setDeleteId(d.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {/* Create Dialog */}
        <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
          <DialogTitle>New Dashboard</DialogTitle>
          <DialogContent>
            <TextField fullWidth label="Name" value={newName} onChange={(e) => setNewName(e.target.value)} sx={{ mb: 2, mt: 1 }} />
            <TextField fullWidth label="Description (optional)" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} sx={{ mb: 2 }} multiline rows={2} />
            <FormControl fullWidth>
              <InputLabel>Dataset (optional)</InputLabel>
              <Select value={newDatasetId} onChange={(e) => setNewDatasetId(e.target.value)} label="Dataset (optional)">
                <MenuItem value=""><em>None</em></MenuItem>
                {readyDatasets.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
              </Select>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleCreateDashboard} disabled={!newName.trim() || creating}>
              {creating ? <CircularProgress size={16} /> : 'Create'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* NLP Generate Dialog */}
        <Dialog open={nlpOpen} onClose={() => setNlpOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AutoAwesomeIcon color="primary" /> Generate Dashboard with AI
          </DialogTitle>
          <DialogContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Describe the dashboard you want. AI will auto-create widgets and queries.
            </Typography>
            <TextField
              fullWidth multiline rows={3}
              label="Describe your dashboard"
              placeholder='e.g. "Create a sales performance dashboard with trends, top products, and revenue breakdown"'
              value={nlpPrompt}
              onChange={(e) => setNlpPrompt(e.target.value)}
              sx={{ mb: 2 }}
            />
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Dataset *</InputLabel>
              <Select value={nlpDatasetId} onChange={(e) => setNlpDatasetId(e.target.value)} label="Dataset *">
                {readyDatasets.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
              </Select>
            </FormControl>
            <TextField fullWidth label="Dashboard name (optional)" value={nlpName} onChange={(e) => setNlpName(e.target.value)} />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setNlpOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleGenerateNLP}
              disabled={!nlpPrompt.trim() || !nlpDatasetId || nlpLoading}
              startIcon={nlpLoading ? <CircularProgress size={16} /> : <AutoAwesomeIcon />}
            >
              Generate
            </Button>
          </DialogActions>
        </Dialog>

        {/* Delete confirm */}
        <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} maxWidth="xs">
          <DialogTitle>Delete Dashboard?</DialogTitle>
          <DialogContent><Typography>This action cannot be undone.</Typography></DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button variant="contained" color="error" onClick={handleDeleteDashboard}>Delete</Button>
          </DialogActions>
        </Dialog>

        <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar(null)} message={snackbar} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} />
      </Box>
    );
  }

  // ── Single dashboard view ────────────────────────────────────────────────
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <Tooltip title="Back to dashboards">
          <IconButton onClick={() => navigate('/dashboards')} size="small">
            <ArrowBackIcon />
          </IconButton>
        </Tooltip>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" fontWeight={700}>
            {activeDashboard?.name || <Skeleton width={200} />}
          </Typography>
          {activeDashboard && (activeDashboard as any).description && (
            <Typography variant="body2" color="text.secondary">{(activeDashboard as any).description}</Typography>
          )}
        </Box>
        <Tooltip title="Refresh widgets">
          <IconButton size="small" onClick={() => routeId && loadDashboard(routeId)} disabled={dashLoading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Delete dashboard">
          <IconButton size="small" color="error" onClick={() => activeDashboard && setDeleteId(activeDashboard.id)}>
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {dashLoading ? (
        <Grid container spacing={2}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={12} md={6} key={i}>
              <Skeleton variant="rectangular" height={280} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
      ) : activeDashboard && (activeDashboard as any).widgets?.length > 0 ? (
        <Grid container spacing={2}>
          {(activeDashboard as any).widgets.map((widget: any) => {
            const wData = widgetData[widget.id];
            return (
              <Grid
                item
                xs={12}
                md={widget.grid_w <= 6 ? 6 : 12}
                key={widget.id}
              >
                <Paper sx={{ p: 2, height: 320, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2" fontWeight={600} sx={{ flexGrow: 1 }} noWrap>
                      {widget.title}
                    </Typography>
                    <Chip label={widget.chart_type} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                  </Box>
                  <Divider sx={{ mb: 1.5 }} />
                  <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                    {!wData || wData.loading ? (
                      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                        <CircularProgress size={32} />
                      </Box>
                    ) : wData.error ? (
                      <Alert severity="warning" sx={{ fontSize: '0.8rem' }}>{wData.error}</Alert>
                    ) : wData.data.length === 0 ? (
                      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                        <Typography variant="body2" color="text.disabled">No data</Typography>
                      </Box>
                    ) : widget.chart_type === 'table' ? (
                      <DataTable
                        data={wData.data}
                        columns={Object.keys(wData.data[0] || {}).map((k) => ({ name: k, dtype: 'text' }))}
                        compact
                      />
                    ) : (
                      <ChartRenderer
                        chartType={widget.chart_type as ChartType}
                        data={wData.data}
                      />
                    )}
                  </Box>
                </Paper>
              </Grid>
            );
          })}
        </Grid>
      ) : activeDashboard ? (
        <Paper sx={{ p: 8, textAlign: 'center', border: '2px dashed', borderColor: 'divider', backgroundColor: 'transparent' }}>
          <Typography variant="h6" color="text.secondary">No widgets yet</Typography>
          <Typography variant="body2" color="text.disabled">
            Widgets can be added via the query page or by editing this dashboard's definition.
          </Typography>
        </Paper>
      ) : null}

      {/* Delete confirm */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} maxWidth="xs">
        <DialogTitle>Delete Dashboard?</DialogTitle>
        <DialogContent><Typography>This action cannot be undone.</Typography></DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDeleteDashboard}>Delete</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar(null)} message={snackbar} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} />
    </Box>
  );
};

export default DashboardPage;
