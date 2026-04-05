const processingItems = [
  {
    f: "BCBS_TX_ONCOLOGY_2024.pdf",
    s: "VECTORIZING",
    k: "OCR Complete",
    p: 78,
  },
  {
    f: "cms.gov/medicare-coverage-database/...",
    s: "ENTITY_MAPPING",
    k: "Mapping Clinical Codes",
    p: 42,
  },
];

export default function IngestPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto">
      <header className="mb-10">
        <h2 className="font-headline text-3xl font-extrabold text-on-surface tracking-tight">
          Ingest Policies
        </h2>
        <p className="text-slate-500 mt-2 text-lg">
          Add new payer policies to the Clinical Knowledge Graph for real-time
          analysis.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {/* Upload area */}
        <div className="md:col-span-2 bg-white rounded-xl p-8 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-teal-50 flex items-center justify-center rounded-lg">
                <span className="material-symbols-outlined text-[#0EA5A0]">
                  upload_file
                </span>
              </div>
              <h3 className="font-semibold text-lg">Direct Document Upload</h3>
            </div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest bg-slate-50 px-2 py-1 rounded">
              PDF / DOCX
            </span>
          </div>
          <div className="border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50 p-12 flex flex-col items-center justify-center group cursor-pointer hover:bg-white hover:border-[#0EA5A0] transition-all">
            <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-sm mb-4 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-[#0EA5A0] text-3xl">
                add
              </span>
            </div>
            <p className="text-on-surface font-medium text-center">
              Drag and drop policy files here
            </p>
            <p className="text-slate-400 text-sm mt-1">
              or{" "}
              <span className="text-[#0EA5A0] font-semibold underline decoration-2 underline-offset-4">
                browse files
              </span>
            </p>
          </div>
        </div>

        {/* URL import */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl p-6 border border-slate-100 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-teal-50 flex items-center justify-center rounded-lg">
                <span className="material-symbols-outlined text-[#0EA5A0] text-xl">
                  link
                </span>
              </div>
              <h3 className="font-semibold">Import from URL</h3>
            </div>
            <p className="text-slate-500 text-sm mb-4">
              Crawl specific payer portal URLs to automatically extract text.
            </p>
            <div className="relative">
              <input
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-[#0EA5A0] outline-none transition-all pr-12"
                placeholder="https://payer-portal.com/policy-pdf"
                type="text"
              />
              <button className="absolute right-2 top-2 p-1.5 bg-[#0EA5A0] rounded-md text-white">
                <span className="material-symbols-outlined text-sm">
                  arrow_forward
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Processing table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="text-[11px] uppercase tracking-widest text-slate-400 font-bold bg-slate-50">
              <th className="px-6 py-4">Source File</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Knowledge Extraction</th>
              <th className="px-6 py-4 text-right">Progress</th>
            </tr>
          </thead>
          <tbody className="text-sm divide-y divide-slate-50">
            {processingItems.map((item, i) => (
              <tr key={i} className="hover:bg-slate-50/30 transition-colors">
                <td className="px-6 py-5">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-slate-400">
                      picture_as_pdf
                    </span>
                    <span className="font-mono text-xs">{item.f}</span>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <span className="px-3 py-1 bg-teal-50 text-[#0EA5A0] text-xs font-bold rounded-full">
                    {item.s}
                  </span>
                </td>
                <td className="px-6 py-5 text-slate-500">{item.k}</td>
                <td className="px-6 py-5 text-right">
                  <div className="flex flex-col items-end gap-1.5">
                    <span className="font-mono text-xs font-semibold text-[#0EA5A0]">
                      {item.p}%
                    </span>
                    <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#0EA5A0]"
                        style={{ width: `${item.p}%` }}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
