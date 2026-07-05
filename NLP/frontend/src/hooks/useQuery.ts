import { useState, useCallback } from 'react';
import { nlpQuery, executeSQL } from '../services/api';
import type { QueryResult, QueryHistoryItem } from '../types';
import { format } from 'date-fns';

const HISTORY_KEY = 'nlp_query_history';
const MAX_HISTORY = 10;

// ─── useQuery ─────────────────────────────────────────────────────────────────

interface UseQueryReturn {
  result: QueryResult | null;
  loading: boolean;
  error: string | null;
  runNLPQuery: (datasetId: string, query: string, datasetName?: string) => Promise<QueryResult | null>;
  runSQLQuery: (datasetId: string, sql: string, datasetName?: string) => Promise<QueryResult | null>;
  clearResult: () => void;
  history: QueryHistoryItem[];
  clearHistory: () => void;
}

export const useQuery = (): UseQueryReturn => {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>(() => loadHistory());

  const addToHistory = useCallback((item: QueryHistoryItem) => {
    setHistory((prev) => {
      const filtered = prev.filter((h) => h.query !== item.query || h.dataset_id !== item.dataset_id);
      const updated = [item, ...filtered].slice(0, MAX_HISTORY);
      saveHistory(updated);
      return updated;
    });
  }, []);

  const runNLPQuery = useCallback(
    async (datasetId: string, query: string, datasetName = 'Unknown Dataset'): Promise<QueryResult | null> => {
      setLoading(true);
      setError(null);
      try {
        const queryResult = await nlpQuery(datasetId, query);
        setResult(queryResult);
        addToHistory({
          id: queryResult.query_id,
          query,
          dataset_id: datasetId,
          dataset_name: datasetName,
          timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
          result_count: queryResult.row_count,
        });
        return queryResult;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Query execution failed';
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [addToHistory]
  );

  const runSQLQuery = useCallback(
    async (datasetId: string, sql: string, datasetName = 'Unknown Dataset'): Promise<QueryResult | null> => {
      setLoading(true);
      setError(null);
      try {
        const queryResult = await executeSQL(datasetId, sql);
        setResult(queryResult);
        addToHistory({
          id: queryResult.query_id,
          query: sql,
          dataset_id: datasetId,
          dataset_name: datasetName,
          timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
          result_count: queryResult.row_count,
        });
        return queryResult;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'SQL execution failed';
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [addToHistory]
  );

  const clearResult = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    saveHistory([]);
  }, []);

  return { result, loading, error, runNLPQuery, runSQLQuery, clearResult, history, clearHistory };
};

// ─── History Storage Helpers ──────────────────────────────────────────────────

function loadHistory(): QueryHistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as QueryHistoryItem[];
  } catch {
    return [];
  }
}

function saveHistory(items: QueryHistoryItem[]): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
  } catch {
    // ignore
  }
}
