# Policy Lens

**Real-time drug coverage intelligence for market access analysts.**

Policy Lens turns 2 days of manual PDF reading into a 10-second answer. Market access analysts at firms like Anton Rx currently spend hours visiting each payer's website, downloading PDFs, and manually normalizing coverage data. Policy Lens ingests medical benefit drug policies from multiple payers, extracts structured coverage data, and surfaces it through a searchable, comparable, and change-tracked interface — all in one place.

> **Anton Rx Challenge — Medical Benefit Drug Policy Tracker**
> Innovation Hacks 2.0 · Arizona State University · April 2026

---

## The Problem We're Solving

Health plans govern medical benefit drug coverage through individual policy documents that vary by payer and change frequently. There is no centralized source for tracking which drugs are covered, what clinical criteria apply, or how policies differ across plans. An analyst answering "What does Cigna require for Humira?" currently opens 10 PDFs, reads each one, and manually normalizes the information. This takes hours. Policy Lens makes it 10 seconds.

---

## Key Features

- **Drug Lookup** — Search by drug name, NDC, or HCPCS code. Returns one card per payer with color-coded coverage badges: covered, covered with PA, or not covered. See coverage across 400+ payers instantly with PA status, step therapy, and tier information.
- **Cross-Payer Comparison** — Side-by-side 9-row normalized grid comparing a single drug across up to 4 payers: coverage status, prior auth, step therapy, site of care, indications, quantity limits, access score, effective date, and policy source. Color-coded differences across UHC, Cigna, Aetna, and BCBS.
- **PA Friction Heatmap** — Not just covered/not covered — a 1–10 friction score showing how hard it actually is to get each drug approved at each payer.
- **Policy Change Tracker** — Detects clinical vs. cosmetic changes automatically. Shows word-level diffs. Classifies changes as Clinical Major, Clinical Minor, Administrative, or Cosmetic. Full timeline feed of policy updates with before/after diffs highlighted inline.
- **Step Therapy Ladder** — Visual flowchart of every drug a patient must try and fail before being approved, per payer. Shows minimum time to treatment.
- **Market Positioning Map** — Bubble chart showing each drug's rebate leverage based on competitive position and payer breadth.
- **AI Ask** — Natural language Q&A grounded in indexed policy documents with source citations. Chat interface answers cite source policy documents with IDs.
- **Ingest Policies** — Drag-and-drop PDF upload, URL import, and auto-fetch by drug name. Handles UHC single-drug PDFs, UPMC mega-documents (200+ pages), and BCBS web portals. Runs OCR, entity extraction, and vectorization through a processing queue.
- **Policy Library** — Searchable, filterable index of 1,400+ clinical policy documents across 84 payer networks.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| PDF Parsing | PyMuPDF + pdfplumber |
| LLM | Claude Sonnet / Gemini 1.5 Pro |
| Embeddings | sentence-transformers |
| Vector DB | ChromaDB |
| Relational DB | SQLite (`policies.db`) |
| Web Scraping | Playwright |
| Fonts | Manrope, DM Sans, IBM Plex Mono |
| Icons | Material Symbols Outlined |

---

## Schema

Six tables: `policies`, `drugs`, `covered_indications`, `excluded_indications`, `step_therapy`, `dosing_limits`. JSON columns store clinical criteria arrays, brand name lists, ICD-10 codes, and policy change history. All drug lookups join across these tables at query time — no denormalization.

---

## Real Data Sources

- **UHC** — uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/
- **Aetna** — aetna.com clinical program summary PDFs
- **Cigna** — static.cigna.com drug policy A-Z index
- **UPMC** — Prior authorization policies portal

---

## Running Locally

**Backend**
```bash
cd policy-lens/backend
pip install -r requirements.txt
cp .env.template .env
# Add your API keys to .env
uvicorn main:app --reload
# Runs on http://localhost:8000
```

**Frontend**
```bash
cd policy-lens/frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

Copy `policies.db` into `backend/` before starting the server.

---

## API

```
GET /api/drugs/search?q={query}
GET /api/comparison?drug={name}&payers={payer1,payer2,payer3,payer4}
```

---

## Who It's For

Market access analysts, HEOR teams, and payer relations managers who currently track coverage policies across spreadsheets and PDF portals. Policy Lens replaces that workflow with structured, searchable, comparable data in one place.

---

Built with FastAPI + React. No third-party analytics. No ads.
