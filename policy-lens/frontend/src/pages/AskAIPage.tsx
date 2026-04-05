const suggestedPrompts = [
  "Compare Humira biosimilars",
  "Summarize recent oncology edits",
  "Check PA criteria for Ozempic",
];

const citations = [
  {
    icon: "description",
    badge: "Primary Source",
    code: "BCBSMA-PMP-2024",
    title: "Adalimumab (Humira) and Biosimilars Policy",
    meta: "PDF • Jan 15",
  },
  {
    icon: "history_edu",
    badge: "Summary of Changes",
    code: "BCBSMA-SOC-Q1",
    title: "Pharmacy Benefit Quarterly Update - Q1 2024",
    meta: "PDF • Dec 01",
  },
];

export default function AskAIPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Chat messages */}
      <section className="flex-1 overflow-y-auto px-8 py-10 custom-scrollbar max-w-4xl mx-auto w-full space-y-12">
        {/* User message */}
        <div className="flex flex-col items-end max-w-[85%] ml-auto">
          <div className="bg-white rounded-2xl rounded-tr-none px-6 py-4 border border-slate-100 whisper-shadow">
            <p className="text-on-surface text-base leading-relaxed">
              What are the step therapy requirements for Humira vs. biosimilars
              in the BCBS Massachusetts 2024 Commercial policy?
            </p>
          </div>
          <span className="text-[10px] text-slate-400 mt-2 font-mono uppercase">
            10:42 AM • SENT
          </span>
        </div>

        {/* AI response */}
        <div className="flex items-start gap-4 mb-2 max-w-[95%]">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shrink-0">
            <span
              className="material-symbols-outlined text-sm"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              psychology
            </span>
          </div>
          <div className="flex flex-col gap-6">
            <div className="bg-white rounded-2xl rounded-tl-none px-6 py-5 border border-slate-100 whisper-shadow">
              <p className="text-on-surface text-base leading-relaxed mb-4">
                According to the{" "}
                <span className="font-bold text-primary">
                  BCBSMA 2024 Commercial Pharmacy Medical Policy
                </span>
                , the criteria for Humira have been updated to prioritize
                "preferred biosimilars" before approving the reference brand.
              </p>
              <ul className="space-y-4 text-sm text-slate-700 list-disc pl-5">
                <li>
                  <strong>Step 1:</strong> Documented trial and failure of at
                  least two (2) preferred biosimilars (Adalimumab-adbm or
                  Hadlima).
                </li>
                <li>
                  <strong>Clinical Exception:</strong> Criteria for reference
                  Humira may be met if the patient has a documented
                  contraindication to all preferred biosimilars.
                </li>
                <li>
                  <strong>Policy Transition:</strong> For patients currently on
                  Humira, there is a 90-day grace period for re-authorization.
                </li>
              </ul>
            </div>

            {/* Citation cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {citations.map((cite, idx) => (
                <div
                  key={idx}
                  className="bg-slate-50 rounded-xl p-4 flex flex-col gap-3 group hover:bg-white transition-all duration-150 border border-transparent hover:border-primary/10"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary text-lg">
                        {cite.icon}
                      </span>
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tighter">
                        {cite.badge}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] bg-white px-2 py-0.5 rounded text-slate-500 border border-slate-200">
                      {cite.code}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-on-surface-variant line-clamp-1">
                    {cite.title}
                  </p>
                  <div className="flex items-center justify-between mt-1">
                    <span className="font-mono text-[10px] text-slate-400">
                      {cite.meta}
                    </span>
                    <button className="text-primary flex items-center gap-1 text-[11px] font-bold hover:underline">
                      VIEW CITATION
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Chat footer */}
      <footer className="w-full bg-white/80 backdrop-blur-md px-8 py-6 border-t border-slate-200/50">
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex flex-wrap gap-2">
            {suggestedPrompts.map((prompt, idx) => (
              <button
                key={idx}
                className="px-4 py-2 bg-white rounded-full text-xs font-medium text-slate-600 whisper-shadow hover:text-primary hover:scale-[1.02] transition-all flex items-center gap-2 border border-slate-100"
              >
                <span className="material-symbols-outlined text-base">
                  auto_awesome
                </span>
                {prompt}
              </button>
            ))}
          </div>
          <div className="relative">
            <div className="flex items-center bg-white rounded-2xl whisper-shadow border border-slate-200 px-4 py-2 group focus-within:border-primary/50 transition-colors">
              <span className="material-symbols-outlined text-slate-400 mr-3">
                chat_bubble
              </span>
              <input
                className="flex-1 bg-transparent border-none focus:ring-0 text-sm placeholder:text-slate-400 py-3"
                placeholder="Ask a clinical policy question..."
                type="text"
              />
              <div className="flex items-center gap-2">
                <button className="p-2 text-slate-400 hover:text-primary transition-colors">
                  <span className="material-symbols-outlined">attach_file</span>
                </button>
                <button className="bg-primary text-white p-2.5 rounded-xl flex items-center justify-center shadow-md shadow-primary/20">
                  <span className="material-symbols-outlined">send</span>
                </button>
              </div>
            </div>
            <p className="text-[10px] text-slate-400 text-center mt-3 font-medium uppercase tracking-widest">
              Powered by Policy Lens Medical Knowledge Base • v4.2.0
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
