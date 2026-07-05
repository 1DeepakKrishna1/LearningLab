import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Paper, Typography, Button, IconButton, Tooltip,
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, Select, FormControl, InputLabel,
  Chip, CircularProgress, Alert, Skeleton, Card, CardContent,
  CardActions, Snackbar, Divider, List, ListItem, ListItemText,
  Accordion, AccordionSummary, AccordionDetails, LinearProgress,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import AssessmentIcon from '@mui/icons-material/Assessment';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import TableChartIcon from '@mui/icons-material/TableChart';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import RefreshIcon from '@mui/icons-material/Refresh';

import { useDatasets } from '../hooks/useDatasets';
import {
  getReports, getReport, createReport, generateReport,
  deleteReport, exportReportCSV, exportReportPDF, downloadBlob,
} from '../services/api';
import type { Report } from '../types';

const STATUS_COLOR: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  draft: 'default',
  generating: 'warning',
  ready: 'success',
  error: 'error',
};

const SECTION_TYPES = ['summary', 'table', 'chart', 'stats', 'text'];

interface SectionDraft {
  title: string;
  section_type: string;
  sql_query: string;
  order_index: number;
}

const ReportsPage: React.FC = () => {
  const { datasets } = useDatasets();
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  // Dialogs
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Create form
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDatasetId, setNewDatasetId] = useState('');
  const [sections, setSections] = useState<SectionDraft[]>([
    { title: 'Summary Statistics', section_type: 'summary', sql_query: '', order_index: 0 },
    { title: 'Data Overview', section_type: 'table', sql_query: '', order_index: 1 },
  ]);
  const [creating, setCreating] = useState(false);

  // Generating / exporting
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);

  const readyDatasets = datasets.filter((d) => d.status === 'ready');

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getReports();
      setReports(data as unknown as Report[]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  // Auto-fill SQL queries when dataset changes
  useEffect(() => {
    if (!newDatasetId) return;
    const ds = datasets.find((d) => d.id === newDatasetId);
    if (!ds) return;
    setSections((prev) =>
      prev.map((s) => ({
        ...s,
        sql_query: s.sql_query || `SELECT * FROM "${newDatasetId.replace(/-/g, '')}" LIMIT 100`,
      }))
    );
  }, [newDatasetId, datasets]);

  const handleCreate = async () => {
    if (!newTitle.trim() || !newDatasetId) return;
    setCreating(true);
    try {
      const payload = {
        dataset_id: newDatasetId,
        title: newTitle,
        description: newDesc || undefined,
        sections: sections
          .filter((s) => s.title.trim())
          .map((s, i) => ({ ...s, order_index: i })),
      };
      const report = await createReport(payload as any);
      setSnackbar('Report created');
      setCreateOpen(false);
      resetCreateForm();
      await fetchReports();
      setSelectedReport(report as unknown as Report);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const resetCreateForm = () => {
    setNewTitle(''); setNewDesc(''); setNewDatasetId('');
    setSections([
      { title: 'Summary Statistics', section_type: 'summary', sql_query: '', order_index: 0 },
      { title: 'Data Overview', section_type: 'table', sql_query: '', order_index: 1 },
    ]);
  };

  const handleGenerate = async (reportId: string) => {
    setGeneratingId(reportId);
    try {
      const updated = await generateReport(reportId, {} as any);
      setSnackbar('Report generated');
      setReports((prev) => prev.map((r) => (r.id === reportId ? (updated as unknown as Report) : r)));
      if (selectedReport?.id === reportId) setSelectedReport(updated as unknown as Report);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGeneratingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteReport(deleteId);
      setSnackbar('Report deleted');
      setReports((prev) => prev.filter((r) => r.id !== deleteId));
      if (selectedReport?.id === deleteId) setSelectedReport(null);
      setDeleteId(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleExportCSV = async (reportId: string) => {
    setExportingId(reportId);
    try {
      const blob = await exportReportCSV(reportId);
      downloadBlob(blob, `report_${reportId}.csv`);
      setSnackbar('CSV exported');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setExportingId(null);
    }
  };

  const handleExportPDF = async (reportId: string) => {
    setExportingId(reportId);
    try {
      const blob = await exportReportPDF(reportId);
      downloadBlob(blob, `report_${reportId}.pdf`);
      setSnackbar('PDF exported');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setExportingId(null);
    }
  };

  const openReport = async (id: string) => {
    try {
      const r = await getReport(id);
      setSelectedReport(r as unknown as Report);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2, flexWrap: 'wrap' }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" fontWeight={700}>Reports</Typography>
          <Typography variant="body2" color="text.secondary">
            Generate tabular and chart-based reports, export to CSV or PDF
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchReports}>Refresh</Button>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
          New Report
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Grid container spacing={3}>
        {/* Report list */}
        <Grid item xs={12} md={selectedReport ? 4 : 12}>
          {loading ? (
            <Grid container spacing={2}>
              {[1, 2, 3].map((i) => (
                <Grid item xs={12} sm={selectedReport ? 12 : 4} key={i}>
                  <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 2 }} />
                </Grid>
              ))}
            </Grid>
          ) : reports.length === 0 ? (
            <Paper sx={{ p: 8, textAlign: 'center', border: '2px dashed', borderColor: 'divider', backgroundColor: 'transparent' }}>
              <AssessmentIcon sx={{ fontSize: 56, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>No reports yet</Typography>
              <Typography variant="body2" color="text.disabled" sx={{ mb: 3 }}>
                Create a report to analyse and export dataset insights.
              </Typography>
              <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
                Create Report
              </Button>
            </Paper>
          ) : (
            <Grid container spacing={2}>
              {reports.map((r) => (
                <Grid item xs={12} sm={selectedReport ? 12 : 6} md={selectedReport ? 12 : 4} key={r.id}>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      border: selectedReport?.id === r.id ? '2px solid' : '1px solid',
                      borderColor: selectedReport?.id === r.id ? 'primary.main' : 'divider',
                    }}
                    onClick={() => openReport(r.id)}
                  >
                    <CardContent sx={{ pb: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                        <AssessmentIcon color="primary" sx={{ mr: 1, mt: 0.2 }} />
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="subtitle2" fontWeight={600} noWrap>{(r as any).title || r.name}</Typography>
                          {(r as any).description && (
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {(r as any).description}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                        <Chip
                          label={(r as any).status || 'draft'}
                          size="small"
                          color={STATUS_COLOR[(r as any).status || 'draft']}
                        />
                        <Chip
                          label={`${(r as any).sections?.length || 0} sections`}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                    </CardContent>
                    <CardActions sx={{ pt: 0, gap: 0.5 }}>
                      {(r as any).status !== 'ready' && (
                        <Tooltip title="Generate report">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={(e) => { e.stopPropagation(); handleGenerate(r.id); }}
                            disabled={generatingId === r.id}
                          >
                            {generatingId === r.id ? <CircularProgress size={16} /> : <PlayArrowIcon fontSize="small" />}
                          </IconButton>
                        </Tooltip>
                      )}
                      {(r as any).status === 'ready' && (
                        <>
                          <Tooltip title="Export CSV">
                            <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleExportCSV(r.id); }} disabled={exportingId === r.id}>
                              <TableChartIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Export PDF">
                            <IconButton size="small" color="error" onClick={(e) => { e.stopPropagation(); handleExportPDF(r.id); }} disabled={exportingId === r.id}>
                              <PictureAsPdfIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                      <Box sx={{ flexGrow: 1 }} />
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={(e) => { e.stopPropagation(); setDeleteId(r.id); }}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Grid>

        {/* Report detail */}
        {selectedReport && (
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
                <Typography variant="h6" fontWeight={700} sx={{ flexGrow: 1 }}>
                  {(selectedReport as any).title || selectedReport.name}
                </Typography>
                <Chip label={(selectedReport as any).status || 'draft'} color={STATUS_COLOR[(selectedReport as any).status || 'draft']} />
                {(selectedReport as any).status !== 'ready' && (
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={generatingId === selectedReport.id ? <CircularProgress size={14} /> : <PlayArrowIcon />}
                    onClick={() => handleGenerate(selectedReport.id)}
                    disabled={generatingId === selectedReport.id}
                  >
                    Generate
                  </Button>
                )}
                {(selectedReport as any).status === 'ready' && (
                  <>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<TableChartIcon />}
                      onClick={() => handleExportCSV(selectedReport.id)}
                      disabled={exportingId === selectedReport.id}
                    >
                      CSV
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<PictureAsPdfIcon />}
                      onClick={() => handleExportPDF(selectedReport.id)}
                      disabled={exportingId === selectedReport.id}
                    >
                      PDF
                    </Button>
                  </>
                )}
              </Box>

              {(selectedReport as any).description && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {(selectedReport as any).description}
                </Typography>
              )}
              <Divider sx={{ mb: 2 }} />

              {(selectedReport as any).sections?.length === 0 ? (
                <Typography variant="body2" color="text.secondary">No sections defined.</Typography>
              ) : (
                (selectedReport as any).sections?.map((section: any) => (
                  <Accordion key={section.id} sx={{ mb: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                        <Typography variant="subtitle2" fontWeight={600}>{section.title}</Typography>
                        <Chip label={section.section_type} size="small" variant="outlined" />
                        {section.content?.rows && (
                          <Chip label={`${section.content.rows.length} rows`} size="small" color="primary" />
                        )}
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      {section.content?.rows?.length > 0 ? (
                        <Box sx={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                            <thead>
                              <tr style={{ backgroundColor: '#f8fafc' }}>
                                {Object.keys(section.content.rows[0]).map((k) => (
                                  <th key={k} style={{ padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid #e2e8f0', fontWeight: 600 }}>
                                    {k}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {section.content.rows.slice(0, 20).map((row: any, i: number) => (
                                <tr key={i} style={{ backgroundColor: i % 2 === 0 ? 'white' : '#f8fafc' }}>
                                  {Object.values(row).map((v: any, j: number) => (
                                    <td key={j} style={{ padding: '6px 12px', borderBottom: '1px solid #f1f5f9' }}>
                                      {v === null || v === undefined ? '—' : String(v)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {section.content.rows.length > 20 && (
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                              Showing 20 of {section.content.rows.length} rows. Export for full data.
                            </Typography>
                          )}
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          {(selectedReport as any).status === 'ready' ? 'No data for this section.' : 'Generate the report to populate data.'}
                        </Typography>
                      )}
                    </AccordionDetails>
                  </Accordion>
                ))
              )}
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* Create Report Dialog */}
      <Dialog open={createOpen} onClose={() => { setCreateOpen(false); resetCreateForm(); }} maxWidth="md" fullWidth>
        <DialogTitle>Create Report</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} sm={8}>
              <TextField fullWidth label="Report Title *" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Dataset *</InputLabel>
                <Select value={newDatasetId} onChange={(e) => setNewDatasetId(e.target.value)} label="Dataset *">
                  {readyDatasets.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth label="Description" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} multiline rows={2} />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
                Sections
              </Typography>
              {sections.map((s, i) => (
                <Paper key={i} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
                  <Grid container spacing={1} alignItems="center">
                    <Grid item xs={4}>
                      <TextField
                        fullWidth size="small" label="Title"
                        value={s.title}
                        onChange={(e) => setSections((prev) => prev.map((x, j) => j === i ? { ...x, title: e.target.value } : x))}
                      />
                    </Grid>
                    <Grid item xs={3}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Type</InputLabel>
                        <Select
                          value={s.section_type}
                          onChange={(e) => setSections((prev) => prev.map((x, j) => j === i ? { ...x, section_type: e.target.value } : x))}
                          label="Type"
                        >
                          {SECTION_TYPES.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={4}>
                      <TextField
                        fullWidth size="small" label="SQL Query (optional)"
                        value={s.sql_query}
                        onChange={(e) => setSections((prev) => prev.map((x, j) => j === i ? { ...x, sql_query: e.target.value } : x))}
                        placeholder="SELECT * FROM ..."
                      />
                    </Grid>
                    <Grid item xs={1}>
                      <IconButton size="small" color="error" onClick={() => setSections((prev) => prev.filter((_, j) => j !== i))}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Grid>
                  </Grid>
                </Paper>
              ))}
              <Button
                size="small"
                startIcon={<AddIcon />}
                onClick={() => setSections((prev) => [...prev, { title: '', section_type: 'table', sql_query: '', order_index: prev.length }])}
              >
                Add Section
              </Button>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setCreateOpen(false); resetCreateForm(); }}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!newTitle.trim() || !newDatasetId || creating}
            startIcon={creating ? <CircularProgress size={16} /> : undefined}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={!!deleteId} onClose={() => setDeleteId(null)} maxWidth="xs">
        <DialogTitle>Delete Report?</DialogTitle>
        <DialogContent><Typography>This action cannot be undone.</Typography></DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar(null)} message={snackbar} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} />
    </Box>
  );
};

export default ReportsPage;
