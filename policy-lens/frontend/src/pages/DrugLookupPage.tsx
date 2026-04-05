import { useState, type FormEvent } from "react";
import { useDrugSearch, useTrendingDrugs } from "../hooks/useDrugSearch";
import type { DrugSearchResult } from "../lib/types";

function statusLabel(result: DrugSearchResult) {
  const group = result.access_status_group;
  const pa = result.prior_auth_required;
  if (group === "not_covered") return { text: "Not Covered", variant: "error" as const };
  if (group === "non_preferred") return { text: "Non-Preferred", variant: "warning" as const };
  if (pa === 1) return { text: "Covered (PA)", variant: "warning" as const };
  if (group === "preferred") return { text: "Preferred", variant: "success" as const };
  if (group === "covered" || group === "non_specialty") return { text: "Covered", variant: "success" as const };
  return { text: group ?? "Covered", variant: "success" as const };
}

const badgeClasses = {
  success: "bg-[#0EA5A0]/10 text-[#0EA5A0]",
  warning: "bg-tertiary-container/20 text-tertiary-container",
  error: "bg-error-container/30 text-error",
};

function DrugCard({ result }: { result: DrugSearchResult }) {
  const status = statusLabel(result);
  return (
    <div className="bg-white rounded-xl whisper-shadow overflow-hidden flex flex-col group hover:translate-y-[-2px] transition-transform duration-200 border border-slate-100">
      <div className="p-6 flex-1">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="font-bold text-lg leading-tight">{result.payer}</h3>
            <p className="text-xs text-slate-400 font-mono mt-1">
              {result.hcpcs_code ?? result.drug_name}
            </p>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${badgeClasses[status.variant]}`}
          >
            {status.text}
          </span>
        </div>
        <div className="space-y-4 pt-2">
          <div className="flex justify-between items-end border-b border-slate-50 pb-2">
            <span className="text-xs font-medium text-slate-500">Access Status</span>
            <span className="mono-text font-semibold text-on-surface capitalize">
              {result.access_status_group?.replace(/_/g, " ") ?? "—"}
            </span>
          </div>
          <div className="flex justify-between items-end border-b border-slate-50 pb-2">
            <span className="text-xs font-medium text-slate-500">Drug Category</span>
            <span className="mono-text font-semibold text-on-surface text-right max-w-[60%] truncate">
              {result.drug_category ?? "—"}
            </span>
          </div>
          <div className="flex justify-between items-end border-b border-slate-50 pb-2">
            <span className="text-xs font-medium text-slate-500">PA Requirement</span>
            {result.prior_auth_required === 1 ? (
              <span
                className="material-symbols-outlined text-tertiary-container"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                assignment_late
              </span>
            ) : (
              <span className="material-symbols-outlined text-slate-300">block</span>
            )}
          </div>
          <div className="flex justify-between items-end">
            <span className="text-xs font-medium text-slate-500">Step Therapy</span>
            {result.step_therapy_required === 1 ? (
              <span className="material-symbols-outlined text-[#0EA5A0] text-[20px]">
                check_circle
              </span>
            ) : (
              <span className="material-symbols-outlined text-slate-300">block</span>
            )}
          </div>
        </div>
      </div>
      <div className="px-6 py-4 bg-slate-50 flex justify-between items-center">
        <span className="text-[10px] uppercase font-bold text-slate-400">
          {result.effective_date ? `Effective: ${result.effective_date}` : "—"}
        </span>
        <button className="text-[#0EA5A0] text-xs font-bold hover:underline">View Policy</button>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl whisper-shadow overflow-hidden flex flex-col border border-slate-100 animate-pulse">
      <div className="p-6 flex-1 space-y-4">
        <div className="flex justify-between">
          <div className="space-y-2">
            <div className="h-5 w-36 bg-slate-200 rounded" />
            <div className="h-3 w-24 bg-slate-100 rounded" />
          </div>
          <div className="h-6 w-20 bg-slate-100 rounded-full" />
        </div>
        <div className="space-y-3 pt-4">
          <div className="h-4 w-full bg-slate-100 rounded" />
          <div className="h-4 w-full bg-slate-100 rounded" />
          <div className="h-4 w-3/4 bg-slate-100 rounded" />
        </div>
      </div>
      <div className="px-6 py-4 bg-slate-50">
        <div className="h-3 w-32 bg-slate-200 rounded" />
      </div>
    </div>
  );
}

export default function DrugLookupPage() {
  const [query, setQuery] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const { data: results, isLoading, isError } = useDrugSearch(searchTerm);
  const { data: trending } = useTrendingDrugs();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) setSearchTerm(query.trim());
  }

  function handleTrendingClick(drug: string) {
    setQuery(drug);
    setSearchTerm(drug);
  }

  const trendingList = trending?.slice(0, 6) ?? [];

  return (
    <div className="p-10 max-w-7xl mx-auto">
      <section className="mb-12">
        <h2 className="text-4xl font-extrabold font-headline text-on-surface tracking-tight mb-4">
          Drug Lookup
        </h2>
        <p className="text-on-surface-variant text-lg max-w-2xl mb-8 text-slate-500">
          Analyze real-time coverage, tiering, and prior authorization requirements across national
          payers.
        </p>

        <form onSubmit={handleSubmit} className="relative max-w-3xl">
          <div className="bg-white rounded-xl whisper-shadow p-2 flex items-center border border-slate-100">
            <span className="material-symbols-outlined text-[#0EA5A0] mx-4 text-3xl">pill</span>
            <input
              className="flex-1 border-none focus:ring-0 text-xl font-medium placeholder-slate-400 py-4"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter drug name, NDC, or HCPCS code..."
              type="text"
            />
            <button
              type="submit"
              className="bg-[#0EA5A0] text-white px-8 py-4 rounded-lg font-bold hover:brightness-110 transition-all active:scale-95"
            >
              Search
            </button>
          </div>
          <div className="absolute -bottom-16 left-0 flex space-x-2 flex-wrap">
            <span className="text-xs font-bold text-on-surface-variant uppercase tracking-widest pt-2 px-4 text-slate-400">
              Trending:
            </span>
            {trendingList.map((drug) => (
              <button
                key={drug.drug_name}
                type="button"
                onClick={() => handleTrendingClick(drug.drug_name)}
                className="px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded text-xs font-medium text-slate-600 transition-colors"
              >
                {drug.drug_name}
              </button>
            ))}
          </div>
        </form>
      </section>

      {/* Results */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {isError && (
        <div className="text-center py-20">
          <span className="material-symbols-outlined text-error text-4xl mb-4">error</span>
          <p className="text-slate-500">Failed to fetch results. Is the backend running?</p>
        </div>
      )}

      {results && results.length === 0 && (
        <div className="text-center py-20">
          <span className="material-symbols-outlined text-slate-300 text-5xl mb-4">search_off</span>
          <p className="text-slate-500 text-lg">No results found for "{searchTerm}"</p>
          <p className="text-slate-400 text-sm mt-1">Try a different drug name or HCPCS code</p>
        </div>
      )}

      {results && results.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {results.map((result) => (
            <DrugCard key={result.id} result={result} />
          ))}

          {/* AI Summary Card — static placeholder */}
          <div className="bg-[#003331] rounded-xl whisper-shadow p-6 text-white flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 mb-6">
                <span className="material-symbols-outlined text-[#0EA5A0]">auto_awesome</span>
                <span className="text-xs font-bold uppercase tracking-widest text-[#0EA5A0]">
                  Policy Summary
                </span>
              </div>
              <p className="text-lg leading-relaxed mb-4">
                Found{" "}
                <span className="font-bold text-[#5ED9D3]">{results.length} results</span> for{" "}
                <span className="font-bold text-[#5ED9D3]">{searchTerm}</span> across{" "}
                <span className="font-bold">
                  {new Set(results.map((r) => r.payer)).size} payers
                </span>
                .
              </p>
              <div className="bg-white/10 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium opacity-80">PA Required</span>
                  <span className="text-xs font-mono">
                    {results.filter((r) => r.prior_auth_required === 1).length}/{results.length}
                  </span>
                </div>
                <div className="w-full bg-white/20 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[#0EA5A0] h-full transition-all"
                    style={{
                      width: `${(results.filter((r) => r.prior_auth_required === 1).length / results.length) * 100}%`,
                    }}
                  />
                </div>
              </div>
            </div>
            <button className="w-full py-3 bg-[#0EA5A0] rounded-lg text-sm font-bold hover:brightness-110 transition-all">
              Generate Market Insight Report
            </button>
          </div>
        </div>
      )}

      {/* Initial state — no search yet */}
      {!searchTerm && !isLoading && (
        <div className="text-center py-20">
          <span className="material-symbols-outlined text-slate-200 text-6xl mb-4">search</span>
          <p className="text-slate-400 text-lg">Search for a drug to see coverage across payers</p>
          <p className="text-slate-300 text-sm mt-1">
            Try clicking a trending drug above or type a name
          </p>
        </div>
      )}
    </div>
  );
}
