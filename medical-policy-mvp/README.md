# Medical Policy MVP

This repo extracts structured drug-coverage data from payer PDFs into JSON, normalizes those JSON files into SQLite, and can build a deterministic markdown master drug table.

## Pipeline

1. Extract JSON from PDFs:

```bash
.venv/bin/python main.py
```

To extract a single document:

```bash
.venv/bin/python src/extract.py --single "docs/Priority Health 2026 MDL - Priority Health Commercial (Employer Group) and MyPriority.pdf"
```

For large drug-list PDFs, extraction now prefers page-local table parsing with HCPCS/CPT row anchors and source-page tracking before falling back to LLM chunk extraction.

2. Normalize JSON into SQLite:

```bash
.venv/bin/python src/normalize.py --reset --outputs-dir outputs --db outputs/policies.db
```

Normalization preserves both:

- `drug_name_raw`: the exact source value when present
- `drug_name_normalized`: the repaired label used for matching

The normalized schema now also captures richer access-management detail in `drugs` and the `drug_access_summary` view, including:

- `drug_category`
- `access_status_raw` and `access_status_group`
- `category_access_position`, `category_total_drugs`, `category_preferred_drugs`, `category_nonpreferred_drugs`
- `covered_diagnoses`
- `prior_auth_required` and `prior_auth_criteria`
- `step_therapy_required` and `step_therapy_details`
- `site_of_care_required` and `site_of_care_details`
- `dosing_limit_summary`

If multiple overlapping JSONs exist for the same payer/document type, the normalizer prefers the best-ranked source. For Priority Health, the canonical source is:

- `outputs/Priority Health 2026 MDL - Priority Health Commercial (Employer Group) and MyPriority.json`

That file is preferred over:

- `outputs/priority_health_2026_mdl_extracted.json`

3. Build the markdown master table:

```bash
.venv/bin/python build_master_table.py --db outputs/policies.db --output outputs/master_drug_table.md
```

Optional payer filter:

```bash
.venv/bin/python build_master_table.py --db outputs/policies.db --output outputs/priority_health_master_drug_table.md --payer "Priority Health"
```

## Reproducibility

To rebuild the final markdown output from repo contents alone:

```bash
.venv/bin/python src/normalize.py --reset --outputs-dir outputs --db outputs/policies.db
.venv/bin/python build_master_table.py --db outputs/policies.db --output outputs/priority_health_master_drug_table.md --payer "Priority Health"
```

## Tests

Run the regression suite with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
