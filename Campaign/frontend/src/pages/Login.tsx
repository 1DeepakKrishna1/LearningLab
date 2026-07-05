import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Alert, Box, Button, Card, CardContent, Stack, TextField, Typography,
} from '@mui/material';
import CampaignIcon from '@mui/icons-material/Campaign';
import { useAuth } from '../store/auth';
import { apiErrorMessage } from '../api/client';

export default function Login() {
  const { login, loading, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname: string } } };
  const [email, setEmail] = useState('admin@local');
  const [password, setPassword] = useState('Admin@123');
  const [error, setError] = useState('');

  if (user) navigate('/', { replace: true });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
      navigate(location.state?.from?.pathname ?? '/', { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      bgcolor: 'background.default', p: 2 }}>
      <Card sx={{ width: 400, maxWidth: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Stack alignItems="center" spacing={1} sx={{ mb: 3 }}>
            <CampaignIcon color="primary" sx={{ fontSize: 40 }} />
            <Typography variant="h5" fontWeight={700}>CampaignHub</Typography>
            <Typography variant="body2" color="text.secondary">Sign in to your account</Typography>
          </Stack>
          <form onSubmit={submit}>
            <Stack spacing={2}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField label="Email" value={email} onChange={(e) => setEmail(e.target.value)}
                fullWidth autoFocus autoComplete="username" />
              <TextField label="Password" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} fullWidth autoComplete="current-password" />
              <Button type="submit" variant="contained" size="large" disabled={loading}>
                {loading ? 'Signing in…' : 'Sign In'}
              </Button>
            </Stack>
          </form>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 3, textAlign: 'center' }}>
            Demo: admin@local / Admin@123 · marketer@local / Marketer@123 · viewer@local / Viewer@123
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
