import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Typography,
  TextField,
  Button,
  Chip,
  InputAdornment,
  Tooltip,
  IconButton,
  Skeleton,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import NumbersIcon from '@mui/icons-material/Numbers';
import AbcIcon from '@mui/icons-material/Abc';
import DateRangeIcon from '@mui/icons-material/DateRange';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import FilterListOffIcon from '@mui/icons-material/FilterListOff';
import type { QueryColumn } from '../../types';
import { truncate } from '../../utils/format';

type Order = 'asc' | 'desc';

interface DataTableProps {
  columns: QueryColumn[];
  data: Record<string, unknown>[];
  loading?: boolean;
  title?: string;
  maxHeight?: number | string;
  onExportCSV?: () => void;
  showExport?: boolean;
  compact?: boolean;
}

const getTypeIcon = (dtype: string) => {
  const lower = dtype.toLowerCase();
  if (lower.includes('int') || lower.includes('float') || lower.includes('double') || lower.includes('numeric')) {
    return <NumbersIcon sx={{ fontSize: 14, color: 'info.main' }} />;
  }
  if (lower.includes('date') || lower.includes('time')) {
    return <DateRangeIcon sx={{ fontSize: 14, color: 'secondary.main' }} />;
  }
  if (lower === 'bool' || lower === 'boolean') {
    return <CheckBoxIcon sx={{ fontSize: 14, color: 'warning.main' }} />;
  }
  return <AbcIcon sx={{ fontSize: 14, color: 'text.secondary' }} />;
};

const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toLocaleString();
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const isCellNull = (value: unknown): boolean => value === null || value === undefined;

const DataTable: React.FC<DataTableProps> = ({
  columns,
  data,
  loading = false,
  title,
  maxHeight = 480,
  onExportCSV,
  showExport = true,
  compact = false,
}) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [orderBy, setOrderBy] = useState<string>('');
  const [order, setOrder] = useState<Order>('asc');
  const [searchText, setSearchText] = useState('');

  // Filter
  const filteredData = useMemo(() => {
    if (!searchText.trim()) return data;
    const lower = searchText.toLowerCase();
    return data.filter((row) =>
      Object.values(row).some((v) => {
        const str = formatCellValue(v).toLowerCase();
        return str.includes(lower);
      })
    );
  }, [data, searchText]);

  // Sort
  const sortedData = useMemo(() => {
    if (!orderBy) return filteredData;
    return [...filteredData].sort((a, b) => {
      const av = a[orderBy];
      const bv = b[orderBy];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      if (typeof av === 'number' && typeof bv === 'number') {
        return order === 'asc' ? av - bv : bv - av;
      }
      const as = String(av).toLowerCase();
      const bs = String(bv).toLowerCase();
      if (order === 'asc') return as < bs ? -1 : as > bs ? 1 : 0;
      return as > bs ? -1 : as < bs ? 1 : 0;
    });
  }, [filteredData, orderBy, order]);

  const paginatedData = sortedData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const handleSort = (col: string) => {
    if (orderBy === col) {
      setOrder(order === 'asc' ? 'desc' : 'asc');
    } else {
      setOrderBy(col);
      setOrder('asc');
    }
    setPage(0);
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value);
    setPage(0);
  };

  const handleExportCSV = () => {
    if (onExportCSV) {
      onExportCSV();
      return;
    }
    // Client-side export
    const header = columns.map((c) => c.name).join(',');
    const rows = data.map((row) =>
      columns.map((c) => {
        const val = formatCellValue(row[c.name]);
        return val.includes(',') ? `"${val}"` : val;
      }).join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <Box>
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} height={compact ? 36 : 48} sx={{ mb: 0.5 }} />
        ))}
      </Box>
    );
  }

  return (
    <Box>
      {/* Toolbar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          mb: 1.5,
          flexWrap: 'wrap',
        }}
      >
        {title && (
          <Typography variant="subtitle1" fontWeight={600} sx={{ mr: 'auto' }}>
            {title}
          </Typography>
        )}
        <Chip
          label={`${filteredData.length.toLocaleString()} row${filteredData.length !== 1 ? 's' : ''}`}
          size="small"
          variant="outlined"
          color="primary"
        />
        <TextField
          size="small"
          value={searchText}
          onChange={handleSearch}
          placeholder="Search..."
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: searchText ? (
              <InputAdornment position="end">
                <Tooltip title="Clear search">
                  <IconButton size="small" onClick={() => { setSearchText(''); setPage(0); }}>
                    <FilterListOffIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </InputAdornment>
            ) : null,
          }}
          sx={{ width: 200 }}
        />
        {showExport && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<FileDownloadIcon />}
            onClick={handleExportCSV}
            disabled={data.length === 0}
          >
            Export CSV
          </Button>
        )}
      </Box>

      {/* Table */}
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{ maxHeight, borderRadius: 2 }}
      >
        <Table stickyHeader size={compact ? 'small' : 'medium'}>
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell
                  key={col.name}
                  sortDirection={orderBy === col.name ? order : false}
                  sx={{ whiteSpace: 'nowrap', minWidth: 100 }}
                >
                  <TableSortLabel
                    active={orderBy === col.name}
                    direction={orderBy === col.name ? order : 'asc'}
                    onClick={() => handleSort(col.name)}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {getTypeIcon(col.dtype)}
                      <span>{col.name}</span>
                    </Box>
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} align="center" sx={{ py: 6 }}>
                  <Typography color="text.secondary">
                    {searchText ? 'No results match your search' : 'No data available'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedData.map((row, rowIdx) => (
                <TableRow
                  key={rowIdx}
                  hover
                  sx={{
                    '&:last-child td': { borderBottom: 0 },
                  }}
                >
                  {columns.map((col) => {
                    const cellValue = row[col.name];
                    const isNull = isCellNull(cellValue);
                    const displayValue = isNull ? '' : formatCellValue(cellValue);
                    const isTruncated = displayValue.length > 60;

                    return (
                      <TableCell key={col.name} sx={{ maxWidth: 300 }}>
                        {isNull ? (
                          <Typography
                            variant="caption"
                            color="text.disabled"
                            fontStyle="italic"
                          >
                            null
                          </Typography>
                        ) : isTruncated ? (
                          <Tooltip title={displayValue} placement="top-start">
                            <Typography variant="body2" sx={{ cursor: 'help' }}>
                              {truncate(displayValue, 60)}
                            </Typography>
                          </Tooltip>
                        ) : (
                          <Typography
                            variant="body2"
                            sx={{
                              fontVariantNumeric:
                                typeof cellValue === 'number' ? 'tabular-nums' : 'normal',
                              fontFamily:
                                typeof cellValue === 'number'
                                  ? "'Fira Code', monospace"
                                  : 'inherit',
                              textAlign: typeof cellValue === 'number' ? 'right' : 'left',
                            }}
                          >
                            {displayValue}
                          </Typography>
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <TablePagination
        component="div"
        count={filteredData.length}
        page={page}
        onPageChange={(_, p) => setPage(p)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
        rowsPerPageOptions={[10, 25, 50, 100]}
        labelRowsPerPage="Rows:"
        sx={{ borderTop: '1px solid', borderColor: 'divider' }}
      />
    </Box>
  );
};

export default DataTable;
