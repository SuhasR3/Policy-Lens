const stats = [
  { l: "Critical Updates", v: "12", d: "+3 today", c: "error" as const },
  { l: "Clinical Minor", v: "48", d: "Stable", c: "tertiary" as const },
  { l: "Pending Review", v: "07", d: "Active", c: "primary" as const },
  { l: "Auto-Processed", v: "214", d: "24h", c: "slate" as const },
];

export default function PolicyChangesPage() {
  return (
    <div className="p-8 max-w-7xl w-full mx-auto">
      <div className="flex items-end justify-between mb-8">
        <div>
          <h2 className="text-3xl font-extrabold font-headline tracking-tight text-on-surface">
            Policy Changes
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Real-time clinical and administrative modification timeline.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="bg-white text-slate-600 px-4 py-2 rounded-lg text-sm font-medium whisper-shadow ghost-border hover:bg-slate-50 transition-all flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">filter_list</span> Filter
            Feed
          </button>
          <button className="bg-[#0EA5A0] text-white px-4 py-2 rounded-lg text-sm font-medium whisper-shadow hover:scale-95 duration-150 transition-all flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">file_download</span> Export
            Report
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-6 mb-10">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-xl whisper-shadow border border-slate-100">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
              {stat.l}
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-semibold font-headline">{stat.v}</span>
              <span
                className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  stat.c === "error"
                    ? "bg-red-50 text-error"
                    : stat.c === "primary"
                    ? "bg-teal-50 text-[#0EA5A0]"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {stat.d}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Timeline */}
      <div className="space-y-8 relative before:absolute before:left-[19px] before:top-2 before:bottom-0 before:w-px before:bg-slate-200">
        <div className="relative pl-12">
          <div className="absolute left-0 top-1 w-10 h-10 bg-[#F7F8FA] flex items-center justify-center rounded-full border-2 border-white z-10">
            <div className="w-3 h-3 bg-[#0EA5A0] rounded-full" />
          </div>
          <div className="mb-4">
            <span className="text-sm font-bold text-slate-400 uppercase tracking-widest">
              Today, Oct 24
            </span>
          </div>

          <div className="bg-white rounded-xl whisper-shadow border border-slate-100 overflow-hidden mb-6">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-4">
                  <span className="bg-red-50 text-error text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider">
                    Clinical Major
                  </span>
                  <h3 className="text-lg font-bold text-on-surface">
                    Humira (Adalimumab) Prior Authorization Update
                  </h3>
                </div>
                <span className="mono-text text-xs text-slate-500 bg-slate-50 px-2 py-1 rounded">
                  RX-992-B-2024
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-red-50/50 border border-red-100/30">
                  <p className="text-[10px] font-bold text-error uppercase tracking-widest mb-2">
                    Previous Version
                  </p>
                  <p className="text-sm text-slate-700 leading-relaxed italic">
                    "Coverage requires failure of at least one preferred alternative therapy
                    (Enbrel)..."
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-emerald-50/50 border border-emerald-100/30">
                  <p className="text-[10px] font-bold text-[#0EA5A0] uppercase tracking-widest mb-2">
                    Updated Version
                  </p>
                  <p className="text-sm text-slate-800 leading-relaxed font-medium">
                    "Coverage requires failure of{" "}
                    <span className="bg-emerald-100 text-teal-900 px-1 rounded font-bold italic">
                      two (2)
                    </span>{" "}
                    preferred alternative therapies..."
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
