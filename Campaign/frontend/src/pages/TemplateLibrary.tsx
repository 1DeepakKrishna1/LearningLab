import { useState } from 'react';
import {
  Alert, Box, Button, Card, CardActions, CardContent, Chip, Dialog, DialogActions,
  DialogContent, DialogTitle, Grid, IconButton, MenuItem, Stack, TextField, Typography,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ArchiveIcon from '@mui/icons-material/Archive';
import DeleteIcon from '@mui/icons-material/Delete';
import { useTemplates, useSaveTemplate, useTemplateAction, useDeleteTemplate } from '../api/hooks';
import { PageHeader, Loading, EmptyState, ConfirmDialog } from '../components/shared';
import { useAuth } from '../store/auth';
import { apiErrorMessage } from '../api/client';
import type { Channel, Template } from '../types';

const BLANK: Partial<Template> = { name: '', channel: 'email', category: 'general', variables: [] };

export default function TemplateLibrary() {
  const [channel, setChannel] = useState('');
  const [q, setQ] = useState('');
  const [editor, setEditor] = useState<Partial<Template> | null>(null);
  const [toDelete, setToDelete] = useState<number | null>(null);
  const [error, setError] = useState('');
  const canEdit = useAuth((s) => s.hasRole('admin', 'marketer'));

  const { data, isLoading } = useTemplates({ channel: channel || undefined, q: q || undefined, page_size: 100 });
  const save = useSaveTemplate();
  const action = useTemplateAction();
  const del = useDeleteTemplate();

  const submit = async () => {
    if (!editor) return;
    setError('');
    try {
      const body: Partial<Template> = { ...editor };
      await save.mutateAsync({ id: editor.id, body });
      setEditor(null);
    } catch (err) { setError(apiErrorMessage(err)); }
  };

  return (
    <Box>
      <PageHeader title="Template Library" subtitle="Email, SMS & push templates with personalization"
        action={canEdit && <Button variant="contained" onClick={() => setEditor({ ...BLANK })}>New Template</Button>} />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <TextField size="small" label="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <TextField size="small" select label="Channel" value={channel} onChange={(e) => setChannel(e.target.value)} sx={{ minWidth: 160 }}>
          <MenuItem value="">All</MenuItem>
          <MenuItem value="email">Email</MenuItem>
          <MenuItem value="sms">SMS</MenuItem>
          <MenuItem value="push">Push</MenuItem>
        </TextField>
      </Stack>

      {isLoading ? <Loading /> : (data?.items.length ?? 0) === 0 ? (
        <EmptyState title="No templates" hint="Create your first template to use in campaigns." />
      ) : (
        <Grid container spacing={2}>
          {data!.items.map((t) => (
            <Grid item xs={12} sm={6} md={4} key={t.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                    <Chip size="small" label={t.channel} color="primary" />
                    <Chip size="small" label={t.status} variant="outlined" />
                    <Chip size="small" label={`v${t.version}`} variant="outlined" />
                  </Stack>
                  <Typography variant="h6" noWrap>{t.name}</Typography>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {t.subject || t.text_content || t.title || t.category}
                  </Typography>
                </CardContent>
                {canEdit && (
                  <CardActions>
                    <Button size="small" onClick={() => setEditor(t)}>Edit</Button>
                    <IconButton size="small" title="Clone" onClick={() => action.mutate({ id: t.id, action: 'clone' })}><ContentCopyIcon fontSize="small" /></IconButton>
                    <IconButton size="small" title="Archive" onClick={() => action.mutate({ id: t.id, action: 'archive' })}><ArchiveIcon fontSize="small" /></IconButton>
                    <IconButton size="small" color="error" title="Delete" onClick={() => setToDelete(t.id)}><DeleteIcon fontSize="small" /></IconButton>
                  </CardActions>
                )}
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={!!editor} onClose={() => setEditor(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{editor?.id ? 'Edit Template' : 'New Template'}</DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {editor && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField label="Name" value={editor.name ?? ''} onChange={(e) => setEditor({ ...editor, name: e.target.value })} fullWidth />
              <TextField select label="Channel" value={editor.channel} disabled={!!editor.id}
                onChange={(e) => setEditor({ ...editor, channel: e.target.value as Channel })} fullWidth>
                <MenuItem value="email">Email</MenuItem>
                <MenuItem value="sms">SMS</MenuItem>
                <MenuItem value="push">Push</MenuItem>
              </TextField>
              <TextField label="Category" value={editor.category ?? ''} onChange={(e) => setEditor({ ...editor, category: e.target.value })} fullWidth />
              {editor.channel === 'email' && (<>
                <TextField label="Subject" value={editor.subject ?? ''} onChange={(e) => setEditor({ ...editor, subject: e.target.value })} fullWidth />
                <TextField label="Preheader" value={editor.preheader ?? ''} onChange={(e) => setEditor({ ...editor, preheader: e.target.value })} fullWidth />
                <TextField label="HTML content" value={editor.html_content ?? ''} onChange={(e) => setEditor({ ...editor, html_content: e.target.value })} multiline rows={5} fullWidth
                  helperText="Use {{first_name}} etc. for personalization." />
              </>)}
              {editor.channel === 'sms' && (
                <TextField label="Text content" value={editor.text_content ?? ''} onChange={(e) => setEditor({ ...editor, text_content: e.target.value })} multiline rows={3} fullWidth
                  helperText={`${(editor.text_content ?? '').length} chars`} />
              )}
              {editor.channel === 'push' && (<>
                <TextField label="Title" value={editor.title ?? ''} onChange={(e) => setEditor({ ...editor, title: e.target.value })} fullWidth />
                <TextField label="Body" value={editor.body ?? ''} onChange={(e) => setEditor({ ...editor, body: e.target.value })} multiline rows={3} fullWidth />
                <TextField label="Image URL" value={editor.image_url ?? ''} onChange={(e) => setEditor({ ...editor, image_url: e.target.value })} fullWidth />
                <TextField label="Deep link" value={editor.deep_link ?? ''} onChange={(e) => setEditor({ ...editor, deep_link: e.target.value })} fullWidth />
              </>)}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditor(null)}>Cancel</Button>
          <Button variant="contained" onClick={submit} disabled={save.isPending}>Save</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog open={toDelete !== null} title="Delete template?" message="This cannot be undone."
        danger confirmText="Delete" onClose={() => setToDelete(null)}
        onConfirm={() => toDelete && del.mutate(toDelete)} />
    </Box>
  );
}
