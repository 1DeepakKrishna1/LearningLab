import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Chip,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Collapse,
  IconButton,
  Tooltip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  InputAdornment,
} from '@mui/material';
import PsychologyIcon from '@mui/icons-material/Psychology';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import HistoryIcon from '@mui/icons-material/History';
import SendIcon from '@mui/icons-material/Send';
import ClearIcon from '@mui/icons-material/Clear';
import CodeIcon from '@mui/icons-material/Code';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import type { DatasetListItem, QueryHistoryItem } from '../../types';
import { formatRelativeTime } from '../../utils/format';

const SUGGESTION_CHIPS = [
  'Top 10 customers by revenue',
  'Monthly sales trend over time',
  'Show distribution of age column',
  'Correlation analysis between numeric columns',
  'Count records by category',
  'Average value by group',
  'Find records where value is above average',
  'Compare performance across regions',
];

interface NLPQueryBarProps {
  datasets: DatasetListItem[];
  selectedDatasetId: string;
  onDatasetChange: (id: string) => void;
  onSubmit: (query: string) => Promise<void>;
  loading: boolean;
  generatedSQL?: string;
  queryHistory: QueryHistoryItem[];
  onHistorySelect: (item: QueryHistoryItem) => void;
  onClearHistory: () => void;
}

const NLPQueryBar: React.FC<NLPQueryBarProps> = ({
  datasets,
  selectedDatasetId,
  onDatasetChange,
  onSubmit,
  loading,
  generatedSQL,
  queryHistory,
  onHistorySelect,
  onClearHistory,
}) => {
  const [query, setQuery] = useState('');
  const [sqlExpanded, setSqlExpanded] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading]);

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (!trimmed || !selectedDatasetId || loading) return;
    await onSubmit(trimmed);
    setSqlExpanded(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    inputRef.current?.focus();
  };

  const handleCopySQL = async () => {
    if (!generatedSQL) return;
    try {
      await navigator.clipboard.writeText(generatedSQL);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  };

  const handleHistorySelect = (item: QueryHistoryItem) => {
    setQuery(item.query);
    onHistorySelect(item);
    setHistoryExpanded(false);
    inputRef.current?.focus();
  };

  return (
    <Box>
      {/* Main Query Card */}
      <Paper
        elevation={0}
        sx={{
          border: '2px solid',
          borderColor: loading ? 'primary.main' : 'divider',
          borderRadius: 3,
          overflow: 'hidden',
          transition: 'border-color 0.2s ease',
          '&:focus-within': { borderColor: 'primary.main' },
        }}
      >
        {/* Header */}
        <Box
          sx={{
            px: 2.5,
            py: 1.5,
            background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <PsychologyIcon sx={{ color: 'white', fontSize: 22 }} />
          <Typography variant="subtitle2" sx={{ color: 'white', fontWeight: 600 }}>
            Ask in Natural Language
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.75)' }}>
            Press Ctrl+Enter to submit
          </Typography>
        </Box>

        {/* Dataset selector + input */}
        <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {datasets.length > 1 && (
            <FormControl size="small" fullWidth>
              <InputLabel>Dataset</InputLabel>
              <Select
                value={selectedDatasetId}
                onChange={(e) => onDatasetChange(e.target.value)}
                label="Dataset"
                disabled={loading}
              >
                {datasets.map((d) => (
                  <MenuItem key={d.id} value={d.id}>
                    <Box>
                      <Typography variant="body2" fontWeight={500}>
                        {d.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {d.row_count?.toLocaleString()} rows · {d.column_count} cols
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <TextField
            inputRef={inputRef}
            fullWidth
            multiline
            minRows={2}
            maxRows={5}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='e.g., "Show me the top 10 products by total sales in Q4" or "What is the average age by department?"'
            variant="outlined"
            disabled={loading || !selectedDatasetId}
            InputProps={{
              sx: { fontSize: '1rem', lineHeight: 1.6 },
              endAdornment: query ? (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    onClick={() => setQuery('')}
                    edge="end"
                    sx={{ color: 'text.secondary' }}
                  >
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ) : null,
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                '& fieldset': { border: 'none' },
                backgroundColor: 'background.default',
              },
            }}
          />

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              {query.length > 0 ? `${query.length} characters` : 'Type your question above'}
            </Typography>
            <Button
              variant="contained"
              size="large"
              onClick={handleSubmit}
              disabled={!query.trim() || !selectedDatasetId || loading}
              startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <SendIcon />}
              sx={{ minWidth: 140 }}
            >
              {loading ? 'Analyzing...' : 'Run Query'}
            </Button>
          </Box>
        </Box>

        {/* Suggestion chips */}
        <Box sx={{ px: 2, pb: 1.5 }}>
          <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ mb: 1, display: 'block' }}>
            QUICK SUGGESTIONS
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {SUGGESTION_CHIPS.map((s) => (
              <Chip
                key={s}
                label={s}
                size="small"
                variant="outlined"
                clickable
                onClick={() => handleSuggestionClick(s)}
                disabled={loading}
                sx={{
                  fontSize: '0.75rem',
                  '&:hover': { borderColor: 'primary.main', color: 'primary.main' },
                }}
              />
            ))}
          </Box>
        </Box>

        {/* Generated SQL (collapsible) */}
        {generatedSQL && (
          <>
            <Divider />
            <Box>
              <Box
                onClick={() => setSqlExpanded(!sqlExpanded)}
                sx={{
                  px: 2,
                  py: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  cursor: 'pointer',
                  '&:hover': { backgroundColor: 'action.hover' },
                }}
              >
                <CodeIcon fontSize="small" color="action" />
                <Typography variant="caption" fontWeight={600} color="text.secondary">
                  GENERATED SQL
                </Typography>
                <Box sx={{ flexGrow: 1 }} />
                <Tooltip title={copied ? 'Copied!' : 'Copy SQL'}>
                  <IconButton
                    size="small"
                    onClick={(e) => { e.stopPropagation(); handleCopySQL(); }}
                    color={copied ? 'success' : 'default'}
                  >
                    <ContentCopyIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                {sqlExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </Box>
              <Collapse in={sqlExpanded}>
                <Box
                  sx={{
                    mx: 2,
                    mb: 1.5,
                    p: 1.5,
                    backgroundColor: '#1e293b',
                    borderRadius: 2,
                    fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
                    fontSize: '0.8125rem',
                    color: '#e2e8f0',
                    overflowX: 'auto',
                    whiteSpace: 'pre',
                    lineHeight: 1.7,
                  }}
                >
                  {generatedSQL}
                </Box>
              </Collapse>
            </Box>
          </>
        )}
      </Paper>

      {/* Query History */}
      {queryHistory.length > 0 && (
        <Paper
          elevation={0}
          sx={{ mt: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}
        >
          <Box
            onClick={() => setHistoryExpanded(!historyExpanded)}
            sx={{
              px: 2,
              py: 1.25,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              cursor: 'pointer',
              '&:hover': { backgroundColor: 'action.hover' },
              borderRadius: 'inherit',
            }}
          >
            <HistoryIcon fontSize="small" color="action" />
            <Typography variant="subtitle2" color="text.secondary">
              Recent Queries ({queryHistory.length})
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Button
              size="small"
              color="inherit"
              onClick={(e) => { e.stopPropagation(); onClearHistory(); }}
              sx={{ color: 'text.secondary', fontSize: '0.75rem' }}
            >
              Clear
            </Button>
            {historyExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </Box>
          <Collapse in={historyExpanded}>
            <Divider />
            <List disablePadding dense>
              {queryHistory.map((item, index) => (
                <React.Fragment key={item.id}>
                  <ListItem
                    button
                    onClick={() => handleHistorySelect(item)}
                    sx={{
                      px: 2,
                      py: 1,
                      '&:hover': { backgroundColor: 'action.hover' },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <AccessTimeIcon fontSize="small" color="action" />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Typography
                          variant="body2"
                          fontWeight={500}
                          sx={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {item.query}
                        </Typography>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {item.dataset_name} · {formatRelativeTime(item.timestamp)}
                          {item.result_count !== undefined && ` · ${item.result_count.toLocaleString()} rows`}
                        </Typography>
                      }
                    />
                  </ListItem>
                  {index < queryHistory.length - 1 && <Divider component="li" />}
                </React.Fragment>
              ))}
            </List>
          </Collapse>
        </Paper>
      )}
    </Box>
  );
};

export default NLPQueryBar;
