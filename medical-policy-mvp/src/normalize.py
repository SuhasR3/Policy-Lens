#!/usr/bin/env python3
"""
Normalize all JSON outputs into a SQLite database.

Handles two document_type values produced by the extraction pipeline:
  - "single_drug_policy"  (Florida Blue, BCBS NC, Cigna, ...)
  - "drug_list"           (UHC Botulinum, Priority Health MDL, ...)

Usage:
    python src/normalize.py                          # outputs/ → outputs/policies.db
    python src/normalize.py --outputs-dir outputs --db outputs/policies.db
    python src/normalize.py --reset                  # drop + recreate tables first
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS policies (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filename             TEXT UNIQUE,
    payer                       TEXT,
    policy_id                   TEXT,
    policy_title                TEXT,
    document_type               TEXT,
    effective_date              TEXT,
    revision_date               TEXT,
    prior_auth_required         INTEGER,   -- 0/1/NULL
    approval_duration_initial   TEXT,
    approval_duration_renewal   TEXT,
    site_of_care_restrictions   TEXT,
    general_requirements        TEXT,      -- JSON array
    preferred_products          TEXT,      -- JSON array
    policy_changes              TEXT,      -- JSON array
    raw_text                    TEXT
);

-- Drugs / drug-list rows both land here.
-- single_drug_policy uses: generic_name, brand_names, hcpcs_codes, is_biosimilar, reference_product
-- drug_list uses: hcpcs_code (singular), drug_name, description, coverage_level, notes, covered_alternatives
CREATE TABLE IF NOT EXISTS drugs (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id             INTEGER NOT NULL REFERENCES policies(id),
    -- single_drug_policy fields
    generic_name          TEXT,
    brand_names           TEXT,   -- JSON array
    hcpcs_codes           TEXT,   -- JSON array
    is_biosimilar         INTEGER, -- 0/1/NULL
    reference_product     TEXT,
    -- drug_list entry fields
    hcpcs_code            TEXT,
    drug_name             TEXT,
    description           TEXT,
    coverage_level        TEXT,
    notes                 TEXT,
    covered_alternatives  TEXT    -- JSON array
);

CREATE TABLE IF NOT EXISTS covered_indications (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id                     INTEGER NOT NULL REFERENCES policies(id),
    indication_name               TEXT,
    clinical_criteria             TEXT,  -- JSON array
    required_combination_regimens TEXT,  -- JSON array
    icd10_codes                   TEXT,  -- JSON array
    applies_to_products           TEXT   -- JSON array
);

CREATE TABLE IF NOT EXISTS step_therapy (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id             INTEGER NOT NULL REFERENCES policies(id),
    required_prior_drugs  TEXT,  -- JSON array
    condition_description TEXT,
    applies_to_products   TEXT   -- JSON array
);

CREATE TABLE IF NOT EXISTS dosing_limits (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id            INTEGER NOT NULL REFERENCES policies(id),
    description          TEXT,
    max_dose             TEXT,
    frequency            TEXT,
    max_units_per_period TEXT
);

CREATE TABLE IF NOT EXISTS excluded_indications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id   INTEGER NOT NULL REFERENCES policies(id),
    description TEXT
);

CREATE VIEW IF NOT EXISTS drugs_unified AS
SELECT
    d.id,
    d.policy_id,
    p.source_filename,
    p.payer,
    p.document_type,
    COALESCE(d.drug_name, d.generic_name)  AS drug_name,
    d.generic_name,
    d.brand_names,
    COALESCE(d.hcpcs_code,
        CASE WHEN d.hcpcs_codes IS NOT NULL AND d.hcpcs_codes != '[]'
             THEN json_extract(d.hcpcs_codes, '$[0]')
        END)                                AS hcpcs_code,
    d.hcpcs_codes,
    d.is_biosimilar,
    d.reference_product,
    d.description,
    d.coverage_level,
    d.notes,
    d.covered_alternatives
FROM drugs d
JOIN policies p ON d.policy_id = p.id;
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _j(value: object) -> str | None:
    """Serialize a list/dict to compact JSON text.

    Always returns a JSON string for lists (even empty ones) so that
    drug rows from single_drug_policy with hcpcs_codes=[] are stored as
    '[]' rather than NULL — NULL is reserved for truly absent/unknown data.
    Returns None only when value is None.
    """
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


_NA_PATTERN = re.compile(r"^(?:n/?a|none|null|unknown|-+|\.+)$", re.IGNORECASE)


def _sanitize(value: str | None) -> str | None:
    """Return None for blank / sentinel strings like 'N/A', 'None', '---'."""
    if value is None:
        return None
    value = value.strip()
    if not value or _NA_PATTERN.match(value):
        return None
    return value


_DESC_DRUG_RE = re.compile(
    r"^(?:injection|infusion|inhalation\s+solution)[,;:\s]+(.+?)"
    r"(?:,\s*(?:biosimilar|per|each|\d))",
    re.IGNORECASE,
)


def _drug_name_from_description(desc: str | None) -> str | None:
    """Try to extract a drug name from an HCPCS-style description string.

    Handles two common formats:
      "Injection, aflibercept-abzv (enzeevu), biosimilar, 1 mg"
      "Leuprolide injectable (camcevi etm), 1 mg"
    """
    if not desc:
        return None
    text = desc.strip()
    m = _DESC_DRUG_RE.match(text)
    if m:
        return m.group(1).strip()
    # Fallback: first comma-delimited segment, stripped of dosage info
    first_seg = text.split(",")[0].strip()
    if first_seg and not first_seg[0].isdigit() and len(first_seg) > 2:
        return first_seg
    return None


def _build_mdl_lookup(data: dict) -> dict[str, str]:
    """Build {hcpcs_code: drug_name} from master_drug_code_list (Shape B files)."""
    lookup: dict[str, str] = {}
    for item in data.get("master_drug_code_list") or []:
        code = _sanitize(item.get("hcpcs_code"))
        name = _sanitize(item.get("drug_name"))
        if code and name:
            lookup[code] = name
    return lookup


def _resolve_payer(data: dict) -> str | None:
    """Extract payer from either Shape A or Shape B JSON, with entry fallback."""
    if "document" in data and isinstance(data["document"], dict):
        doc = data["document"]
        payer = doc.get("payer") or data.get("payer")
        if not payer:
            entries = doc.get("entries") or []
            if entries:
                payer = entries[0].get("payer")
        return payer
    payer = data.get("payer")
    if not payer:
        entries = data.get("entries") or []
        if entries:
            payer = entries[0].get("payer")
    return payer


def _entry_count(data: dict) -> int:
    """Count drug/entry rows in a parsed JSON document."""
    if "document" in data and isinstance(data["document"], dict):
        return len(data["document"].get("entries") or [])
    if "entries" in data:
        return len(data.get("entries") or [])
    return len(data.get("drugs") or [])


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_policy_document(con: sqlite3.Connection, data: dict, source_filename: str) -> None:
    """Insert a single_drug_policy document into all relevant tables."""
    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO policies (
            source_filename, payer, policy_id, policy_title, document_type,
            effective_date, revision_date, prior_auth_required,
            approval_duration_initial, approval_duration_renewal,
            site_of_care_restrictions, general_requirements,
            preferred_products, policy_changes, raw_text
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            source_filename,
            data.get("payer"),
            data.get("policy_id"),
            data.get("policy_title"),
            data.get("document_type", "single_drug_policy"),
            data.get("effective_date"),
            data.get("revision_date"),
            _bool_to_int(data.get("prior_auth_required")),
            data.get("approval_duration_initial"),
            data.get("approval_duration_renewal"),
            data.get("site_of_care_restrictions"),
            _j(data.get("general_requirements")),
            _j(data.get("preferred_products")),
            _j(data.get("policy_changes")),
            data.get("raw_text"),
        ),
    )
    policy_row_id = cur.lastrowid

    for drug in data.get("drugs") or []:
        generic = _sanitize(drug.get("generic_name"))
        codes = drug.get("hcpcs_codes") or []
        brands = drug.get("brand_names") or []

        first_code = codes[0] if codes else None
        unified_name = generic or (brands[0] if brands else None)

        cur.execute(
            """
            INSERT INTO drugs (
                policy_id, generic_name, brand_names, hcpcs_codes,
                is_biosimilar, reference_product,
                hcpcs_code, drug_name
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                policy_row_id,
                generic,
                _j(brands),
                _j(codes),
                _bool_to_int(drug.get("is_biosimilar")),
                drug.get("reference_product"),
                first_code,
                unified_name,
            ),
        )

    for ind in data.get("covered_indications") or []:
        cur.execute(
            """
            INSERT INTO covered_indications (
                policy_id, indication_name, clinical_criteria,
                required_combination_regimens, icd10_codes, applies_to_products
            ) VALUES (?,?,?,?,?,?)
            """,
            (
                policy_row_id,
                ind.get("indication_name"),
                _j(ind.get("clinical_criteria")),
                _j(ind.get("required_combination_regimens")),
                _j(ind.get("icd10_codes")),
                _j(ind.get("applies_to_products")),
            ),
        )

    for st in data.get("step_therapy") or []:
        cur.execute(
            """
            INSERT INTO step_therapy (
                policy_id, required_prior_drugs, condition_description, applies_to_products
            ) VALUES (?,?,?,?)
            """,
            (
                policy_row_id,
                _j(st.get("required_prior_drugs")),
                st.get("condition_description"),
                _j(st.get("applies_to_products")),
            ),
        )

    for dl in data.get("dosing_limits") or []:
        cur.execute(
            """
            INSERT INTO dosing_limits (
                policy_id, description, max_dose, frequency, max_units_per_period
            ) VALUES (?,?,?,?,?)
            """,
            (
                policy_row_id,
                dl.get("description"),
                dl.get("max_dose"),
                dl.get("frequency"),
                dl.get("max_units_per_period"),
            ),
        )

    for excl in data.get("excluded_indications") or []:
        cur.execute(
            "INSERT INTO excluded_indications (policy_id, description) VALUES (?,?)",
            (policy_row_id, excl),
        )

    con.commit()
    logger.info("  Loaded single_drug_policy → policy row %d", policy_row_id)


