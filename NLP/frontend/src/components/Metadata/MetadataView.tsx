import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Chip,
  LinearProgress,
  Tooltip,
  Collapse,
  IconButton,
  Divider,
  useTheme,
} from '@mui/material';
import NumbersIcon from '@mui/icons-material/Numbers';
import AbcIcon from '@mui/icons-material/Abc';
import DateRangeIcon from '@mui/icons-material/DateRange';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import type { Dataset, DatasetColumn } from '../../types';
import { formatNumber, formatPercent } from '../../utils/format';

// ─── Column Type Helpers ──────────────────────────────────────────────────────

const getColumnTypeIcon = (dtype: string): React.ReactNode => {
  const lower = dtype.toLowerCase();
  if (
    lower.includes('int') ||
    lower.includes('float') ||
    lower.includes('double') ||
    lower.includes('numeric') ||
    lower.includes('decimal')
  ) {
    return <NumbersIcon sx={{ fontSize: 16, color: 'info.main' }} />;
  }
  if (lower.includes('date') || lower.includes('time')) {
    return <DateRangeIcon sx={{ fontSize: 16, color: 'secondary.main' }} />;
  }
  if (lower === 'bool' || lower === 'boolean') {
    return <CheckBoxIcon sx={{ fontSize: 16, color: 'warning.main' }} />;
  }
  return <AbcIcon sx={{ fontSize: 16, color: 'text.secondary' }} />;
};

const getColumnTypeLabel = (dtype: string): string => {
  const lower = dtype.toLowerCase();
  if (lower.includes('int')) return 'Integer';
  if (lower.includes('float') || lower.includes('double') || lower.includes('decimal')) return 'Float';
  if (lower.includes('date')) return 'Date';
  if (lower.includes('time')) return 'DateTime';
  if (lower === 'bool' || lower === 'boolean') return 'Boolean';
  return 'Text';
};

const getNullColor = (pct: number): 'success' | 'warning' | 'error' | 'default' => {
  if (pct === 0) return 'success';
  if (pct < 10) return 'default';
  if (pct < 30) return 'warning';
  return 'error';
};

const getHealthIcon = (score: number) => {
  if (score >= 80) return <HealthAndSafetyIcon sx={{ color: 'success.main' }} />;
  if (score >= 50) return <WarningAmberIcon sx={{ color: 'warning.main' }} />;
  return <ErrorOutlineIcon sx={{ color: 'error.main' }} />;
};

const getHealthColor = (score: number): string => {
  if (score >= 80) return '#2e7d32';
  if (score >= 50) return '#ed6c02';
  return '#d32f2f';
};

// ─── Column Card ──────────────────────────────────────────────────────────────

interface ColumnCardProps {
  column: DatasetColumn;
}

const ColumnCard: React.FC<ColumnCardProps> = ({ column }) => {
  const theme = useTheme();
  const nullPct = column.null_percentage ?? 0;
  const nullColor = getNullColor(nullPct);

  const sampleValues = (column.sample_values || [])
    .filter((v) => v !== null && v !== undefined)
    .slice(0, 5)
    .map((v) => String(v));

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        borderRadius: 2,
        height: '100%',
        transition: 'box-shadow 0.2s',
        '&:hover': {
          boxShadow: theme.shadows[3],
        },
        borderLeft: '3px solid',
        borderLeftColor:
          nullColor === 'success'
            ? 'success.main'
            : nullColor === 'warning'
            ? 'warning.main'
            : nullColor === 'error'
            ? 'error.main'
            : 'divider',
      }}
    >
      {/* Column header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1 }}>
        {getColumnTypeIcon(column.dtype)}
        <Tooltip title={column.name} placement="top">
          <Typography
            variant="subtitle2"
            fontWeight={600}
            sx={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
            }}
          >
            {column.name}
          </Typography>
        </Tooltip>
        <Chip
          label={getColumnTypeLabel(column.dtype)}
          size="small"
          variant="outlined"
          sx={{ fontSize: '0.65rem', height: 18, flexShrink: 0 }}
        />
      </Box>

      {/* Null percentage bar */}
      <Box sx={{ mb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.25 }}>
          <Typography variant="caption" color="text.secondary">
            Nulls
          </Typography>
          <Chip
            label={formatPercent(nullPct)}
            size="small"
            color={nullColor === 'default' ? undefined : nullColor}
            variant={nullPct === 0 ? 'filled' : 'outlined'}
            sx={{ height: 18, fontSize: '0.65rem' }}
          />
        </Box>
        <LinearProgress
          variant="determinate"
          value={Math.min(nullPct, 100)}
          color={nullColor === 'default' ? 'primary' : nullColor}
          sx={{ height: 4, borderRadius: 2 }}
        />
      </Box>

      {/* Stats grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5, mb: 1 }}>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Unique
          </Typography>
          <Typography variant="body2" fontWeight={600}>
            {formatNumber(column.unique_count)}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Non-null
          </Typography>
          <Typography variant="body2" fontWeight={600}>
            {formatNumber(column.null_count !== undefined ? undefined : undefined)}
            {column.null_count !== undefined && column.null_percentage !== undefined
              ? formatPercent(100 - column.null_percentage)
              : '—'}
          </Typography>
        </Box>
        {column.min_value !== undefined && column.min_value !== null && (
          <Box>
            <Typography variant="caption" color="text.secondary">
              Min
            </Typography>
            <Typography variant="body2" fontWeight={600} sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
              {String(column.min_value).length > 8
                ? String(column.min_value).slice(0, 8) + '…'
                : String(column.min_value)}
            </Typography>
          </Box>
        )}
        {column.max_value !== undefined && column.max_value !== null && (
          <Box>
            <Typography variant="caption" color="text.secondary">
              Max
            </Typography>
            <Typography variant="body2" fontWeight={600} sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
              {String(column.max_value).length > 8
                ? String(column.max_value).slice(0, 8) + '…'
                : String(column.max_value)}
            </Typography>
          </Box>
        )}
      </Box>

      {/* Sample values */}
      {sampleValues.length > 0 && (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            Sample values
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.4 }}>
            {sampleValues.map((v, i) => (
              <Tooltip key={i} title={v.length > 16 ? v : ''} placement="top">
                <Chip
                  label={v.length > 16 ? v.slice(0, 16) + '…' : v}
                  size="small"
                  variant="outlined"
                  sx={{ height: 18, fontSize: '0.65rem', maxWidth: 100 }}
                />
              </Tooltip>
            ))}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

