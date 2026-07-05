import { useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar, Avatar, Box, Divider, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, Menu, MenuItem, Toolbar, Typography, useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import CampaignIcon from '@mui/icons-material/Campaign';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import DescriptionIcon from '@mui/icons-material/Description';
import PeopleIcon from '@mui/icons-material/People';
import SegmentIcon from '@mui/icons-material/Segment';
import BarChartIcon from '@mui/icons-material/BarChart';
import AssessmentIcon from '@mui/icons-material/Assessment';
import SettingsInputComponentIcon from '@mui/icons-material/SettingsInputComponent';
import ManageAccountsIcon from '@mui/icons-material/ManageAccounts';
import HistoryIcon from '@mui/icons-material/History';
import { useAuth } from '../store/auth';

const DRAWER_WIDTH = 248;

interface NavItem { label: string; to: string; icon: React.ReactNode; roles?: string[] }
const NAV: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: <DashboardIcon /> },
  { label: 'Campaigns', to: '/campaigns', icon: <CampaignIcon /> },
  { label: 'Calendar', to: '/calendar', icon: <CalendarMonthIcon /> },
  { label: 'Templates', to: '/templates', icon: <DescriptionIcon /> },
  { label: 'Contacts', to: '/contacts', icon: <PeopleIcon /> },
  { label: 'Segments', to: '/segments', icon: <SegmentIcon /> },
  { label: 'Analytics', to: '/analytics', icon: <BarChartIcon /> },
  { label: 'Reports', to: '/reports', icon: <AssessmentIcon /> },
  { label: 'Providers', to: '/providers', icon: <SettingsInputComponentIcon />, roles: ['admin', 'marketer'] },
  { label: 'Users', to: '/users', icon: <ManageAccountsIcon />, roles: ['admin'] },
  { label: 'Audit Logs', to: '/audit', icon: <HistoryIcon />, roles: ['admin'] },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, hasRole } = useAuth();

  const visibleNav = NAV.filter((n) => !n.roles || hasRole(...n.roles));

  const drawer = (
    <Box>
      <Toolbar>
        <CampaignIcon color="primary" sx={{ mr: 1 }} />
        <Typography variant="h6" fontWeight={700} noWrap>CampaignHub</Typography>
      </Toolbar>
      <Divider />
      <List>
        {visibleNav.map((item) => {
          const selected = item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to);
          return (
            <ListItemButton
              key={item.to}
              component={RouterLink}
              to={item.to}
              selected={selected}
              onClick={() => isMobile && setMobileOpen(false)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" color="inherit" elevation={0}
        sx={{ borderBottom: '1px solid #e0e0e0', zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          {isMobile && (
            <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Typography variant="body2" sx={{ mr: 1, display: { xs: 'none', sm: 'block' } }}>
            {user?.full_name} · {user?.roles.map((r) => r.name).join(', ')}
          </Typography>
          <IconButton onClick={(e) => setAnchor(e.currentTarget)} size="small">
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
              {user?.full_name?.[0]?.toUpperCase()}
            </Avatar>
          </IconButton>
          <Menu anchorEl={anchor} open={!!anchor} onClose={() => setAnchor(null)}>
            <MenuItem disabled>{user?.email}</MenuItem>
            <Divider />
            <MenuItem onClick={async () => { await logout(); navigate('/login'); }}>Logout</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? mobileOpen : true}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' } }}
        >
          {drawer}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 3 }, width: { md: `calc(100% - ${DRAWER_WIDTH}px)` } }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
