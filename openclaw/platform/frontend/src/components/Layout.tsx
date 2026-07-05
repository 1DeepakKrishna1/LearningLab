import { Outlet, NavLink, useNavigate } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Chip,
} from "@mui/material";
import {
  LayoutDashboard,
  Workflow,
  PlayCircle,
  Bot,
  Wrench,
  UserCheck,
  ScrollText,
  Settings as SettingsIcon,
  MessageSquare,
  LogOut,
} from "lucide-react";
import { useAuth } from "../store/auth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workflows", label: "Workflows", icon: Workflow },
  { to: "/executions", label: "Executions", icon: PlayCircle },
  { to: "/agents", label: "Agent Manager", icon: Bot },
  { to: "/tools", label: "Tool Library", icon: Wrench },
  { to: "/approvals", label: "Approvals", icon: UserCheck },
  { to: "/audit", label: "Audit Logs", icon: ScrollText },
  { to: "/chatbot", label: "AI Chatbot", icon: MessageSquare },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

const DRAWER_WIDTH = 240;

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <Box sx={{ display: "flex", height: "100vh" }}>
      <AppBar position="fixed" elevation={0} sx={{ zIndex: 1300, bgcolor: "#1e1b4b" }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            🦅 ClawFlow
            <Typography component="span" sx={{ ml: 1, opacity: 0.6, fontSize: 13 }}>
              Agentic Workflow Automation
            </Typography>
          </Typography>
          <Chip
            size="small"
            label={user?.role}
            sx={{ mr: 2, bgcolor: "rgba(255,255,255,0.15)", color: "#fff" }}
          />
          <Typography sx={{ mr: 1 }}>{user?.name || user?.email}</Typography>
          <Avatar sx={{ width: 32, height: 32, bgcolor: "#6366F1" }}>
            {(user?.name || user?.email || "?")[0]?.toUpperCase()}
          </Avatar>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <List sx={{ flexGrow: 1 }}>
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} style={{ textDecoration: "none", color: "inherit" }} end={to === "/"}>
              {({ isActive }) => (
                <ListItemButton selected={isActive}>
                  <ListItemIcon sx={{ minWidth: 38 }}>
                    <Icon size={20} />
                  </ListItemIcon>
                  <ListItemText primary={label} />
                </ListItemButton>
              )}
            </NavLink>
          ))}
        </List>
        <List>
          <ListItemButton onClick={() => { logout(); navigate("/login"); }}>
            <ListItemIcon sx={{ minWidth: 38 }}>
              <LogOut size={20} />
            </ListItemIcon>
            <ListItemText primary="Log out" />
          </ListItemButton>
        </List>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, overflow: "auto", bgcolor: "#f5f6fa" }}>
        <Toolbar />
        <Box sx={{ p: 3 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
