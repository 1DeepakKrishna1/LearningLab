import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Paper,
  Chip,
  Skeleton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Avatar,
  alpha,
} from '@mui/material';
import StorageIcon from '@mui/icons-material/Storage';
import PsychologyIcon from '@mui/icons-material/Psychology';
import GridViewIcon from '@mui/icons-material/GridView';
import AssessmentIcon from '@mui/icons-material/Assessment';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import AddIcon from '@mui/icons-material/Add';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import SearchIcon from '@mui/icons-material/Search';
import DashboardCustomizeIcon from '@mui/icons-material/DashboardCustomize';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { useDatasets } from '../hooks/useDatasets';
import { getReports, getDashboards } from '../services/api';
import type { ActivityItem, AppStats } from '../types';
import { formatRelativeTime } from '../utils/format';

// ─── Stats Card ───────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
  loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon, color, subtitle, loading }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent sx={{ p: 2.5 }}>
      {loading ? (
        <>
          <Skeleton width={40} height={40} variant="circular" sx={{ mb: 1.5 }} />
          <Skeleton width={60} height={36} sx={{ mb: 0.5 }} />
          <Skeleton width={100} />
        </>
      ) : (
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="body2" color="text.secondary" fontWeight={500} gutterBottom>
              {label}
            </Typography>
            <Typography variant="h4" fontWeight={800} sx={{ color, lineHeight: 1.2, mb: 0.5 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Avatar sx={{ backgroundColor: alpha(color, 0.12), width: 48, height: 48 }}>
            <Box sx={{ color, display: 'flex' }}>{icon}</Box>
          </Avatar>
        </Box>
      )}
    </CardContent>
  </Card>
);

// ─── Getting Started Step ─────────────────────────────────────────────────────

interface StepCardProps {
  step: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  action: string;
  onAction: () => void;
  color: string;
}

const StepCard: React.FC<StepCardProps> = ({ step, title, description, icon, action, onAction, color }) => (
  <Paper
    variant="outlined"
    sx={{
      p: 2.5,
      borderRadius: 3,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: 1.5,
      borderColor: 'divider',
      '&:hover': { borderColor: color, boxShadow: 3 },
      transition: 'all 0.2s',
    }}
  >
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
      <Avatar sx={{ backgroundColor: alpha(color, 0.12), color, width: 44, height: 44 }}>
        {icon}
      </Avatar>
      <Chip
        label={`Step ${step}`}
        size="small"
        sx={{ backgroundColor: alpha(color, 0.1), color, fontWeight: 700 }}
      />
    </Box>
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="subtitle1" fontWeight={700} gutterBottom>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {description}
      </Typography>
    </Box>
    <Button
      variant="outlined"
      size="small"
      onClick={onAction}
      sx={{ alignSelf: 'flex-start', borderColor: color, color }}
    >
      {action}
    </Button>
  </Paper>
);

// ─── Main Page ─────────────────────────────────────────────────────────────────

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { datasets, loading: datasetsLoading } = useDatasets();

  const [stats, setStats] = useState<AppStats>({
    total_datasets: 0,
    total_queries: 0,
    active_dashboards: 0,
    reports_generated: 0,
  });
  const [statsLoading, setStatsLoading] = useState(true);
  const [activity, setActivity] = useState<ActivityItem[]>([]);

  useEffect(() => {
    const loadStats = async () => {
      setStatsLoading(true);
      try {
        const [reports, dashboards] = await Promise.allSettled([getReports(), getDashboards()]);
        const reportCount = reports.status === 'fulfilled' ? reports.value.length : 0;
        const dashboardCount = dashboards.status === 'fulfilled' ? dashboards.value.length : 0;

        // Load query count from localStorage history
        let queryCount = 0;
        try {
          const h = localStorage.getItem('nlp_query_history');
          if (h) queryCount = JSON.parse(h).length;
        } catch {
          // ignore
        }

        setStats({
          total_datasets: datasets.length,
          total_queries: queryCount,
          active_dashboards: dashboardCount,
          reports_generated: reportCount,
        });

        // Build activity from datasets
        const acts: ActivityItem[] = datasets.slice(0, 5).map((d) => ({
          id: d.id,
          type: 'upload' as const,
          title: `Uploaded "${d.name}"`,
          subtitle: `${d.row_count?.toLocaleString() ?? '?'} rows · ${d.column_count} columns`,
          timestamp: d.created_at,
        }));
        setActivity(acts);
      } catch {
        // ignore
      } finally {
        setStatsLoading(false);
      }
    };
    loadStats();
  }, [datasets]);

  const activityTypeColor = (type: ActivityItem['type']) => {
    const map = { upload: '#1976d2', query: '#00897b', dashboard: '#ed6c02', report: '#7b1fa2' };
    return map[type] || '#64748b';
  };

  return (
    <Box>
      {/* Hero Banner */}
      <Paper
        elevation={0}
        sx={{
          background: 'linear-gradient(135deg, #1565c0 0%, #0277bd 50%, #00695c 100%)',
          borderRadius: 3,
          p: { xs: 3, md: 5 },
          mb: 4,
          color: 'white',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Decorative circles */}
        <Box
          sx={{
            position: 'absolute',
            top: -40,
            right: -40,
            width: 200,
            height: 200,
            borderRadius: '50%',
            backgroundColor: 'rgba(255,255,255,0.05)',
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: -60,
            right: 80,
            width: 150,
            height: 150,
            borderRadius: '50%',
            backgroundColor: 'rgba(255,255,255,0.05)',
          }}
        />

        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <AutoAwesomeIcon sx={{ fontSize: 32 }} />
            <Chip
              label="AI-Powered"
              size="small"
              sx={{
                backgroundColor: 'rgba(255,255,255,0.2)',
                color: 'white',
                fontWeight: 700,
                backdropFilter: 'blur(4px)',
              }}
            />
          </Box>
          <Typography variant="h3" fontWeight={800} gutterBottom sx={{ maxWidth: 600 }}>
            NLP Data Intelligence Platform
          </Typography>
          <Typography
            variant="subtitle1"
            sx={{ color: 'rgba(255,255,255,0.85)', maxWidth: 500, mb: 3 }}
          >
            Query your datasets using plain English. No SQL needed. Upload data, ask questions, and
            discover insights instantly.
          </Typography>
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              size="large"
              startIcon={<PsychologyIcon />}
              onClick={() => navigate('/query')}
              sx={{
                backgroundColor: 'white',
                color: '#1565c0',
                '&:hover': { backgroundColor: '#f8fafc' },
                fontWeight: 700,
              }}
            >
              Start Querying
            </Button>
            <Button
              variant="outlined"
              size="large"
              startIcon={<CloudUploadIcon />}
              onClick={() => navigate('/datasets')}
              sx={{
                borderColor: 'rgba(255,255,255,0.5)',
                color: 'white',
                '&:hover': {
                  borderColor: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                },
              }}
            >
              Upload Data
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* Stats Grid */}
      <Grid container spacing={2.5} sx={{ mb: 4 }}>
        <Grid item xs={6} md={3}>
          <StatCard
            label="Total Datasets"
            value={statsLoading ? '—' : stats.total_datasets}
            icon={<StorageIcon />}
            color="#1976d2"
            subtitle="Uploaded datasets"
            loading={statsLoading}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            label="Queries Run"
            value={statsLoading ? '—' : stats.total_queries}
            icon={<PsychologyIcon />}
            color="#00897b"
            subtitle="NLP & SQL queries"
            loading={statsLoading}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            label="Dashboards"
            value={statsLoading ? '—' : stats.active_dashboards}
            icon={<GridViewIcon />}
            color="#ed6c02"
            subtitle="Active dashboards"
            loading={statsLoading}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            label="Reports"
            value={statsLoading ? '—' : stats.reports_generated}
            icon={<AssessmentIcon />}
            color="#7b1fa2"
            subtitle="Generated reports"
            loading={statsLoading}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Recent Activity */}
        <Grid item xs={12} md={7}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6" fontWeight={700}>
                  Recent Activity
                </Typography>
                <Button size="small" color="primary" onClick={() => navigate('/datasets')}>
                  View All
                </Button>
              </Box>

              {datasetsLoading ? (
                <Box>
                  {[...Array(4)].map((_, i) => (
                    <Box key={i} sx={{ display: 'flex', gap: 1.5, mb: 2 }}>
                      <Skeleton variant="circular" width={36} height={36} />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton width="60%" height={20} />
                        <Skeleton width="40%" height={16} />
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : activity.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                  <StorageIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
                  <Typography color="text.secondary">No activity yet</Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<CloudUploadIcon />}
                    onClick={() => navigate('/datasets')}
                    sx={{ mt: 1.5 }}
                  >
                    Upload Your First Dataset
                  </Button>
                </Box>
              ) : (
                <List disablePadding>
                  {activity.map((item, i) => (
                    <React.Fragment key={item.id}>
                      <ListItem disablePadding sx={{ py: 1 }}>
                        <ListItemIcon sx={{ minWidth: 44 }}>
                          <Avatar
                            sx={{
                              width: 36,
                              height: 36,
                              backgroundColor: alpha(activityTypeColor(item.type), 0.12),
                            }}
                          >
                            <FiberManualRecordIcon
                              sx={{ fontSize: 14, color: activityTypeColor(item.type) }}
                            />
                          </Avatar>
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" fontWeight={600}>
                              {item.title}
                            </Typography>
                          }
                          secondary={
                            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 0.25 }}>
                              <Typography variant="caption" color="text.secondary">
                                {item.subtitle}
                              </Typography>
                              <Typography variant="caption" color="text.disabled">
                                ·
                              </Typography>
                              <Typography variant="caption" color="text.disabled">
                                {formatRelativeTime(item.timestamp)}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                      {i < activity.length - 1 && <Divider component="li" variant="inset" />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="h6" fontWeight={700} gutterBottom>
                Quick Actions
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<UploadFileIcon />}
                  onClick={() => navigate('/datasets')}
                  sx={{ justifyContent: 'flex-start', py: 1.5, px: 2 }}
                >
                  <Box sx={{ textAlign: 'left' }}>
                    <Typography variant="body2" fontWeight={600}>
                      Upload Dataset
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      CSV, Excel files supported
                    </Typography>
                  </Box>
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  color="secondary"
                  startIcon={<SearchIcon />}
                  onClick={() => navigate('/query')}
                  sx={{ justifyContent: 'flex-start', py: 1.5, px: 2 }}
                >
                  <Box sx={{ textAlign: 'left' }}>
                    <Typography variant="body2" fontWeight={600}>
                      New NLP Query
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Ask questions in plain English
                    </Typography>
                  </Box>
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  color="warning"
                  startIcon={<DashboardCustomizeIcon />}
                  onClick={() => navigate('/dashboards')}
                  sx={{ justifyContent: 'flex-start', py: 1.5, px: 2 }}
                >
                  <Box sx={{ textAlign: 'left' }}>
                    <Typography variant="body2" fontWeight={600}>
                      Create Dashboard
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Drag-and-drop widgets
                    </Typography>
                  </Box>
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  color="error"
                  startIcon={<AssessmentIcon />}
                  onClick={() => navigate('/reports')}
                  sx={{ justifyContent: 'flex-start', py: 1.5, px: 2 }}
                >
                  <Box sx={{ textAlign: 'left' }}>
                    <Typography variant="body2" fontWeight={600}>
                      Generate Report
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      AI-powered analytics report
                    </Typography>
                  </Box>
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Getting Started */}
        <Grid item xs={12}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
            Getting Started
          </Typography>
          <Grid container spacing={2.5}>
            <Grid item xs={12} md={4}>
              <StepCard
                step={1}
                title="Upload Your Data"
                description="Upload CSV or Excel files. The platform will automatically analyze your data, detect column types, and compute statistics."
                icon={<CloudUploadIcon />}
                action="Upload Dataset"
                onAction={() => navigate('/datasets')}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <StepCard
                step={2}
                title="Query with Natural Language"
                description='Ask questions like "Show me top 10 products by revenue" or "What is the monthly trend?" No SQL knowledge required.'
                icon={<PsychologyIcon />}
                action="Open Query"
                onAction={() => navigate('/query')}
                color="#00897b"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <StepCard
                step={3}
                title="Build Dashboards & Reports"
                description="Combine multiple queries into interactive dashboards. Generate comprehensive reports with one click."
                icon={<AddIcon />}
                action="Create Dashboard"
                onAction={() => navigate('/dashboards')}
                color="#ed6c02"
              />
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default HomePage;
