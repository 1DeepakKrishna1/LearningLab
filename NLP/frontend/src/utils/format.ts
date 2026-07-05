import { format as dateFnsFormat, formatDistanceToNow, parseISO, isValid } from 'date-fns';

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

export const formatNumber = (n: number | undefined | null, decimals = 0): string => {
  if (n === undefined || n === null || isNaN(n)) return '—';
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

export const formatPercent = (n: number | undefined | null): string => {
  if (n === undefined || n === null || isNaN(n)) return '—';
  return `${n.toFixed(1)}%`;
};

export const formatDate = (dateStr: string | undefined | null): string => {
  if (!dateStr) return '—';
  try {
    const d = parseISO(dateStr);
    if (!isValid(d)) return dateStr;
    return dateFnsFormat(d, 'MMM d, yyyy');
  } catch {
    return dateStr;
  }
};

export const formatDateTime = (dateStr: string | undefined | null): string => {
  if (!dateStr) return '—';
  try {
    const d = parseISO(dateStr);
    if (!isValid(d)) return dateStr;
    return dateFnsFormat(d, 'MMM d, yyyy h:mm a');
  } catch {
    return dateStr;
  }
};

export const formatRelativeTime = (dateStr: string | undefined | null): string => {
  if (!dateStr) return '—';
  try {
    const d = parseISO(dateStr);
    if (!isValid(d)) return dateStr;
    return formatDistanceToNow(d, { addSuffix: true });
  } catch {
    return dateStr;
  }
};

export const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
};

export const truncate = (str: string, maxLen = 50): string => {
  if (!str) return '';
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + '...';
};

export const getColumnTypeIcon = (dtype: string): string => {
  const lower = dtype.toLowerCase();
  if (lower.includes('int') || lower.includes('float') || lower.includes('double') || lower.includes('decimal') || lower.includes('numeric')) return 'number';
  if (lower.includes('date') || lower.includes('time')) return 'datetime';
  if (lower === 'bool' || lower === 'boolean') return 'boolean';
  return 'string';
};
