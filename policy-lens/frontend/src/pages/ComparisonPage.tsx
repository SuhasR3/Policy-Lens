const payers = ["United Healthcare", "Aetna", "Cigna", "Anthem BCBS"];

const metrics = [
  { l: "Avg Covered Lives", v: "12.4M", d: "+4.2%" },
  { l: "Total Policy Alerts", v: "08", d: "3 New", e: true },
  { l: "Clinical Variance", v: "24%", d: "Stable" },
  { l: "Market Access Score", v: "82", d: "/ 100", p: true },
];

interface ComparisonFactor {
  label: string;
  values: string[];
  type: "badge" | "status" | "mono" | "icon-text" | "text" | "mono-bold";
}

const factors: ComparisonFactor[] = [
  {
    label: "Coverage Status",
    values: ["COVERED_TIER_2", "COVERED_TIER_3", "NOT_PREFERRED", "COVERED_TIER_2"],
    type: "badge",
  },
  {
    label: "Prior Auth",
    values: ["REQUIRED", "REQUIRED", "Enhanced Review", "NOT REQUIRED"],
    type: "status",
  },
  {
    label: "Step Therapy",
    values: [
      "Requires 1 alternative fail",
      "None defined",
      "Requires 3 alternative fails",
      "Requires 1 alternative fail",
    ],
    type: "mono",
  },
  {
    label: "Site of Care",
    values: [
      "Home / Physician Office",
      "Outpatient Hospital Only",
      "Home Only",
      "Any Facility",
    ],
    type: "icon-text",
  },
  {
    label: "Indications",
    values: [
      "RA, PsA, AS, CD, UC, Ps, HS, UV",
      "RA, PsA, AS, CD, UC",
      "RA, PsA ONLY",
      "All FDA Approved",
    ],
    type: "text",
  },
  {
    label: "Quantity Limit",
    values: ["2 pens / 28 days", "4 pens / 28 days", "1 pen / 30 days", "No Limit"],
    type: "mono-bold",
  },
];

function CellValue({ type, value }: { type: ComparisonFactor["type"]; value: string }) {
  switch (type) {
    case "badge":
      return (
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-bold font-mono ${
            value.includes("NOT")
              ? "bg-error-container/20 text-error"
              : "bg-[#0EA5A0]/10 text-[#0EA5A0]"
          }`}
        >
          {value}
        </span>
      );
    case "status": {
      const color =
        value === "REQUIRED"
          ? "text-[#0EA5A0]"
          : value === "NOT REQUIRED"
          ? "text-slate-400"
          : "text-error";
      const icon =
        value === "REQUIRED"
          ? "check_circle"
          : value === "NOT REQUIRED"
          ? "info"
          : "warning";
      return (
        <div className={`flex items-center gap-2 ${color}`}>
          <span className="material-symbols-outlined text-[20px]">{icon}</span>
          <span className="text-xs font-bold">{value}</span>
        </div>
      );
    }
    case "mono":
      return <span className="text-xs font-mono text-slate-600">{value}</span>;
    case "icon-text":
      return (
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-slate-400 text-[18px]">home</span>
          <span className="text-xs font-medium">{value}</span>
        </div>
      );
    case "text":
      return <span className="text-xs text-slate-600 leading-relaxed">{value}</span>;
    case "mono-bold":
      return <span className="text-sm font-mono text-slate-900 font-bold">{value}</span>;
  }
}

export default function ComparisonPage() {
  return (
    <div className="p-8 flex flex-col gap-8 max-w-7xl mx-auto w-full">
      <div className="flex flex-col gap-6">
        <div className="flex justify-between items-end">
          <div>
            <nav className="flex items-center gap-2 text-slate-400 text-xs mb-2 font-medium">
              <span>Clinical Analytics</span>
              <span className="material-symbols-outlined text-[14px]">chevron_right</span>
              <span>Payer Comparison</span>
            </nav>
            <h2 className="text-4xl font-extrabold font-headline tracking-tight text-slate-900">
              Humira <span className="text-slate-400 font-medium">(Adalimumab)</span>
            </h2>
          </div>
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-white text-slate-600 border border-slate-200 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-all flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">download</span> Export
              Analysis
            </button>
            <button className="px-6 py-2 bg-[#0EA5A0] text-white rounded-lg text-sm font-semibold hover:opacity-90 active:scale-95 transition-all shadow-sm">
              Generate AI Summary
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {metrics.map((m, i) => (
            <div
              key={i}
              className="bg-white p-6 rounded-lg shadow-sm border border-slate-100 flex flex-col justify-between"
            >
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                {m.l}
              </span>
              <div className="flex items-baseline gap-2 mt-2">
                <span
                  className={`text-4xl font-semibold tracking-tighter ${
                    m.p ? "text-[#0EA5A0]" : "text-slate-900"
                  }`}
                >
                  {m.v}
                </span>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold ${
                    m.e
                      ? "bg-error-container/20 text-error"
                      : "bg-primary-container/10 text-[#0EA5A0]"
                  }`}
                >
                  {m.d}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col overflow-hidden rounded-xl bg-white border border-slate-100 shadow-sm">
        {/* Header */}
        <div className="grid grid-cols-5 bg-slate-900 text-white">
          <div className="p-6 flex items-center font-bold text-sm border-r border-white/5">
            COMPARISON FACTORS
          </div>
          {payers.map((payer, idx) => (
            <div key={idx} className="p-6 flex flex-col gap-1 border-r border-white/5 last:border-0">
              <span className="text-[10px] text-[#0EA5A0] font-black tracking-widest uppercase">
                Payer 0{idx + 1}
              </span>
              <h4 className="font-bold text-lg leading-tight">{payer}</h4>
              <p className="text-xs text-slate-400">Commercial / Regional</p>
            </div>
          ))}
        </div>

        {/* Rows */}
        {factors.map((f, i) => (
          <div
            key={i}
            className={`grid grid-cols-5 group hover:bg-[#F7F8FA] transition-colors ${
              i % 2 === 0 ? "bg-white" : "bg-slate-50/50"
            }`}
          >
            <div className="p-6 flex items-center font-semibold text-sm text-slate-500">
              {f.label}
            </div>
            {f.values.map((v, idx) => (
              <div key={idx} className="p-6 border-l border-slate-100">
                <CellValue type={f.type} value={v} />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
