# Policy Lens

**Real-time drug coverage intelligence for market access analysts.**

Policy Lens normalizes health insurance drug coverage policies across national payers into a single, queryable interface. Search a drug, get instant coverage status, prior auth requirements, step therapy protocols, and dosing limits across UnitedHealthcare, Aetna, Cigna, Anthem, Kaiser, and more — side by side.

---

## What It Does

- **Drug Lookup** — Search by drug name, NDC, or HCPCS code. Returns one card per payer with color-coded coverage badges: covered, covered with PA, or not covered.
- **Comparison View** — 9-row normalized grid comparing a single drug across up to 4 payers: coverage status, prior auth, step therapy, site of care, indications, quantity limits, access score, effective date, and policy source.
- **Policy Changes** — Timeline feed of policy updates classified as Clinical Major, Clinical Minor, Administrative, or Cosmetic — with before/after diffs highlighted inline.
- **Ask AI** — Chat interface grounded in the clinical knowledge base. Answers cite source policy documents with IDs.
- **Ingest Policies** — Drag-and-drop PDF upload, URL import, and auto-fetch by drug name. Runs OCR, entity extraction, and vectorization through a processing queue.
- **Policy Library** — Searchable, filterable index of 1,400+ clinical policy documents across 84 payer networks.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| Database | SQLite (`policies.db`) |
| Fonts | Manrope, DM Sans, IBM Plex Mono |
| Icons | Material Symbols Outlined |

---

## Schema

Six tables: `policies`, `drugs`, `covered_indications`, `excluded_indications`, `step_therapy`, `dosing_limits`. JSON columns store clinical criteria arrays, brand name lists, ICD-10 codes, and policy change history. All drug lookups join across these tables at query time — no denormalization.

---

## Running Locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# Runs on http://localhost:8000
```

**Frontend**
```bash
cd frontend
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