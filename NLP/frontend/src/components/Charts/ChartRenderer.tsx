import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  LabelList,
} from 'recharts';
import { Box, Typography, Paper } from '@mui/material';
import type { ChartType, ChartConfig } from '../../types';

// ─── Color palette ────────────────────────────────────────────────────────────

const COLORS = [
  '#1976d2',
  '#00897b',
  '#ed6c02',
  '#d32f2f',
  '#7b1fa2',
  '#c2185b',
  '#0288d1',
  '#388e3c',
];

const GRADIENT_COLORS = {
  primary: ['#42a5f5', '#1565c0'],
  secondary: ['#4db6ac', '#00695c'],
};

// ─── Custom Tooltip ───────────────────────────────────────────────────────────

const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: { name: string; value: number | string; color: string }[];
  label?: string;
}> = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <Paper
      elevation={4}
      sx={{
        px: 2,
        py: 1.5,
        borderRadius: 2,
        maxWidth: 280,
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      {label && (
        <Typography variant="caption" fontWeight={700} color="text.secondary" display="block" mb={0.5}>
          {String(label)}
        </Typography>
      )}
      {payload.map((entry, i) => (
        <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
          <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: entry.color, flexShrink: 0 }} />
          <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
            {entry.name}:
          </Typography>
          <Typography variant="body2" fontWeight={600}>
            {typeof entry.value === 'number'
              ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
              : String(entry.value)}
          </Typography>
        </Box>
      ))}
    </Paper>
  );
};

// ─── Pie custom label ─────────────────────────────────────────────────────────

const renderPieLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  percent: number;
}) => {
  if (percent < 0.04) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={600}>
      {`${(percent * 100).toFixed(1)}%`}
    </text>
  );
};

// ─── Data preparation helpers ─────────────────────────────────────────────────

const inferChartType = (
  data: Record<string, unknown>[],
  config?: ChartConfig
): { chartType: ChartType; xKey: string; yKey: string } => {
  if (!data || data.length === 0) return { chartType: 'bar', xKey: '', yKey: '' };

  const keys = Object.keys(data[0] || {});
  if (keys.length === 0) return { chartType: 'bar', xKey: '', yKey: '' };

  const numericKeys = keys.filter((k) => typeof data[0][k] === 'number');
  const stringKeys = keys.filter((k) => typeof data[0][k] === 'string');

  // Single numeric value → metric
  if (numericKeys.length === 1 && keys.length === 1) {
    return { chartType: 'metric', xKey: '', yKey: numericKeys[0] };
  }

  const xKey = config?.x_axis || stringKeys[0] || keys[0];
  const yKey = config?.y_axis || numericKeys[0] || keys[1] || keys[0];

  // Detect time series
  const xValues = data.map((d) => String(d[xKey]));
  const isTimeSeries =
    xValues.some((v) => /^\d{4}(-\d{2})?(-\d{2})?/.test(v));

  if (isTimeSeries) return { chartType: 'line', xKey, yKey };
  if (data.length <= 8 && stringKeys.length >= 1) return { chartType: 'pie', xKey, yKey };
  return { chartType: 'bar', xKey, yKey };
};

const preparePieData = (data: Record<string, unknown>[], nameKey: string, valueKey: string) => {
  const sorted = [...data].sort((a, b) => (Number(b[valueKey]) || 0) - (Number(a[valueKey]) || 0));
  if (sorted.length <= 8) return sorted.map((d) => ({ name: String(d[nameKey]), value: Number(d[valueKey]) || 0 }));

  const top7 = sorted.slice(0, 7);
  const otherValue = sorted.slice(7).reduce((sum, d) => sum + (Number(d[valueKey]) || 0), 0);
  return [
    ...top7.map((d) => ({ name: String(d[nameKey]), value: Number(d[valueKey]) || 0 })),
    { name: 'Other', value: otherValue },
  ];
};

// ─── Main component ───────────────────────────────────────────────────────────

interface ChartRendererProps {
  chartType?: ChartType;
  data: Record<string, unknown>[];
  config?: ChartConfig;
  height?: number;
  title?: string;
}

