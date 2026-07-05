import { useState } from 'react';
import {
  Alert, Box, Button, Card, Checkbox, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, FormControlLabel, Stack, TextField, Typography,
} from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import { useUsers, useSaveUser } from '../api/hooks';
import { PageHeader, ErrorState } from '../components/shared';
import { apiErrorMessage } from '../api/client';
import type { User } from '../types';

const ALL_ROLES = ['admin', 'marketer', 'viewer'];

interface Editor { id?: number; email: string; full_name: string; password: string; roles: string[]; is_active: boolean }

export default function UserManagement() {
  const { data, isLoading, error } = useUsers();
  const save = useSaveUser();
  const [editor, setEditor] = useState<Editor | null>(null);
  const [err, setErr] = useState('');

  const columns: GridColDef[] = [
    { field: 'email', headerName: 'Email', flex: 1, minWidth: 200 },
    { field: 'full_name', headerName: 'Name', flex: 1, minWidth: 150 },
    { field: 'roles', headerName: 'Roles', flex: 1, minWidth: 180,
      renderCell: (p) => <Stack direction="row" spacing={0.5}>{(p.value as User['roles']).map((r) => <Chip key={r.id} size="small" label={r.name} />)}</Stack> },
    { field: 'is_active', headerName: 'Active', width: 90, type: 'boolean' },
  ];

  const submit = async () => {
    if (!editor) return;
    setErr('');
    try {
      const body: Record<string, unknown> = editor.id
        ? { full_name: editor.full_name, roles: editor.roles, is_active: editor.is_active }
        : { email: editor.email, full_name: editor.full_name, password: editor.password, roles: editor.roles };
      await save.mutateAsync({ id: editor.id, body });
      setEditor(null);
    } catch (e) { setErr(apiErrorMessage(e)); }
  };

  const toggleRole = (role: string) =>
    setEditor((e) => e && ({ ...e, roles: e.roles.includes(role) ? e.roles.filter((r) => r !== role) : [...e.roles, role] }));

  return (
    <Box>
      <PageHeader title="User Management" subtitle="Manage users and roles (Admin only)"
        action={<Button variant="contained" onClick={() => setEditor({ email: '', full_name: '', password: '', roles: ['viewer'], is_active: true })}>Add User</Button>} />
      {error && <ErrorState message={apiErrorMessage(error)} />}
      <Card>
        <DataGrid autoHeight rows={data ?? []} columns={columns} loading={isLoading}
          onRowClick={(p) => {
            const u = p.row as User;
            setEditor({ id: u.id, email: u.email, full_name: u.full_name, password: '', roles: u.roles.map((r) => r.name), is_active: u.is_active });
          }}
          disableRowSelectionOnClick sx={{ border: 0 }} />
      </Card>

      <Dialog open={!!editor} onClose={() => setEditor(null)} maxWidth="xs" fullWidth>
        <DialogTitle>{editor?.id ? 'Edit User' : 'Add User'}</DialogTitle>
        <DialogContent>
          {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
          {editor && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField label="Email" value={editor.email} disabled={!!editor.id}
                onChange={(e) => setEditor({ ...editor, email: e.target.value })} fullWidth />
              <TextField label="Full name" value={editor.full_name}
                onChange={(e) => setEditor({ ...editor, full_name: e.target.value })} fullWidth />
              {!editor.id && (
                <TextField label="Password" type="password" value={editor.password}
                  onChange={(e) => setEditor({ ...editor, password: e.target.value })} fullWidth
                  helperText="Min 8 characters" />
              )}
              <Box>
                <Typography variant="body2" sx={{ mb: 1 }}>Roles</Typography>
                {ALL_ROLES.map((r) => (
                  <FormControlLabel key={r} control={<Checkbox checked={editor.roles.includes(r)} onChange={() => toggleRole(r)} />} label={r} />
                ))}
              </Box>
              {editor.id && (
                <FormControlLabel control={<Checkbox checked={editor.is_active} onChange={(e) => setEditor({ ...editor, is_active: e.target.checked })} />} label="Active" />
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditor(null)}>Cancel</Button>
          <Button variant="contained" onClick={submit} disabled={save.isPending}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
