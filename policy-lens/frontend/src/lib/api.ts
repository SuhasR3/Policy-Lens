import type {
  DrugSearchResult,
  TrendingDrug,
  PayerComparison,
  CompareSummary,
} from "./types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const api = {
  drugs: {
    search: (q: string) => get<DrugSearchResult[]>(`/drugs/search?q=${encodeURIComponent(q)}`),
    trending: () => get<TrendingDrug[]>("/drugs/trending"),
    detail: (id: number) => get<DrugSearchResult>(`/drugs/${id}`),
  },
  compare: {
    byDrug: (drug: string) => get<PayerComparison[]>(`/compare?drug=${encodeURIComponent(drug)}`),
    summary: (drug: string) => get<CompareSummary>(`/compare/summary?drug=${encodeURIComponent(drug)}`),
    payers: () => get<string[]>("/payers"),
  },
};
