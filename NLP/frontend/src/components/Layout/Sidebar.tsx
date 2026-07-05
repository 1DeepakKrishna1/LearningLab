import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Badge,
  Chip,
  Tooltip,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import StorageIcon from '@mui/icons-material/Storage';
import PsychologyIcon from '@mui/icons-material/Psychology';
import GridViewIcon from '@mui/icons-material/GridView';
import AssessmentIcon from '@mui/icons-material/Assessment';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

export const DRAWER_WIDTH = 240;

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  badge?: number;
  chip?: string;
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  variant: 'permanent' | 'temporary';
  datasetCount?: number;
}

const Sidebar: React.FC<SidebarProps> = ({ open, onClose, variant, datasetCount }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems: NavItem[] = [
    {
      label: 'Home',
      path: '/',
      icon: <DashboardIcon />,
    },
    {
      label: 'Datasets',
      path: '/datasets',
      icon: <StorageIcon />,
      badge: datasetCount,
    },
    {
      label: 'NLP Query',
      path: '/query',
      icon: <PsychologyIcon />,
      chip: 'AI',
    },
    {
      label: 'Dashboards',
      path: '/dashboards',
      icon: <GridViewIcon />,
    },
    {
      label: 'Reports',
      path: '/reports',
      icon: <AssessmentIcon />,
    },
  ];

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    if (variant === 'temporary') onClose();
  };

  const drawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo / Brand */}
      <Box
        sx={{
          px: 2.5,
          py: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
        }}
      >
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: 2,
            background: 'linear-gradient(135deg, #1976d2, #00897b)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <AutoAwesomeIcon sx={{ color: 'white', fontSize: 20 }} />
        </Box>
        <Box>
          <Typography
            variant="subtitle1"
            sx={{
              fontWeight: 700,
              color: 'text.primary',
              lineHeight: 1.2,
              fontSize: '0.9375rem',
            }}
          >
            NLP Intelligence
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Data Platform
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ borderColor: 'divider' }} />

      {/* Navigation */}
      <Box sx={{ flexGrow: 1, py: 1.5, overflowY: 'auto' }}>
        <Typography
          variant="overline"
          sx={{
            px: 2.5,
            mb: 1,
            display: 'block',
            color: 'text.secondary',
            fontSize: '0.6875rem',
          }}
        >
          Navigation
        </Typography>
        <List disablePadding>
          {navItems.map((item) => (
            <ListItem key={item.path} disablePadding sx={{ display: 'block', mb: 0.25 }}>
              <Tooltip title={item.label} placement="right" disableHoverListener>
                <ListItemButton
                  selected={isActive(item.path)}
                  onClick={() => handleNavigate(item.path)}
                  sx={{
                    minHeight: 44,
                    py: 1,
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 36,
                      color: isActive(item.path) ? 'primary.main' : 'text.secondary',
                    }}
                  >
                    {item.badge !== undefined && item.badge > 0 ? (
                      <Badge badgeContent={item.badge} color="primary" max={99}>
                        {item.icon}
                      </Badge>
                    ) : (
                      item.icon
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{
                      fontSize: '0.9375rem',
                      fontWeight: isActive(item.path) ? 600 : 500,
                      color: isActive(item.path) ? 'primary.main' : 'text.primary',
                    }}
                  />
                  {item.chip && (
                    <Chip
                      label={item.chip}
                      size="small"
                      color="secondary"
                      sx={{
                        height: 20,
                        fontSize: '0.625rem',
                        fontWeight: 700,
                        ml: 0.5,
                      }}
                    />
                  )}
                </ListItemButton>
              </Tooltip>
            </ListItem>
          ))}
        </List>
      </Box>

      <Divider sx={{ borderColor: 'divider' }} />

      {/* Footer */}
      <Box sx={{ px: 2.5, py: 2 }}>
        <Typography variant="caption" color="text.secondary" display="block">
          v1.0.0 — NLP Platform
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          borderRight: '1px solid',
          borderColor: 'divider',
          backgroundColor: 'background.paper',
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
};

export default Sidebar;
