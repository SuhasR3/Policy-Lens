const summaryStats = [
  { l: "Total Documents", v: "1,428" },
  { l: "Indexed Networks", v: "84" },
  { l: "AI Policy Coverage", v: "92%" },
  { l: "Latest Indexed", v: "May 14" },
];

const policies = [
  {
    name: "Oncology Biosimilar Preferred Products",
    id: "POL-ONC-88219",
    payer: "UnitedHealthcare",
    drugClass: "Oncology",
    date: "2024-05-12",
    status: "Active" as const,
  },
  {
    name: "Advanced Psoriasis Therapies",
    id: "POL-DERM-44321",
    payer: "Aetna CVS Health",
    drugClass: "Dermatology",
    date: "2024-05-10",
    status: "Active" as const,
  },
  {
    name: "Multiple Sclerosis Clinical Guideline",
    id: "POL-NEURO-11202",
    payer: "Cigna",
    drugClass: "Neurology",
    date: "2024-05-08",
    status: "Review" as const,
  },
  {
    name: "Growth Hormone Replacement Therapy",
    id: "POL-ENDO-99812",
    payer: "BCBS",
    drugClass: "Endocrinology",
    date: "2024-04-29",
    status: "Active" as const,
  },
];

export default function LibraryPage() {
  return (
    <div className="px-8 pb-12">
      <div className="flex justify-between items-end py-8">
        <div>
          <h2 className="text-3xl font-extrabold font-headline tracking-tight text-slate-900">
            Policy Library
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Access and manage over 1,420 clinical policy documents across all payers.
          </p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-white text-slate-700 text-sm font-semibold rounded-lg shadow-sm border border-slate-200">
            <span className="material-symbols-outlined text-[18px]">filter_list</span> Advanced
            Filters
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-[#0EA5A0] text-white text-sm font-semibold rounded-lg shadow-sm">
            <span className="material-symbols-outlined text-[18px]">add</span> New Policy
          </button>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        {summaryStats.map((s, i) => (
          <div
            key={i}
            className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col justify-between h-32"
          >
            <p className="text-slate-500 text-xs font-bold uppercase tracking-wider">{s.l}</p>
            <span className="text-4xl font-semibold text-slate-900 tracking-tight leading-none">
              {s.v}
            </span>
          </div>
        ))}
      </div>

      {/* Policy table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50">
            <tr className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">
              <th className="px-6 py-4">Policy Name</th>
              <th className="px-6 py-4">Payer</th>
              <th className="px-6 py-4">Drug Class</th>
              <th className="px-6 py-4">Last Indexed</th>
              <th className="px-6 py-4 text-center">Status</th>
              <th className="px-6 py-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {policies.map((p, i) => (
              <tr key={i} className="hover:bg-slate-50 transition-colors">
                <td className="px-6 py-5">
                  <div className="flex flex-col">
                    <span className="text-sm font-bold text-slate-900">{p.name}</span>
                    <span className="text-[10px] font-mono text-slate-400">{p.id}</span>
                  </div>
                </td>
                <td className="px-6 py-5 text-sm text-slate-700">{p.payer}</td>
                <td className="px-6 py-5">
                  <span className="px-2 py-1 bg-slate-100 text-slate-600 text-[10px] font-bold rounded uppercase">
                    {p.drugClass}
                  </span>
                </td>
                <td className="px-6 py-5 font-mono text-[11px] text-slate-500">{p.date}</td>
                <td className="px-6 py-5">
                  <div className="flex justify-center">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        p.status === "Active"
                          ? "bg-teal-50 text-[#0EA5A0]"
                          : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {p.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-5 text-right">
                  <button className="text-slate-400 hover:text-[#0EA5A0]">
                    <span className="material-symbols-outlined">more_vert</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