// ─── Column Group ─────────────────────────────────────────────────────────────

interface ColumnGroupProps {
  label: string;
  columns: DatasetColumn[];
  icon: React.ReactNode;
  defaultExpanded?: boolean;
}

const ColumnGroup: React.FC<ColumnGroupProps> = ({ label, columns, icon, defaultExpanded = true }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (columns.length === 0) return null;

  return (
    <Box sx={{ mb: 2 }}>
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          cursor: 'pointer',
          mb: 1,
          py: 0.5,
          '&:hover': { opacity: 0.8 },
        }}
      >
        {icon}
        <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
          {label}
        </Typography>
        <Chip label={columns.length} size="small" sx={{ height: 18, fontSize: '0.7rem' }} />
        <Box sx={{ flexGrow: 1 }} />
        <IconButton size="small">
          {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>
      <Collapse in={expanded}>
        <Grid container spacing={1.5}>
          {columns.map((col) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={col.name}>
              <ColumnCard column={col} />
            </Grid>
          ))}
        </Grid>
      </Collapse>
    </Box>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────

interface MetadataViewProps {
  dataset: Dataset;
}

const MetadataView: React.FC<MetadataViewProps> = ({ dataset }) => {
  const healthScore = dataset.health_score ?? 80;

  const columns = dataset.columns || [];
  const numericCols = columns.filter((c) => {
    const lower = c.dtype.toLowerCase();
    return (
      lower.includes('int') ||
      lower.includes('float') ||
      lower.includes('double') ||
      lower.includes('decimal') ||
      lower.includes('numeric')
    );
  });
  const datetimeCols = columns.filter((c) => {
    const lower = c.dtype.toLowerCase();
    return lower.includes('date') || lower.includes('time');
  });
  const boolCols = columns.filter((c) => {
    const lower = c.dtype.toLowerCase();
    return lower === 'bool' || lower === 'boolean';
  });
  const textCols = columns.filter(
    (c) => !numericCols.includes(c) && !datetimeCols.includes(c) && !boolCols.includes(c)
  );

  const totalNullPct =
    columns.length > 0
      ? columns.reduce((sum, c) => sum + (c.null_percentage ?? 0), 0) / columns.length
      : 0;

  return (
    <Box>
      {/* Overview Header */}
      <Box
        sx={{
          p: 2.5,
          mb: 2,
          background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          flexWrap: 'wrap',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getHealthIcon(healthScore)}
          <Box>
            <Typography variant="caption" color="text.secondary">
              Dataset Health Score
            </Typography>
            <Typography
              variant="h5"
              fontWeight={700}
              sx={{ color: getHealthColor(healthScore), lineHeight: 1.2 }}
            >
              {healthScore}/100
            </Typography>
          </Box>
        </Box>

        <Divider orientation="vertical" flexItem />

        <Box>
          <Typography variant="caption" color="text.secondary">
            Total Columns
          </Typography>
          <Typography variant="h6" fontWeight={700}>
            {columns.length}
          </Typography>
        </Box>

        <Box>
          <Typography variant="caption" color="text.secondary">
            Avg Null %
          </Typography>
          <Typography variant="h6" fontWeight={700}>
            {formatPercent(totalNullPct)}
          </Typography>
        </Box>

        <Box>
          <Typography variant="caption" color="text.secondary">
            Numeric Cols
          </Typography>
          <Typography variant="h6" fontWeight={700}>
            {numericCols.length}
          </Typography>
        </Box>

        <Box>
          <Typography variant="caption" color="text.secondary">
            Text Cols
          </Typography>
          <Typography variant="h6" fontWeight={700}>
            {textCols.length}
          </Typography>
        </Box>

        <Box>
          <Typography variant="caption" color="text.secondary">
            DateTime Cols
          </Typography>
          <Typography variant="h6" fontWeight={700}>
            {datetimeCols.length}
          </Typography>
        </Box>
      </Box>

      {/* Column groups */}
      {columns.length === 0 ? (
        <Typography color="text.secondary" textAlign="center" py={4}>
          No column metadata available
        </Typography>
      ) : (
        <>
          <ColumnGroup
            label="Numeric Columns"
            columns={numericCols}
            icon={<NumbersIcon sx={{ fontSize: 18, color: 'info.main' }} />}
          />
          <ColumnGroup
            label="Text / Categorical Columns"
            columns={textCols}
            icon={<AbcIcon sx={{ fontSize: 18, color: 'text.secondary' }} />}
          />
          <ColumnGroup
            label="Date / Time Columns"
            columns={datetimeCols}
            icon={<DateRangeIcon sx={{ fontSize: 18, color: 'secondary.main' }} />}
          />
          <ColumnGroup
            label="Boolean Columns"
            columns={boolCols}
            icon={<CheckBoxIcon sx={{ fontSize: 18, color: 'warning.main' }} />}
          />
        </>
      )}
    </Box>
  );
};

export default MetadataView;
