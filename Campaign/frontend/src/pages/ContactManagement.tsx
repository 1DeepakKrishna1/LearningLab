import { useRef, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  Stack, TextField, Typography,
} from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { useContacts, useSaveContact, useImportContacts } from '../api/hooks';
import { PageHeader, ErrorState } from '../components/shared';
import { useAuth } from '../store/auth';
import { apiErrorMessage } from '../api/client';
import type { Contact } from '../types';

export default function ContactManagement() {
  const [q, setQ] = useState('');
  const [editor, setEditor] = useState<Partial<Contact> | null>(null);
  const [importResult, setImportResult] = useState<string>('');
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const canEdit = useAuth((s) => s.hasRole('admin', 'marketer'));

  const { data, isLoading, error: qErr } = useContacts({ q: q || undefined, page_size: 100 });
  const save = useSaveContact();
  const importMut = useImportContacts();

  const columns: GridColDef[] = [
    { field: 'email', headerName: 'Email', flex: 1, minWidth: 200 },
    { field: 'first_name', headerName: 'First', width: 120 },
    { field: 'last_name', headerName: 'Last', width: 120 },
    { field: 'country', headerName: 'Country', width: 90 },
    { field: 'tags', headerName: 'Tags', flex: 1, minWidth: 160,
      renderCell: (p) => <Stack direction="row" spacing={0.5}>{(p.value as string[]).map((t) => <Chip key={t} size="small" label={t} />)}</Stack> },
  ];

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(''); setImportResult('');
    try {
      const r = await importMut.mutateAsync(file);
      setImportResult(`Imported: ${r.created} created, ${r.updated} updated, ${r.skipped} skipped.`);
    } catch (err) { setError(apiErrorMessage(err)); }
    if (fileRef.current) fileRef.current.value = '';
  };

  const submit = async () => {
    if (!editor) return;
    setError('');
    try {
      await save.mutateAsync({ id: editor.id, body: editor });
      setEditor(null);
    } catch (err) { setError(apiErrorMessage(err)); }
  };

  return (
    <Box>
      <PageHeader title="Contacts" subtitle="Manage your audience"
        action={canEdit && (
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => fileRef.current?.click()}>Import CSV</Button>
            <Button variant="contained" onClick={() => setEditor({ tags: [], attributes: {}, timezone: 'UTC' })}>Add Contact</Button>
            <input ref={fileRef} type="file" accept=".csv" hidden onChange={onFile} />
          </Stack>
        )} />

      {importResult && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setImportResult('')}>{importResult}</Alert>}
      {(error || qErr) && <ErrorState message={error || apiErrorMessage(qErr)} />}
      <TextField size="small" label="Search" value={q} onChange={(e) => setQ(e.target.value)} sx={{ mb: 2, minWidth: 240 }} />

      <Card>
        <DataGrid autoHeight rows={data?.items ?? []} columns={columns} loading={isLoading}
          onRowClick={(p) => canEdit && setEditor(p.row as Contact)}
          disableRowSelectionOnClick pageSizeOptions={[10, 25, 50]}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }} sx={{ border: 0 }} />
      </Card>

      <Dialog open={!!editor} onClose={() => setEditor(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{editor?.id ? 'Edit Contact' : 'Add Contact'}</DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {editor && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField label="Email" value={editor.email ?? ''} onChange={(e) => setEditor({ ...editor, email: e.target.value })} fullWidth />
              <TextField label="Phone" value={editor.phone ?? ''} onChange={(e) => setEditor({ ...editor, phone: e.target.value })} fullWidth />
              <Stack direction="row" spacing={2}>
                <TextField label="First name" value={editor.first_name ?? ''} onChange={(e) => setEditor({ ...editor, first_name: e.target.value })} fullWidth />
                <TextField label="Last name" value={editor.last_name ?? ''} onChange={(e) => setEditor({ ...editor, last_name: e.target.value })} fullWidth />
              </Stack>
              <TextField label="Country (ISO-2)" value={editor.country ?? ''} onChange={(e) => setEditor({ ...editor, country: e.target.value })} fullWidth />
              <TextField label="Tags (comma separated)" value={(editor.tags ?? []).join(', ')}
                onChange={(e) => setEditor({ ...editor, tags: e.target.value.split(',').map((t) => t.trim()).filter(Boolean) })} fullWidth />
              <Typography variant="caption" color="text.secondary">CSV columns: email, phone, first_name, last_name, country, timezone, tags (use ; between tags). Unknown columns become attributes.</Typography>
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
