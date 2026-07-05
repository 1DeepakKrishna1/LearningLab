// Small shared UI building blocks used across pages.
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogContentText, DialogTitle, Stack, Typography,
} from '@mui/material';
import type { CampaignStatus } from '../types';

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between"
      alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={2} sx={{ mb: 3 }}>
      <Box>
        <Typography variant="h5" fontWeight={700}>{title}</Typography>
        {subtitle && <Typography variant="body2" color="text.secondary">{subtitle}</Typography>}
      </Box>
      {action}
    </Stack>
  );
}

export function Loading() {
  return <Box sx={{ display: 'flex', justifyContent: 'center', p: 6 }}><CircularProgress /></Box>;
}

export function ErrorState({ message }: { message: string }) {
  return <Alert severity="error" sx={{ my: 2 }}>{message}</Alert>;
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <Box sx={{ textAlign: 'center', py: 8, color: 'text.secondary' }}>
      <Typography variant="h6">{title}</Typography>
      {hint && <Typography variant="body2" sx={{ mt: 1 }}>{hint}</Typography>}
      {action && <Box sx={{ mt: 2 }}>{action}</Box>}
    </Box>
  );
}

const STATUS_COLORS: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info'> = {
  draft: 'default', pending_approval: 'warning', approved: 'info', scheduled: 'info',
  sending: 'primary', completed: 'success', failed: 'error', paused: 'warning',
  cancelled: 'default', archived: 'default',
};

export function StatusChip({ status }: { status: CampaignStatus | string }) {
  return <Chip size="small" label={status.replace(/_/g, ' ')} color={STATUS_COLORS[status] ?? 'default'} />;
}

export function ConfirmDialog({
  open, title, message, onConfirm, onClose, confirmText = 'Confirm', danger = false,
}: {
  open: boolean; title: string; message: string; confirmText?: string; danger?: boolean;
  onConfirm: () => void; onClose: () => void;
}) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent><DialogContentText>{message}</DialogContentText></DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={() => { onConfirm(); onClose(); }} color={danger ? 'error' : 'primary'} variant="contained">
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
