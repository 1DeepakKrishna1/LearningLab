import { useState, useEffect, useCallback } from 'react';
import { getDatasets, getDataset, deleteDataset as apiDeleteDataset } from '../services/api';
import type { DatasetListItem, Dataset } from '../types';

// ─── useDatasets (list) ───────────────────────────────────────────────────────

interface UseDatasetsReturn {
  datasets: DatasetListItem[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  deleteDataset: (id: string) => Promise<void>;
}

export const useDatasets = (): UseDatasetsReturn => {
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDatasets();
      setDatasets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const deleteDataset = useCallback(
    async (id: string) => {
      await apiDeleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
    },
    []
  );

  return { datasets, loading, error, refresh: fetchDatasets, deleteDataset };
};

// ─── useDataset (single) ──────────────────────────────────────────────────────

interface UseDatasetReturn {
  dataset: Dataset | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const useDataset = (id: string | null): UseDatasetReturn => {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDataset = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getDataset(id);
      setDataset(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dataset');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDataset();
  }, [fetchDataset]);

  return { dataset, loading, error, refresh: fetchDataset };
};

// ─── useLastDataset (localStorage persistence) ────────────────────────────────

export const useLastDataset = () => {
  const getLastDatasetId = (): string | null => {
    try {
      return localStorage.getItem('nlp_last_dataset_id');
    } catch {
      return null;
    }
  };

  const setLastDatasetId = (id: string) => {
    try {
      localStorage.setItem('nlp_last_dataset_id', id);
    } catch {
      // ignore localStorage errors
    }
  };

  return { getLastDatasetId, setLastDatasetId };
};