const ChartRenderer: React.FC<ChartRendererProps> = ({
  chartType: propChartType,
  data,
  config,
  height = 340,
  title,
}) => {
  const { chartType, xKey, yKey } = useMemo(() => {
    if (propChartType && propChartType !== 'table') {
      const keys = data?.[0] ? Object.keys(data[0]) : [];
      const numericKeys = keys.filter((k) => typeof data[0][k] === 'number');
      const stringKeys = keys.filter((k) => typeof data[0][k] === 'string');
      const xK = config?.x_axis || stringKeys[0] || keys[0] || '';
      const yK = config?.y_axis || numericKeys[0] || keys[1] || keys[0] || '';
      return { chartType: propChartType, xKey: xK, yKey: yK };
    }
    return inferChartType(data, config);
  }, [propChartType, data, config]);

  const seriesKeys = useMemo(() => {
    if (!data?.[0]) return [yKey];
    const keys = Object.keys(data[0]);
    return keys.filter((k) => k !== xKey && typeof data[0][k] === 'number');
  }, [data, xKey, yKey]);

  // Metric chart
  if (chartType === 'metric' || data?.length === 1) {
    const val = data?.[0]?.[yKey];
    const label = title || yKey || config?.title || 'Metric';
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height,
          gap: 1,
        }}
      >
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography
          variant="h2"
          fontWeight={800}
          color="primary.main"
          sx={{ lineHeight: 1 }}
        >
          {typeof val === 'number'
            ? val.toLocaleString(undefined, { maximumFractionDigits: 2 })
            : String(val ?? '—')}
        </Typography>
        {config?.aggregation && (
          <Typography variant="caption" color="text.secondary">
            {config.aggregation}
          </Typography>
        )}
      </Box>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height }}>
        <Typography color="text.secondary">No data to display</Typography>
      </Box>
    );
  }

  const tickFormatter = (value: unknown) => {
    const s = String(value);
    return s.length > 12 ? s.slice(0, 12) + '…' : s;
  };

  const numericFormatter = (value: number) =>
    value >= 1000000
      ? `${(value / 1000000).toFixed(1)}M`
      : value >= 1000
      ? `${(value / 1000).toFixed(1)}K`
      : value.toLocaleString(undefined, { maximumFractionDigits: 2 });

  // Bar chart
  if (chartType === 'bar') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
          <defs>
            <linearGradient id="barGrad0" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={GRADIENT_COLORS.primary[0]} />
              <stop offset="100%" stopColor={GRADIENT_COLORS.primary[1]} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tickFormatter={tickFormatter}
            angle={-30}
            textAnchor="end"
            height={60}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={numericFormatter}
          />
          <RechartsTooltip content={<CustomTooltip />} />
          {seriesKeys.length > 1 && <Legend />}
          {seriesKeys.map((key, i) => (
            <Bar
              key={key}
              dataKey={key}
              fill={i === 0 ? 'url(#barGrad0)' : COLORS[i % COLORS.length]}
              radius={[4, 4, 0, 0]}
              maxBarSize={60}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // Line chart
  if (chartType === 'line') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tickFormatter={tickFormatter}
            angle={-30}
            textAnchor="end"
            height={60}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={numericFormatter}
          />
          <RechartsTooltip content={<CustomTooltip />} />
          {seriesKeys.length > 1 && <Legend />}
          {seriesKeys.map((key, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2.5}
              dot={data.length < 30}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  // Area chart
  if (chartType === 'area') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
          <defs>
            {seriesKeys.map((key, i) => (
              <linearGradient key={key} id={`areaGrad${i}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tickFormatter={tickFormatter}
            angle={-30}
            textAnchor="end"
            height={60}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={numericFormatter}
          />
          <RechartsTooltip content={<CustomTooltip />} />
          {seriesKeys.length > 1 && <Legend />}
          {seriesKeys.map((key, i) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={COLORS[i % COLORS.length]}
              fill={`url(#areaGrad${i})`}
              strokeWidth={2.5}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  // Pie chart
  if (chartType === 'pie') {
    const pieData = preparePieData(data, xKey, yKey);
    return (
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            outerRadius={height * 0.35}
            innerRadius={height * 0.15}
            dataKey="value"
            nameKey="name"
            labelLine={false}
            label={renderPieLabel}
          >
            {pieData.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <RechartsTooltip
            formatter={(value: number) => [numericFormatter(value), '']}
          />
          <Legend
            formatter={(value) => (
              <span style={{ fontSize: 12, color: '#475569' }}>{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  // Scatter chart
  if (chartType === 'scatter') {
    const scatterData = data.map((d) => ({
      x: Number(d[xKey]) || 0,
      y: Number(d[yKey]) || 0,
    }));
    return (
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            type="number"
            dataKey="x"
            name={xKey}
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tickFormatter={numericFormatter}
            label={{ value: xKey, position: 'insideBottom', offset: -5, fontSize: 12, fill: '#64748b' }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name={yKey}
            tick={{ fontSize: 12, fill: '#64748b' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={numericFormatter}
            label={{ value: yKey, angle: -90, position: 'insideLeft', fontSize: 12, fill: '#64748b' }}
          />
          <RechartsTooltip
            cursor={{ strokeDasharray: '3 3' }}
            formatter={(value: number, name: string) => [numericFormatter(value), name]}
          />
          <Scatter data={scatterData} fill={COLORS[0]} opacity={0.7} />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  // Fallback bar
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey={xKey} tick={{ fontSize: 12 }} angle={-30} textAnchor="end" height={60} />
        <YAxis tick={{ fontSize: 12 }} tickFormatter={numericFormatter} />
        <RechartsTooltip content={<CustomTooltip />} />
        <Bar dataKey={yKey} fill={COLORS[0]} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default ChartRenderer;