def _load_drug_list(con: sqlite3.Connection, data: dict, source_filename: str) -> None:
    """
    Insert a drug_list document.

    Supports both top-level shapes produced by the pipeline:
      Shape A  { payer, document_type, source_filename, entries: [...] }
      Shape B  { document_type, document: { payer, entries: [...] } }
    """
    cur = con.cursor()

    # Resolve shape
    if "document" in data and isinstance(data["document"], dict):
        doc = data["document"]
        payer = doc.get("payer") or data.get("payer")
        policy_title = doc.get("policy_title")
        effective_date = doc.get("effective_date")
        entries = doc.get("entries") or []
    else:
        payer = data.get("payer")
        policy_title = None
        effective_date = None
        entries = data.get("entries") or []

    # Fall back to the payer field stored on individual entries when root payer is absent
    if not payer and entries:
        payer = entries[0].get("payer")

    cur.execute(
        """
        INSERT INTO policies (
            source_filename, payer, document_type, policy_title, effective_date
        ) VALUES (?,?,?,?,?)
        """,
        (
            source_filename or data.get("source_filename"),
            payer,
            "drug_list",
            policy_title,
            effective_date,
        ),
    )
    policy_row_id = cur.lastrowid

    mdl_lookup = _build_mdl_lookup(data)

    for entry in entries:
        hcpcs = _sanitize(entry.get("hcpcs_code"))
        name  = _sanitize(entry.get("drug_name"))
        desc  = entry.get("description")

        if not name and hcpcs and hcpcs in mdl_lookup:
            name = mdl_lookup[hcpcs]
        if not name:
            name = _drug_name_from_description(desc)

        cur.execute(
            """
            INSERT INTO drugs (
                policy_id, hcpcs_code, drug_name, description,
                coverage_level, notes, covered_alternatives
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                policy_row_id,
                hcpcs,
                name,
                desc,
                entry.get("coverage_level"),
                entry.get("notes"),
                _j(entry.get("covered_alternatives")),
            ),
        )

    con.commit()
    logger.info(
        "  Loaded drug_list → policy row %d (%d drug entries)",
        policy_row_id,
        len(entries),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def normalize(outputs_dir: Path, db_path: Path, reset: bool = False) -> None:
    json_files = sorted(outputs_dir.glob("*.json"))
    if not json_files:
        logger.warning("No JSON files found in %s", outputs_dir)
        return

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")

    if reset:
        logger.info("Dropping existing tables...")
        con.execute("DROP VIEW IF EXISTS drugs_unified")
        tables = [
            "excluded_indications", "dosing_limits", "step_therapy",
            "covered_indications", "drugs", "policies",
        ]
        for t in tables:
            con.execute(f"DROP TABLE IF EXISTS {t}")
        con.commit()

    con.executescript(DDL)
    con.commit()

    # Pre-scan all files and pick the largest per (payer, doc_type) to
    # avoid loading duplicate/overlapping extractions of the same source.
    file_data: list[tuple[Path, dict]] = []
    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Skipping %s (invalid JSON): %s", path.name, exc)
            continue
        file_data.append((path, data))

    # Build per-file metadata for dedup
    file_meta: list[tuple[Path, dict, str, str, int]] = []
    for path, data in file_data:
        doc_type = data.get("document_type") or ""
        payer = (_resolve_payer(data) or "").lower().strip()
        count = _entry_count(data)
        file_meta.append((path, data, doc_type, payer, count))

    # Group files that share a doc_type and whose payer strings overlap
    # (one is a prefix of the other, with a minimum length to avoid empty
    # strings matching everything).
    skip_paths: set[Path] = set()
    for i, (p_i, _, dt_i, pay_i, cnt_i) in enumerate(file_meta):
        for j, (p_j, _, dt_j, pay_j, cnt_j) in enumerate(file_meta):
            if i >= j or dt_i != dt_j:
                continue
            payers_overlap = (
                pay_i and pay_j
                and (pay_i.startswith(pay_j) or pay_j.startswith(pay_i))
            )
            if not payers_overlap:
                continue
            loser = p_i if cnt_i <= cnt_j else p_j
            skip_paths.add(loser)

    for path, data in file_data:
        logger.info("Processing %s", path.name)

        if path in skip_paths:
            logger.info("  Skipping (duplicate payer/type, smaller file)")
            continue

        already = con.execute(
            "SELECT id FROM policies WHERE source_filename = ?", (path.name,)
        ).fetchone()
        if already:
            logger.info("  Already in DB (policy row %d) — skipping", already[0])
            continue

        doc_type = data.get("document_type")

        if doc_type == "drug_list":
            _load_drug_list(con, data, path.name)
        elif doc_type == "single_drug_policy":
            _load_policy_document(con, data, path.name)
        else:
            logger.warning("  Unknown document_type=%r — skipping", doc_type)

    con.close()
    logger.info("Done. Database written to %s", db_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    _root = Path(__file__).resolve().parent.parent
    default_outputs = _root / "outputs"
    default_db = default_outputs / "policies.db"

    parser = argparse.ArgumentParser(description="Normalize policy JSON outputs to SQLite")
    parser.add_argument(
        "--outputs-dir", type=Path, default=default_outputs,
        help="Directory containing extracted JSON files (default: outputs/)",
    )
    parser.add_argument(
        "--db", type=Path, default=default_db,
        help="Path for the output SQLite database (default: outputs/policies.db)",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Drop and recreate all tables before loading",
    )
    args = parser.parse_args()

    if not args.outputs_dir.is_dir():
        logger.error("outputs-dir not found: %s", args.outputs_dir)
        sys.exit(1)

    normalize(args.outputs_dir, args.db, reset=args.reset)


if __name__ == "__main__":
    main()
