import { useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, Grid, IconButton, MenuItem, Stack, TextField, ToggleButton,
  ToggleButtonGroup, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { useSegments, useSaveSegment, usePreviewSegment } from '../api/hooks';
import { PageHeader, Loading, EmptyState } from '../components/shared';
import { useAuth } from '../store/auth';
import { apiErrorMessage } from '../api/client';
import type { Condition, RuleGroup, Segment } from '../types';

const FIELDS = ['email', 'country', 'first_name', 'last_name', 'tags', 'attributes.plan', 'attributes.ltv'];
const OPERATORS = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'contains', 'in', 'is_set', 'is_not_set'];

export default function SegmentBuilder() {
  const canEdit = useAuth((s) => s.hasRole('admin', 'marketer'));
  const { data, isLoading } = useSegments();
  const save = useSaveSegment();
  const preview = usePreviewSegment();

  const [editor, setEditor] = useState<{ id?: number; name: string; description: string; op: 'AND' | 'OR'; rules: Condition[] } | null>(null);
  const [error, setError] = useState('');
  const [count, setCount] = useState<number | null>(null);

  const openNew = () => { setEditor({ name: '', description: '', op: 'AND', rules: [{ field: 'country', operator: 'eq', value: '' }] }); setCount(null); };
  const openEdit = (s: Segment) => {
    const rules = (s.definition.rules ?? []).filter((r): r is Condition => 'field' in r);
    setEditor({ id: s.id, name: s.name, description: s.description, op: s.definition.op ?? 'AND', rules: rules.length ? rules : [{ field: 'country', operator: 'eq', value: '' }] });
    setCount(s.cached_count ?? null);
  };

  const definition = (): RuleGroup => ({ op: editor!.op, rules: editor!.rules });

  const runPreview = async () => {
    if (!editor) return;
    setError('');
    try {
      const r = await preview.mutateAsync({ name: editor.name || 'preview', definition: definition() });
      setCount(r.count);
    } catch (err) { setError(apiErrorMessage(err)); }
  };

  const submit = async () => {
    if (!editor) return;
    setError('');
    try {
      await save.mutateAsync({ id: editor.id, body: { name: editor.name, description: editor.description, definition: definition(), is_dynamic: true } });
      setEditor(null);
    } catch (err) { setError(apiErrorMessage(err)); }
  };

  const setRule = (i: number, patch: Partial<Condition>) =>
    setEditor((e) => e && ({ ...e, rules: e.rules.map((r, idx) => idx === i ? { ...r, ...patch } : r) }));

  return (
    <Box>
      <PageHeader title="Segments" subtitle="Build dynamic audiences with the filter builder"
        action={canEdit && <Button variant="contained" startIcon={<AddIcon />} onClick={openNew}>New Segment</Button>} />

      {isLoading ? <Loading /> : (data?.length ?? 0) === 0 ? (
        <EmptyState title="No segments" hint="Create a segment to target specific contacts." />
      ) : (
        <Grid container spacing={2}>
          {data!.map((s) => (
            <Grid item xs={12} sm={6} md={4} key={s.id}>
              <Card sx={{ cursor: canEdit ? 'pointer' : 'default' }} onClick={() => canEdit && openEdit(s)}>
                <CardContent>
                  <Typography variant="h6">{s.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{s.description}</Typography>
                  <Chip size="small" sx={{ mt: 1 }} label={`${s.cached_count ?? '?'} contacts`} color="primary" />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={!!editor} onClose={() => setEditor(null)} maxWidth="md" fullWidth>
        <DialogTitle>{editor?.id ? 'Edit Segment' : 'New Segment'}</DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {editor && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField label="Name" value={editor.name} onChange={(e) => setEditor({ ...editor, name: e.target.value })} fullWidth />
              <TextField label="Description" value={editor.description} onChange={(e) => setEditor({ ...editor, description: e.target.value })} fullWidth />
              <Stack direction="row" alignItems="center" spacing={2}>
                <Typography variant="body2">Match</Typography>
                <ToggleButtonGroup size="small" exclusive value={editor.op}
                  onChange={(_, v) => v && setEditor({ ...editor, op: v })}>
                  <ToggleButton value="AND">ALL (AND)</ToggleButton>
                  <ToggleButton value="OR">ANY (OR)</ToggleButton>
                </ToggleButtonGroup>
              </Stack>

              {editor.rules.map((rule, i) => (
                <Stack key={i} direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="center">
                  <TextField select size="small" label="Field" value={rule.field} sx={{ minWidth: 160 }}
                    onChange={(e) => setRule(i, { field: e.target.value })}>
                    {FIELDS.map((f) => <MenuItem key={f} value={f}>{f}</MenuItem>)}
                  </TextField>
                  <TextField select size="small" label="Operator" value={rule.operator} sx={{ minWidth: 130 }}
                    onChange={(e) => setRule(i, { operator: e.target.value })}>
                    {OPERATORS.map((o) => <MenuItem key={o} value={o}>{o}</MenuItem>)}
                  </TextField>
                  <TextField size="small" label="Value" value={String(rule.value ?? '')} sx={{ flexGrow: 1 }}
                    disabled={['is_set', 'is_not_set'].includes(rule.operator)}
                    onChange={(e) => setRule(i, { value: e.target.value })} />
                  <IconButton color="error" onClick={() => setEditor({ ...editor, rules: editor.rules.filter((_, idx) => idx !== i) })}>
                    <DeleteIcon />
                  </IconButton>
                </Stack>
              ))}
              <Button startIcon={<AddIcon />} onClick={() => setEditor({ ...editor, rules: [...editor.rules, { field: 'country', operator: 'eq', value: '' }] })}>
                Add condition
              </Button>

              <Stack direction="row" spacing={2} alignItems="center">
                <Button variant="outlined" onClick={runPreview} disabled={preview.isPending}>Preview count</Button>
                {count !== null && <Chip color="primary" label={`${count} matching contacts`} />}
              </Stack>
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
