const trendingDrugs = ["Humira", "Keytruda", "Entyvio"];

export default function DrugLookupPage() {
  return (
    <div className="p-10 max-w-7xl mx-auto">
      <section className="mb-12">
        <h2 className="text-4xl font-extrabold font-headline text-on-surface tracking-tight mb-4">
          Drug Lookup
        </h2>
        <p className="text-on-surface-variant text-lg max-w-2xl mb-8 text-slate-500">
          Analyze real-time coverage, tiering, and prior authorization
          requirements across national payers.
        </p>

        <div className="relative max-w-3xl">
          <div className="bg-white rounded-xl whisper-shadow p-2 flex items-center border border-slate-100">
            <span className="material-symbols-outlined text-[#0EA5A0] mx-4 text-3xl">
              pill
            </span>
            <input
              className="flex-1 border-none focus:ring-0 text-xl font-medium placeholder-slate-400 py-4"
              defaultValue="Ozempic (Semaglutide)"
              placeholder="Enter drug name, NDC, or HCPCS code..."
              type="text"
            />
            <button className="bg-[#0EA5A0] text-white px-8 py-4 rounded-lg font-bold hover:brightness-110 transition-all active:scale-95">
              Search
            </button>
          </div>
          <div className="absolute -bottom-16 left-0 flex space-x-2">
            <span className="text-xs font-bold text-on-surface-variant uppercase tracking-widest pt-2 px-4 text-slate-400">
              Trending:
            </span>
            {trendingDrugs.map((drug) => (
              <button
                key={drug}
                className="px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded text-xs font-medium text-slate-600 transition-colors"
              >
                {drug}
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Aetna Card */}
        <div className="bg-white rounded-xl whisper-shadow overflow-hidden flex flex-col group hover:translate-y-[-2px] transition-transform duration-200 border border-slate-100">
          <div className="p-6 flex-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-bold text-lg leading-tight">
                  Aetna Health
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-1">
                  PLAN_ID: AET-992-COM
                </p>
              </div>
              <span className="px-3 py-1 bg-[#0EA5A0]/10 text-[#0EA5A0] rounded-full text-[11px] font-bold uppercase tracking-wider">
                Covered
              </span>
            </div>
            <div className="space-y-4 pt-2">
              <div className="flex justify-between items-end border-b border-slate-50 pb-2">
                <span className="text-xs font-medium text-slate-500">
                  Tier Assignment
                </span>
                <span className="mono-text font-semibold text-lg text-on-surface">
                  Tier 2
                </span>
              </div>
              <div className="flex justify-between items-end border-b border-slate-50 pb-2">
                <span className="text-xs font-medium text-slate-500">
                  Copay Range
                </span>
                <span className="mono-text font-semibold text-on-surface">
                  $25.00
                </span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-xs font-medium text-slate-500">
                  PA Requirement
                </span>
                <span className="material-symbols-outlined text-slate-300">
                  block
                </span>
              </div>
            </div>
          </div>
          <div className="px-6 py-4 bg-slate-50 flex justify-between items-center">
            <span className="text-[10px] uppercase font-bold text-slate-400">
              Last Updated: 2h ago
            </span>
            <button className="text-[#0EA5A0] text-xs font-bold hover:underline">
              View Policy
            </button>
          </div>
        </div>

        {/* UHC Card */}
        <div className="bg-white rounded-xl whisper-shadow overflow-hidden flex flex-col group hover:translate-y-[-2px] transition-transform duration-200 border border-slate-100">
          <div className="p-6 flex-1">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-bold text-lg leading-tight">
                  UnitedHealthcare
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-1">
                  PLAN_ID: UHC-TX-440
                </p>
              </div>
              <span className="px-3 py-1 bg-tertiary-container/20 text-tertiary-container text-[11px] font-bold uppercase tracking-wider">
                Covered (PA)
              </span>
            </div>
            <div className="space-y-4 pt-2">
              <div className="flex justify-between items-end border-b border-slate-50 pb-2">
                <span className="text-xs font-medium text-slate-500">
                  Tier Assignment
                </span>
                <span className="mono-text font-semibold text-lg text-on-surface">
                  Tier 3
                </span>
              </div>
              <div className="flex justify-between items-end border-b border-slate-50 pb-2">
                <span className="text-xs font-medium text-slate-500">
                  Copay Range
                </span>
                <span className="mono-text font-semibold text-on-surface">
                  $45.00 - $70.00
                </span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-xs font-medium text-slate-500">
                  PA Requirement
                </span>
                <span
                  className="material-symbols-outlined text-tertiary-container"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  assignment_late
                </span>
              </div>
            </div>
          </div>
          <div className="px-6 py-4 bg-slate-50 flex justify-between items-center">
            <span className="text-[10px] uppercase font-bold text-slate-400">
              Last Updated: Oct 12
            </span>
            <button className="text-[#0EA5A0] text-xs font-bold hover:underline">
              View Criteria
            </button>
          </div>
        </div>

        {/* AI Analytics Card */}
        <div className="bg-[#003331] rounded-xl whisper-shadow p-6 text-white flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-6">
              <span className="material-symbols-outlined text-[#0EA5A0]">
                auto_awesome
              </span>
              <span className="text-xs font-bold uppercase tracking-widest text-[#0EA5A0]">
                Policy Summary
              </span>
            </div>
            <p className="text-lg leading-relaxed mb-4">
              Coverage for{" "}
              <span className="font-bold text-[#5ED9D3]">Semaglutide</span> has
              shifted by <span className="font-bold">14%</span> across North
              American plans in Q4.
            </p>
            <div className="bg-white/10 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium opacity-80">
                  Market Penetration
                </span>
                <span className="text-xs font-mono">68%</span>
              </div>
              <div className="w-full bg-white/20 h-1.5 rounded-full overflow-hidden">
                <div className="bg-[#0EA5A0] h-full w-[68%]" />
              </div>
            </div>
          </div>
          <button className="w-full py-3 bg-[#0EA5A0] rounded-lg text-sm font-bold hover:brightness-110 transition-all">
            Generate Market Insight Report
          </button>
        </div>
      </div>
    </div>
  );
}
