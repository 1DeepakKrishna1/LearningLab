import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import {
  Box,
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Avatar,
  Menu,
  MenuItem,
  Tooltip,
  useMediaQuery,
  useTheme,
  Breadcrumbs,
  Link,
  Chip,
  Divider,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import NotificationsOutlinedIcon from '@mui/icons-material/NotificationsOutlined';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useLocation } from 'react-router-dom';
import Sidebar, { DRAWER_WIDTH } from './Sidebar';
import { useDatasets } from '../../hooks/useDatasets';

const routeLabels: Record<string, string> = {
  '/': 'Home',
  '/datasets': 'Datasets',
  '/query': 'NLP Query',
  '/dashboards': 'Dashboards',
  '/reports': 'Reports',
};

const Layout: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const location = useLocation();
  const navigate = useNavigate();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);

  const { datasets } = useDatasets();

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleUserMenuOpen = (e: React.MouseEvent<HTMLElement>) => setUserMenuAnchor(e.currentTarget);
  const handleUserMenuClose = () => setUserMenuAnchor(null);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Breadcrumbs
  const pathSegments = location.pathname.split('/').filter(Boolean);
  const currentLabel =
    routeLabels[location.pathname] ||
    (pathSegments.length > 0
      ? pathSegments[pathSegments.length - 1].charAt(0).toUpperCase() +
        pathSegments[pathSegments.length - 1].slice(1)
      : 'Home');

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <Sidebar
        open={isMobile ? mobileOpen : true}
        onClose={() => setMobileOpen(false)}
        variant={isMobile ? 'temporary' : 'permanent'}
        datasetCount={datasets.length}
      />

      {/* Main area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
          overflow: 'hidden',
          backgroundColor: 'background.default',
          ml: isMobile ? 0 : 0,
        }}
      >
        {/* AppBar */}
        <AppBar
          position="sticky"
          elevation={0}
          sx={{
            backgroundColor: 'background.paper',
            borderBottom: '1px solid',
            borderColor: 'divider',
            color: 'text.primary',
            zIndex: theme.zIndex.drawer - 1,
          }}
        >
          <Toolbar sx={{ gap: 1, minHeight: '64px !important' }}>
            {isMobile && (
              <IconButton
                edge="start"
                aria-label="open navigation"
                onClick={handleDrawerToggle}
                sx={{ color: 'text.secondary' }}
              >
                <MenuIcon />
              </IconButton>
            )}

            {/* Logo on mobile */}
            {isMobile && (
              <Box
                sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }}
                onClick={() => navigate('/')}
              >
                <Box
                  sx={{
                    width: 28,
                    height: 28,
                    borderRadius: 1.5,
                    background: 'linear-gradient(135deg, #1976d2, #00897b)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <AutoAwesomeIcon sx={{ color: 'white', fontSize: 16 }} />
                </Box>
                <Typography variant="subtitle1" fontWeight={700}>
                  NLP Intelligence
                </Typography>
              </Box>
            )}

            {/* Breadcrumbs on desktop */}
            {!isMobile && (
              <Breadcrumbs aria-label="breadcrumb" sx={{ flexGrow: 1 }}>
                <Link
                  underline="hover"
                  color="text.secondary"
                  href="/"
                  onClick={(e) => { e.preventDefault(); navigate('/'); }}
                  sx={{ fontSize: '0.875rem', fontWeight: 500 }}
                >
                  Home
                </Link>
                {pathSegments.length > 0 && (
                  <Typography
                    sx={{ fontSize: '0.875rem', fontWeight: 600, color: 'text.primary' }}
                  >
                    {currentLabel}
                  </Typography>
                )}
              </Breadcrumbs>
            )}

            {isMobile && <Box sx={{ flexGrow: 1 }} />}

            {/* Status chip */}
            <Chip
              label="Connected"
              size="small"
              color="success"
              variant="outlined"
              sx={{
                display: { xs: 'none', sm: 'flex' },
                fontSize: '0.75rem',
                height: 24,
              }}
            />

            {/* Help */}
            <Tooltip title="Help & Documentation">
              <IconButton size="small" sx={{ color: 'text.secondary' }}>
                <HelpOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>

            {/* Notifications */}
            <Tooltip title="Notifications">
              <IconButton size="small" sx={{ color: 'text.secondary' }}>
                <NotificationsOutlinedIcon fontSize="small" />
              </IconButton>
            </Tooltip>

            <Divider orientation="vertical" flexItem sx={{ mx: 0.5, my: 1 }} />

            {/* User menu */}
            <Tooltip title="User Menu">
              <Box
                onClick={handleUserMenuOpen}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  cursor: 'pointer',
                  borderRadius: 2,
                  px: 1,
                  py: 0.5,
                  '&:hover': { backgroundColor: 'action.hover' },
                }}
              >
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    backgroundColor: 'primary.main',
                    fontSize: '0.875rem',
                    fontWeight: 700,
                  }}
                >
                  DK
                </Avatar>
                <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
                  <Typography variant="caption" fontWeight={600} display="block" lineHeight={1.2}>
                    Deepak
                  </Typography>
                  <Typography variant="caption" color="text.secondary" lineHeight={1.2}>
                    Admin
                  </Typography>
                </Box>
                <KeyboardArrowDownIcon fontSize="small" sx={{ color: 'text.secondary' }} />
              </Box>
            </Tooltip>

            <Menu
              anchorEl={userMenuAnchor}
              open={Boolean(userMenuAnchor)}
              onClose={handleUserMenuClose}
              transformOrigin={{ horizontal: 'right', vertical: 'top' }}
              anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
              PaperProps={{
                elevation: 3,
                sx: { mt: 0.5, minWidth: 160, borderRadius: 2 },
              }}
            >
              <MenuItem disabled>
                <Box>
                  <Typography variant="subtitle2">Deepak Krishna</Typography>
                  <Typography variant="caption" color="text.secondary">
                    deepak.krishna@exelcius.com
                  </Typography>
                </Box>
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleUserMenuClose}>Profile Settings</MenuItem>
              <MenuItem onClick={handleUserMenuClose}>Preferences</MenuItem>
              <Divider />
              <MenuItem onClick={handleUserMenuClose} sx={{ color: 'error.main' }}>
                Sign Out
              </MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        {/* Page content */}
        <Box
          sx={{
            flexGrow: 1,
            overflow: 'auto',
            p: { xs: 2, sm: 3 },
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;
