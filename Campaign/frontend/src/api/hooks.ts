// TanStack Query hooks wrapping the REST API.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type {
  AuditLog, Campaign, CampaignMetrics, Contact, OverviewMetrics, Page,
  ProviderConfig, Segment, Template, TimeseriesPoint, User,
} from '../types';

// ---- Campaigns ----
export function useCampaigns(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: ['campaigns', params],
    queryFn: async () => (await api.get<Page<Campaign>>('/campaigns', { params })).data,
  });
}
export function useCampaign(id?: number) {
  return useQuery({
    queryKey: ['campaign', id],
    enabled: !!id,
    queryFn: async () => (await api.get<Campaign>(`/campaigns/${id}`)).data,
  });
}
export function useCampaignAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, body }: { id: number; action: string; body?: unknown }) =>
      (await api.post<Campaign>(`/campaigns/${id}/${action}`, body ?? {})).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['campaign'] });
    },
  });
}
export function useSaveCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Partial<Campaign> }) =>
      id ? (await api.patch(`/campaigns/${id}`, body)).data
         : (await api.post('/campaigns', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  });
}
export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/campaigns/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  });
}

// ---- Templates ----
export function useTemplates(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: ['templates', params],
    queryFn: async () => (await api.get<Page<Template>>('/templates', { params })).data,
  });
}
export function useSaveTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Partial<Template> }) =>
      id ? (await api.patch(`/templates/${id}`, body)).data
         : (await api.post('/templates', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  });
}
export function useTemplateAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action }: { id: number; action: 'clone' | 'archive' }) =>
      (await api.post(`/templates/${id}/${action}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  });
}
export function useDeleteTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`/templates/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  });
}

// ---- Contacts ----
export function useContacts(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: ['contacts', params],
    queryFn: async () => (await api.get<Page<Contact>>('/contacts', { params })).data,
  });
}
export function useSaveContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Partial<Contact> }) =>
      id ? (await api.patch(`/contacts/${id}`, body)).data
         : (await api.post('/contacts', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contacts'] }),
  });
}
export function useImportContacts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append('file', file);
      return (await api.post('/contacts/import', fd)).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contacts'] }),
  });
}

// ---- Segments ----
export function useSegments() {
  return useQuery({ queryKey: ['segments'], queryFn: async () => (await api.get<Segment[]>('/segments')).data });
}
export function useSaveSegment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Partial<Segment> }) =>
      id ? (await api.patch(`/segments/${id}`, body)).data
         : (await api.post('/segments', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['segments'] }),
  });
}
export function usePreviewSegment() {
  return useMutation({
    mutationFn: async (body: Partial<Segment>) =>
      (await api.post<{ count: number; sample: Record<string, unknown>[] }>('/segments/preview', body)).data,
  });
}

// ---- Providers ----
export function useProviders() {
  return useQuery({ queryKey: ['providers'], queryFn: async () => (await api.get<ProviderConfig[]>('/providers')).data });
}
export function useProviderHealth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await api.post(`/providers/${id}/health`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['providers'] }),
  });
}

// ---- Analytics ----
export function useOverview() {
  return useQuery({ queryKey: ['overview'], queryFn: async () => (await api.get<OverviewMetrics>('/analytics/overview')).data });
}
export function useTimeseries(campaignId?: number) {
  return useQuery({
    queryKey: ['timeseries', campaignId],
    queryFn: async () =>
      (await api.get<TimeseriesPoint[]>('/analytics/timeseries', { params: { campaign_id: campaignId } })).data,
  });
}
export function useCampaignMetrics(id?: number) {
  return useQuery({
    queryKey: ['metrics', id],
    enabled: !!id,
    queryFn: async () => (await api.get<CampaignMetrics>(`/analytics/campaigns/${id}`)).data,
  });
}

// ---- Users ----
export function useUsers() {
  return useQuery({ queryKey: ['users'], queryFn: async () => (await api.get<User[]>('/users')).data });
}
export function useSaveUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body: Record<string, unknown> }) =>
      id ? (await api.patch(`/users/${id}`, body)).data : (await api.post('/users', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });
}

// ---- Audit ----
export function useAuditLogs(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: ['audit', params],
    queryFn: async () => (await api.get<Page<AuditLog>>('/audit-logs', { params })).data,
  });
}
