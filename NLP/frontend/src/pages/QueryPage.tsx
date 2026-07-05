import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box, Grid, Paper, Typography, Button, ButtonGroup, Tooltip,
  Chip, Alert, CircularProgress, Collapse, IconButton,
  FormControl, InputLabel, Select, MenuItem, Divider,
  Snackbar, LinearProgress,
} from '@mui/material';
import TableRowsIcon from '@mui/icons-material/TableRows';
import BarChartIcon from '@mui/icons-material/BarChart';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import PieChartIcon from '@mui/icons-material/PieChart';
import CodeIcon from '@mui/icons-material/Code';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import HistoryIcon from '@mui/icons-material/History';
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import BoltIcon from '@mui/icons-material/Bolt';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

import NLPQueryBar from '../components/NLPQueryBar/NLPQueryBar';
import DataTable from '../components/DataTable/DataTable';
import ChartRenderer from '../components/Charts/ChartRenderer';
import { useDatasets } from '../hooks/useDatasets';
import { nlpQuery, executeSQL } from '../services/api';
import type { QueryResult, ChartType, DatasetListItem } from '../types';

const HISTORY_KEY = 'nlp_query_history';
const MAX_HISTORY = 10;

interface HistoryEntry {
  id: string;
  query: string;
  datasetId: string;
  datasetName: string;
  timestamp: string;
  rowCount: number;
}

function saveHistory(entry: HistoryEntry) {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const history: HistoryEntry[] = raw ? JSON.parse(raw) : [];
    const updated = [entry, ...history.filter((h) => h.id !== entry.id)].slice(0, MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  } catch {}
}

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

const CHART_VIEWS: { type: ChartType | 'table'; icon: React.ReactNode; label: string }[] = [
  { type: 'table', icon: <TableRowsIcon fontSize="small" />, label: 'Table' },
  { type: 'bar', icon: <BarChartIcon fontSize="small" />, label: 'Bar' },
  { type: 'line', icon: <ShowChartIcon fontSize="small" />, label: 'Line' },
  { type: 'pie', icon: <PieChartIcon fontSize="small" />, label: 'Pie' },
];

const QueryPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { datasets } = useDatasets();

  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(
    searchParams.get('dataset') || localStorage.getItem('last_dataset_id') || ''
  );
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ChartType | 'table'>('table');
  const [sqlExpanded, setSqlExpanded] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory());
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const [currentQuery, setCurrentQuery] = useState('');

  // Auto-select first ready dataset
  useEffect(() => {
    if (!selectedDatasetId && datasets.length > 0) {
      const ready = datasets.find((d) => d.status === 'ready');
      if (ready) setSelectedDatasetId(ready.id);
    }
  }, [datasets, selectedDatasetId]);

  // Persist selected dataset
  useEffect(() => {
    if (selectedDatasetId) {
      localStorage.setItem('last_dataset_id', selectedDatasetId);
    }
  }, [selectedDatasetId]);

  const handleQuery = useCallback(
    async (query: string) => {
      if (!selectedDatasetId) {
        setError('Please select a dataset before querying.');
        return;
      }
      setCurrentQuery(query);
      setLoading(true);
      setError(null);

      try {
        const res = await nlpQuery(selectedDatasetId, query);
        setResult(res);

        // Auto-pick chart view based on recommendation
        const rec = (res as any).result?.chart_recommendation || (res as any).chart_recommendation;
        if (rec && rec !== 'table') {
          setViewMode(rec as ChartType);
        } else {
          setViewMode('table');
        }

        // Save history
        const ds = datasets.find((d) => d.id === selectedDatasetId);
        const rows = (res as any).result?.row_count ?? (res as any).row_count ?? 0;
        const entry: HistoryEntry = {
          id: Date.now().toString(),
          query,
          datasetId: selectedDatasetId,
          datasetName: ds?.name || selectedDatasetId,
          timestamp: new Date().toISOString(),
          rowCount: rows,
        };
        saveHistory(entry);
        setHistory(loadHistory());
      } catch (err: any) {
        setError(err.message || 'Query failed.');
      } finally {
        setLoading(false);
      }
    },
    [selectedDatasetId, datasets]
  );

  const handleHistoryClick = (entry: HistoryEntry) => {
    setSelectedDatasetId(entry.datasetId);
    handleQuery(entry.query);
  };

  const copySql = () => {
    const sql = (result as any)?.result?.sql || (result as any)?.generated_sql || '';
    navigator.clipboard.writeText(sql);
    setSnackbar('SQL copied to clipboard');
  };

  const readyDatasets = datasets.filter((d) => d.status === 'ready');
  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId);

  const rawData = (result as any)?.result?.rows || (result as any)?.data || [];
  const rawColumns = (result as any)?.result?.columns || (result as any)?.columns || [];
  const sql = (result as any)?.result?.sql || (result as any)?.generated_sql || '';
  const execMs = (result as any)?.result?.execution_time_ms || (result as any)?.execution_time_ms || 0;
  const fromCache = (result as any)?.result?.from_cache || false;
  const intent = (result as any)?.result?.intent || null;

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          NLP Query Engine
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Ask questions about your data in plain English. The engine converts them to SQL automatically.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Left panel: query + history */}
        <Grid item xs={12} md={4} lg={3}>
          <Paper sx={{ p: 2.5, mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.75rem' }}>
              Dataset
            </Typography>
            {readyDatasets.length === 0 ? (
              <Alert severity="info" sx={{ fontSize: '0.8rem' }}>
                No ready datasets.{' '}
                <Box component="span" sx={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => navigate('/datasets')}>
                  Upload one first.
                </Box>
              </Alert>
            ) : (
              <FormControl fullWidth size="small">
                <Select
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                  displayEmpty
                >
                  <MenuItem value="" disabled>
                    Select dataset…
                  </MenuItem>
                  {readyDatasets.map((d) => (
                    <MenuItem key={d.id} value={d.id}>
                      <Box>
                        <Typography variant="body2" fontWeight={500}>{d.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {(d.row_count || 0).toLocaleString()} rows · {d.column_count} cols
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Paper>

          {/* Query history */}
          <Paper sx={{ p: 2 }}>
            <Box
              sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', mb: historyExpanded ? 1.5 : 0 }}
              onClick={() => setHistoryExpanded(!historyExpanded)}
            >
              <HistoryIcon sx={{ fontSize: 18, mr: 1, color: 'text.secondary' }} />
              <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                Query History
              </Typography>
              <Chip label={history.length} size="small" />
              {historyExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </Box>
            <Collapse in={historyExpanded}>
              {history.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
                  No queries yet.
                </Typography>
              ) : (
                history.map((entry) => (
                  <Box
                    key={entry.id}
                    onClick={() => handleHistoryClick(entry)}
                    sx={{
                      p: 1,
                      mb: 0.5,
                      borderRadius: 1,
                      cursor: 'pointer',
                      border: '1px solid',
                      borderColor: 'divider',
                      '&:hover': { backgroundColor: 'action.hover' },
                    }}
                  >
                    <Typography variant="body2" noWrap fontWeight={500}>
                      {entry.query}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {entry.datasetName} · {entry.rowCount} rows
                    </Typography>
                  </Box>
                ))
              )}
            </Collapse>
          </Paper>
        </Grid>

        {/* Right panel: query bar + results */}
        <Grid item xs={12} md={8} lg={9}>
          <Paper sx={{ p: 2.5, mb: 2 }}>
            <NLPQueryBar
              onQuery={handleQuery}
              loading={loading}
              datasetSelected={!!selectedDatasetId}
            />
          </Paper>

          {loading && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {result && !loading && (
            <>
              {/* Result metadata */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                <Chip
                  icon={<TableRowsIcon fontSize="small" />}
                  label={`${rawData.length.toLocaleString()} rows`}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
                <Chip
                  icon={<AccessTimeIcon fontSize="small" />}
                  label={`${execMs.toFixed(1)} ms`}
                  size="small"
                  variant="outlined"
                />
                {fromCache && (
                  <Chip icon={<BoltIcon fontSize="small" />} label="cached" size="small" color="success" variant="outlined" />
                )}
                {intent && (
                  <Chip label={`intent: ${typeof intent === 'string' ? intent : intent.intent || 'parsed'}`} size="small" variant="outlined" />
                )}

                <Box sx={{ flexGrow: 1 }} />

                {/* View toggle */}
                <ButtonGroup size="small" variant="outlined">
                  {CHART_VIEWS.map(({ type, icon, label }) => (
                    <Tooltip key={type} title={label}>
                      <Button
                        onClick={() => setViewMode(type)}
                        variant={viewMode === type ? 'contained' : 'outlined'}
                        sx={{ minWidth: 40 }}
                      >
                        {icon}
                      </Button>
                    </Tooltip>
                  ))}
                </ButtonGroup>
              </Box>

              {/* Generated SQL */}
              <Paper variant="outlined" sx={{ mb: 2, borderRadius: 2 }}>
                <Box
                  sx={{ display: 'flex', alignItems: 'center', px: 2, py: 1, cursor: 'pointer' }}
                  onClick={() => setSqlExpanded(!sqlExpanded)}
                >
                  <CodeIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
                  <Typography variant="caption" fontWeight={600} sx={{ flexGrow: 1 }}>
                    Generated SQL
                  </Typography>
                  <Tooltip title="Copy SQL">
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); copySql(); }}>
                      <ContentCopyIcon sx={{ fontSize: 14 }} />
                    </IconButton>
                  </Tooltip>
                  {sqlExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                </Box>
                <Collapse in={sqlExpanded}>
                  <Divider />
                  <Box
                    component="pre"
                    sx={{
                      m: 0, p: 2,
                      fontSize: '0.8rem',
                      fontFamily: 'monospace',
                      backgroundColor: 'grey.50',
                      overflowX: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                      borderBottomLeftRadius: 8,
                      borderBottomRightRadius: 8,
                    }}
                  >
                    {sql}
                  </Box>
                </Collapse>
              </Paper>

              {/* Results */}
              <Paper sx={{ minHeight: 300 }}>
                {viewMode === 'table' ? (
                  <DataTable
                    data={rawData}
                    columns={rawColumns.map((c: any) => (typeof c === 'string' ? { name: c, dtype: 'text' } : c))}
                  />
                ) : (
                  <Box sx={{ p: 2, height: 400 }}>
                    <ChartRenderer
                      chartType={viewMode as ChartType}
                      data={rawData}
                    />
                  </Box>
                )}
              </Paper>
            </>
          )}

          {!result && !loading && !error && (
            <Paper
              sx={{
                p: 6, textAlign: 'center', border: '2px dashed',
                borderColor: 'divider', backgroundColor: 'transparent',
              }}
            >
              <BoltIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Ask anything about your data
              </Typography>
              <Typography variant="body2" color="text.disabled">
                Try: "Show top 10 rows", "Count by category", "Monthly trend"
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>

      <Snackbar
        open={!!snackbar}
        autoHideDuration={2000}
        onClose={() => setSnackbar(null)}
        message={snackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default QueryPage;
