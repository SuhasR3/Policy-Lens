#!/usr/bin/env python3
"""
Normalize all JSON outputs into a SQLite database.

Handles two document_type values produced by the extraction pipeline:
  - "single_drug_policy"
  - "drug_list"
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

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
    prior_auth_required         INTEGER,
    approval_duration_initial   TEXT,
    approval_duration_renewal   TEXT,
    site_of_care_restrictions   TEXT,
    general_requirements        TEXT,
    preferred_products          TEXT,
    policy_changes              TEXT,
    raw_text                    TEXT
);

CREATE TABLE IF NOT EXISTS drugs (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id             INTEGER NOT NULL REFERENCES policies(id),
    generic_name          TEXT,
    brand_names           TEXT,
    hcpcs_codes           TEXT,
    is_biosimilar         INTEGER,
    reference_product     TEXT,
    hcpcs_code            TEXT,
    drug_name             TEXT,
    drug_name_raw         TEXT,
    drug_name_normalized  TEXT,
    description           TEXT,
    coverage_level        TEXT,
    notes                 TEXT,
    covered_alternatives  TEXT,
    source_page           INTEGER,
    therapeutic_class     TEXT,
    drug_category         TEXT,
    access_status_raw     TEXT,
    access_status_group   TEXT,
    category_total_drugs  INTEGER,
    category_preferred_drugs INTEGER,
    category_nonpreferred_drugs INTEGER,
    category_access_position TEXT,
    prior_auth_required   INTEGER,
    prior_auth_criteria   TEXT,
    step_therapy_required INTEGER,
    step_therapy_details  TEXT,
    site_of_care_required INTEGER,
    site_of_care_details  TEXT,
    dosing_limit_summary  TEXT,
    covered_diagnoses     TEXT
);

CREATE TABLE IF NOT EXISTS covered_indications (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id                     INTEGER NOT NULL REFERENCES policies(id),
    indication_name               TEXT,
    clinical_criteria             TEXT,
    required_combination_regimens TEXT,
    icd10_codes                   TEXT,
    applies_to_products           TEXT
);

CREATE TABLE IF NOT EXISTS step_therapy (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id             INTEGER NOT NULL REFERENCES policies(id),
    required_prior_drugs  TEXT,
    condition_description TEXT,
    applies_to_products   TEXT
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
    p.policy_title,
    p.document_type,
    p.effective_date,
    COALESCE(d.drug_name_normalized, d.drug_name, d.generic_name) AS drug_name,
    d.drug_name_raw,
    d.drug_name_normalized,
    d.generic_name,
    d.brand_names,
    COALESCE(d.hcpcs_code,
        CASE WHEN d.hcpcs_codes IS NOT NULL AND d.hcpcs_codes != '[]'
             THEN json_extract(d.hcpcs_codes, '$[0]')
        END) AS hcpcs_code,
    d.hcpcs_codes,
    d.is_biosimilar,
    d.reference_product,
    d.description,
    d.coverage_level,
    d.notes,
    d.covered_alternatives,
    d.source_page,
    d.therapeutic_class,
    d.drug_category,
    d.access_status_raw,
    d.access_status_group,
    d.category_total_drugs,
    d.category_preferred_drugs,
    d.category_nonpreferred_drugs,
    d.category_access_position,
    d.prior_auth_required,
    d.prior_auth_criteria,
    d.step_therapy_required,
    d.step_therapy_details,
    d.site_of_care_required,
    d.site_of_care_details,
    d.dosing_limit_summary,
    d.covered_diagnoses
FROM drugs d
JOIN policies p ON d.policy_id = p.id;

CREATE VIEW IF NOT EXISTS drug_access_summary AS
SELECT
    p.payer,
    p.policy_title,
    p.effective_date,
    d.hcpcs_code,
    COALESCE(d.drug_name_normalized, d.drug_name, d.generic_name) AS drug_name_normalized,
    d.drug_name_raw,
    COALESCE(d.drug_category, d.therapeutic_class) AS drug_category,
    d.access_status_raw,
    d.access_status_group,
    d.category_access_position,
    d.category_total_drugs,
    d.category_preferred_drugs,
    d.category_nonpreferred_drugs,
    d.covered_diagnoses,
    d.prior_auth_required,
    d.prior_auth_criteria,
    d.step_therapy_required,
    d.step_therapy_details,
    d.site_of_care_required,
    d.site_of_care_details,
    d.dosing_limit_summary,
    p.source_filename,
    d.source_page
FROM drugs d
JOIN policies p ON p.id = d.policy_id;
"""


def _j(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


_NA_PATTERN = re.compile(r"^(?:n/?a|none|null|unknown|-+|\.+)$", re.IGNORECASE)
_CODE_PATTERN = re.compile(r"^(?:[A-Z]\d{4}|\d{5})$")
_PACKAGING_PATTERN = re.compile(
    r"\b(?:vial|suv|pf|syringe|kit|carton|single-dose|single dose|ml|mg|mg/ml)\b",
    re.IGNORECASE,
)
_CONTAMINATION_PHRASES = (
    "injection,",
    " commercial ",
    " mypriority",
    " drugs ",
    " coverage ",
    "notes",
    "restrictions",
    "hcpcs",
    "cpt",
)


def _sanitize(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    if not value or _NA_PATTERN.match(value):
        return None
    return value


def _clean_name_fragment(text: str | None) -> str | None:
    text = _sanitize(text)
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip(" ,;:-")
    text = re.sub(r"\s+\([A-Z]{1,4}\)$", "", text).strip()
    return text or None


def _looks_contaminated(name: str | None) -> bool:
    text = _sanitize(name)
    if not text:
        return True
    lowered = f" {text.lower()} "
    if any(phrase in lowered for phrase in _CONTAMINATION_PHRASES):
        return True
    if _CODE_PATTERN.match(text):
        return True
    if len(text) > 80:
        return True
    if re.search(r"\b[A-Z]\d{4}\b", text):
        return True
    if re.search(r"\b(?:drugs|commercial and mypriority|priority health)\b", lowered):
        return True
    if re.search(r"\b(?:vial p/f,suv|ml vial p/f,suv|p/f,suv)\b", lowered) and len(text.split()) <= 4:
        return True
    if text.isupper() and _PACKAGING_PATTERN.search(text) and len(text.split()) <= 4:
        return True
    if re.search(r"\b[A-Z][A-Z0-9/-]{4,}\b.*\b[A-Z][A-Z0-9/-]{4,}\b", text) and _PACKAGING_PATTERN.search(text):
        return True
    if re.search(r"\b(?:glucagon|mesna|bevacizumab|aflibercept)\b", lowered) and re.search(
        r"\b(?:desferal|mesnex|avastin)\b", lowered
    ):
        return True
    return False


def _drug_name_from_description(desc: str | None) -> str | None:
    text = _sanitize(desc)
    if not text:
        return None

    patterns = [
        r"^(?:Injection|Infusion|Inhalation solution),\s*([^,]+(?:\([^)]+\))?)\s*,\s*(?:biosimilar|per\b|\d|\w+\s*\d)",
        r"^([^,]+?(?:injectable|intravenous|subcutaneous)?(?:\s*\([^)]+\))?)\s*,\s*(?:per\b|\d)",
        r"^(?:Injection|Infusion),\s*([^,]+?)(?:,\s*not therapeutically equivalent\b|,\s*otherwise specified\b|,\s*per\b|,\s*\d)",
    ]
    for pattern in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return _clean_name_fragment(match.group(1))

    first = _clean_name_fragment(text.split(",")[0])
    if first and not first[0].isdigit():
        return first
    return None


def _build_mdl_lookup(data: dict) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for item in data.get("master_drug_code_list") or []:
        code = _sanitize(item.get("hcpcs_code"))
        name = _clean_name_fragment(item.get("drug_name"))
        if code and name and not _looks_contaminated(name):
            lookup[code] = name
    return lookup


def _resolve_payer(data: dict) -> str | None:
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
    if "document" in data and isinstance(data["document"], dict):
        return len(data["document"].get("entries") or [])
    if "entries" in data:
        return len(data.get("entries") or [])
    return len(data.get("drugs") or [])


def _filename_family(path: Path, data: dict) -> str:
    source = " ".join(
        filter(
            None,
            [
                str(data.get("source_filename") or ""),
                path.stem,
            ],
        )
    ).lower()
    return re.sub(r"[^a-z0-9]+", "", source)


def _source_rank(path: Path, data: dict) -> tuple[int, int, int, str]:
    name = path.name.lower()
    score = 0
    if path.name == "Priority Health 2026 MDL - Priority Health Commercial (Employer Group) and MyPriority.json":
        score += 1000
    if "priority" in name and "master" not in name and "extracted" not in name:
        score += 40
    if "extracted" in name:
        score -= 100
    if "drug list" in json.dumps(data)[:500].lower():
        score += 5
    return (score, _entry_count(data), len(path.name), path.name)


def _iter_drug_list_entries(data: dict) -> list[dict[str, Any]]:
    if "document" in data and isinstance(data["document"], dict):
        return data["document"].get("entries") or []
    return data.get("entries") or []


def _build_global_code_lookup(file_data: list[tuple[Path, dict]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    ranked = sorted(file_data, key=lambda item: _source_rank(item[0], item[1]), reverse=True)
    for path, data in ranked:
        doc_type = data.get("document_type")
        if doc_type != "drug_list":
            continue
        for code, name in _build_mdl_lookup(data).items():
            lookup.setdefault(code, name)
        for entry in _iter_drug_list_entries(data):
            code = _sanitize(entry.get("hcpcs_code"))
            raw = _clean_name_fragment(entry.get("drug_name"))
            desc_name = _drug_name_from_description(entry.get("description"))
            candidate = None
            if raw and not _looks_contaminated(raw):
                candidate = raw
            elif desc_name:
                candidate = desc_name
            if code and candidate:
                lookup.setdefault(code, candidate)
    logger.info("Built trusted code/name lookup with %d codes", len(lookup))
    return lookup


def _derive_generic_and_brand(
    raw_name: str | None,
    normalized_name: str | None,
    description_name: str | None,
) -> tuple[str | None, list[str]]:
    generic_name = None
    brand_names: list[str] = []

    if description_name:
        generic_name = description_name
    elif normalized_name and normalized_name.islower():
        generic_name = normalized_name

    raw = _clean_name_fragment(raw_name)
    norm = _clean_name_fragment(normalized_name)
    if raw and not _looks_contaminated(raw):
        if generic_name and raw.lower() != generic_name.lower():
            brand_names.append(raw)
        elif raw.isupper():
            brand_names.append(raw)
        else:
            generic_name = generic_name or raw

    if norm and generic_name and norm.lower() != generic_name.lower() and norm not in brand_names and norm.isupper():
        brand_names.append(norm)

    if norm and not generic_name and not norm.isupper():
        generic_name = norm

    deduped = list(dict.fromkeys(brand_names))
    return generic_name, deduped


def _categorize_access_status(coverage_level: str | None) -> str | None:
    text = _sanitize(coverage_level)
    if not text:
        return None
    lowered = text.lower()
    if "not covered" in lowered:
        return "not_covered"
    if "preferred" in lowered and "non-" not in lowered:
        return "preferred"
    if "non-preferred" in lowered:
        return "non_preferred"
    if "non-specialty" in lowered:
        return "non_specialty"
    if "specialty" in lowered:
        return "specialty"
    if "covered" in lowered:
        return "covered"
    return "other"


def _extract_icd_tokens(text: str | None) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r"\b[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]+)?(?:\s*-\s*[A-TV-Z]?[0-9][0-9A-Z](?:\.[0-9A-Z]+)?)?\b", text)
    return list(dict.fromkeys(token.strip() for token in tokens))


def _parse_row_management_fields(
    notes: str | None,
    coverage_level: str | None,
) -> dict[str, Any]:
    text = _sanitize(notes)
    lowered = (text or "").lower()
    prior_auth = "pa" in lowered.split() or lowered.startswith("pa") or "prior auth" in lowered or "prior authorization" in lowered
    step_therapy = "step therapy" in lowered or re.search(r"\bst\b", lowered) is not None
    site_of_care = "site of service" in lowered or re.search(r"\bsos\b", lowered) is not None
    diagnoses = _extract_icd_tokens(text)
    dosing_bits = []
    if text and re.search(r"\b(?:per\s+\d|maximum|max dose|dose limit|quantity limit)\b", lowered):
        dosing_bits.append(text)

    return {
        "access_status_raw": _sanitize(coverage_level),
        "access_status_group": _categorize_access_status(coverage_level),
        "prior_auth_required": prior_auth,
        "prior_auth_criteria": text if prior_auth else None,
        "step_therapy_required": step_therapy,
        "step_therapy_details": text if step_therapy else None,
        "site_of_care_required": site_of_care,
        "site_of_care_details": text if site_of_care else None,
        "dosing_limit_summary": " | ".join(dosing_bits) if dosing_bits else None,
        "covered_diagnoses": diagnoses,
    }


def _policy_management_fields(data: dict, drug: dict[str, Any]) -> dict[str, Any]:
    indication_names = [item.get("indication_name") for item in data.get("covered_indications") or [] if item.get("indication_name")]
    indication_criteria = []
    for item in data.get("covered_indications") or []:
        if item.get("indication_name"):
            indication_criteria.append(item["indication_name"])
        indication_criteria.extend(item.get("clinical_criteria") or [])
        indication_criteria.extend(item.get("icd10_codes") or [])
    step_details = []
    for item in data.get("step_therapy") or []:
        drugs = ", ".join(item.get("required_prior_drugs") or [])
        condition = item.get("condition_description")
        summary = " | ".join(part for part in (drugs, condition) if part)
        if summary:
            step_details.append(summary)
    dosing = []
    for item in data.get("dosing_limits") or []:
        summary = " | ".join(
            part
            for part in (
                item.get("description"),
                item.get("max_dose"),
                item.get("frequency"),
                item.get("max_units_per_period"),
            )
            if part
        )
        if summary:
            dosing.append(summary)

    access_status_group = "preferred" if (drug.get("brand_names") and any(name in (data.get("preferred_products") or []) for name in drug.get("brand_names") or [])) else None
    return {
        "drug_category": None,
        "access_status_raw": None,
        "access_status_group": access_status_group,
        "prior_auth_required": bool(data.get("prior_auth_required")),
        "prior_auth_criteria": " | ".join(indication_criteria) if data.get("prior_auth_required") and indication_criteria else None,
        "step_therapy_required": bool(data.get("step_therapy")),
        "step_therapy_details": " || ".join(step_details) if step_details else None,
        "site_of_care_required": bool(_sanitize(data.get("site_of_care_restrictions"))),
        "site_of_care_details": _sanitize(data.get("site_of_care_restrictions")),
        "dosing_limit_summary": " || ".join(dosing) if dosing else None,
        "covered_diagnoses": indication_names,
    }


def _apply_category_access_metrics(con: sqlite3.Connection, policy_row_id: int) -> None:
    rows = con.execute(
        """
        SELECT id, COALESCE(drug_category, therapeutic_class), drug_name_normalized, access_status_group
        FROM drugs
        WHERE policy_id = ?
        """,
        (policy_row_id,),
    ).fetchall()
    by_category: dict[str, list[tuple[int, str | None, str | None]]] = {}
    for row_id, category, drug_name_normalized, access_status_group in rows:
        if not category or not drug_name_normalized:
            continue
        by_category.setdefault(category, []).append((row_id, drug_name_normalized, access_status_group))

    for category, items in by_category.items():
        distinct_names = {name for _, name, _ in items if name}
        preferred_names = {name for _, name, status in items if name and status == "preferred"}
        nonpreferred_names = {name for _, name, status in items if name and status == "non_preferred"}
        bucket_counts: dict[str, int] = {}
        for _, name, status in items:
            if status and name:
                bucket_counts.setdefault(status, set()).add(name)
        bucket_sizes = {status: len(names) for status, names in bucket_counts.items()}

        total = len(distinct_names)
        preferred_total = len(preferred_names)
        nonpreferred_total = len(nonpreferred_names)
        for row_id, _, status in items:
            position = None
            if status and bucket_sizes.get(status):
                label = status.replace("_", "-")
                position = f"{label} 1 of {bucket_sizes[status]}"
            con.execute(
                """
                UPDATE drugs
                SET category_total_drugs = ?,
                    category_preferred_drugs = ?,
                    category_nonpreferred_drugs = ?,
                    category_access_position = ?
                WHERE id = ?
                """,
                (total, preferred_total, nonpreferred_total, position, row_id),
            )


def _repair_drug_name(
    hcpcs: str | None,
    raw_name: str | None,
    description: str | None,
    trusted_lookup: dict[str, str],
) -> tuple[str | None, str | None]:
    raw_clean = _clean_name_fragment(raw_name)
    desc_name = _drug_name_from_description(description)

    if raw_clean and not _looks_contaminated(raw_clean):
        return raw_clean, desc_name

    if raw_clean:
        logger.info("Rejecting contaminated drug_name for code=%s: %r", hcpcs, raw_clean)

    if hcpcs and hcpcs in trusted_lookup:
        repaired = trusted_lookup[hcpcs]
        logger.info("Repaired drug_name for code=%s via trusted lookup: %r", hcpcs, repaired)
        return repaired, desc_name

    if desc_name:
        logger.info("Repaired drug_name for code=%s via description parse: %r", hcpcs, desc_name)
        return desc_name, desc_name

    return raw_clean, desc_name


def _load_policy_document(con: sqlite3.Connection, data: dict, source_filename: str) -> None:
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
        mgmt = _policy_management_fields(data, drug)

        cur.execute(
            """
            INSERT INTO drugs (
                policy_id, generic_name, brand_names, hcpcs_codes,
                is_biosimilar, reference_product,
                hcpcs_code, drug_name, drug_name_raw, drug_name_normalized,
                drug_category, access_status_raw, access_status_group,
                prior_auth_required, prior_auth_criteria,
                step_therapy_required, step_therapy_details,
                site_of_care_required, site_of_care_details,
                dosing_limit_summary, covered_diagnoses
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                unified_name,
                unified_name,
                mgmt["drug_category"],
                mgmt["access_status_raw"],
                mgmt["access_status_group"],
                _bool_to_int(mgmt["prior_auth_required"]),
                mgmt["prior_auth_criteria"],
                _bool_to_int(mgmt["step_therapy_required"]),
                mgmt["step_therapy_details"],
                _bool_to_int(mgmt["site_of_care_required"]),
                mgmt["site_of_care_details"],
                mgmt["dosing_limit_summary"],
                _j(mgmt["covered_diagnoses"]),
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
    _apply_category_access_metrics(con, policy_row_id)
    con.commit()
    logger.info("Loaded single_drug_policy %s into row %d", source_filename, policy_row_id)


def _load_drug_list(
    con: sqlite3.Connection,
    data: dict,
    source_filename: str,
    trusted_lookup: dict[str, str],
) -> None:
    cur = con.cursor()

    if "document" in data and isinstance(data["document"], dict):
        doc = data["document"]
        payer = doc.get("payer") or data.get("payer")
        policy_title = doc.get("policy_title")
        effective_date = doc.get("effective_date")
        entries = doc.get("entries") or []
    else:
        payer = data.get("payer")
        policy_title = data.get("policy_title")
        effective_date = data.get("effective_date")
        entries = data.get("entries") or []

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

    local_lookup = dict(trusted_lookup)
    local_lookup.update(_build_mdl_lookup(data))

    for entry in entries:
        hcpcs = _sanitize(entry.get("hcpcs_code"))
        raw_name = _sanitize(entry.get("drug_name"))
        description = _sanitize(entry.get("description"))
        normalized_name, desc_name = _repair_drug_name(hcpcs, raw_name, description, local_lookup)
        generic_name, brand_names = _derive_generic_and_brand(raw_name, normalized_name, desc_name)
        source_page = entry.get("source_page")
        therapeutic_class = _sanitize(entry.get("therapeutic_class"))
        mgmt = _parse_row_management_fields(entry.get("notes"), entry.get("coverage_level"))
        drug_category = therapeutic_class

        cur.execute(
            """
            INSERT INTO drugs (
                policy_id, generic_name, brand_names, hcpcs_code, drug_name,
                drug_name_raw, drug_name_normalized, description,
                coverage_level, notes, covered_alternatives, source_page, therapeutic_class,
                drug_category, access_status_raw, access_status_group,
                prior_auth_required, prior_auth_criteria,
                step_therapy_required, step_therapy_details,
                site_of_care_required, site_of_care_details,
                dosing_limit_summary, covered_diagnoses
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                policy_row_id,
                generic_name,
                _j(brand_names),
                hcpcs,
                normalized_name,
                raw_name,
                normalized_name,
                description,
                _sanitize(entry.get("coverage_level")),
                _sanitize(entry.get("notes")),
                _j(entry.get("covered_alternatives")),
                source_page if isinstance(source_page, int) else None,
                therapeutic_class,
                drug_category,
                mgmt["access_status_raw"],
                mgmt["access_status_group"],
                _bool_to_int(mgmt["prior_auth_required"]),
                mgmt["prior_auth_criteria"],
                _bool_to_int(mgmt["step_therapy_required"]),
                mgmt["step_therapy_details"],
                _bool_to_int(mgmt["site_of_care_required"]),
                mgmt["site_of_care_details"],
                mgmt["dosing_limit_summary"],
                _j(mgmt["covered_diagnoses"]),
            ),
        )

    con.commit()
    _apply_category_access_metrics(con, policy_row_id)
    con.commit()
    logger.info(
        "Loaded drug_list %s into row %d (%d entries)",
        source_filename,
        policy_row_id,
        len(entries),
    )


def normalize(outputs_dir: Path, db_path: Path, reset: bool = False) -> None:
    json_files = sorted(outputs_dir.glob("*.json"))
    if not json_files:
        logger.warning("No JSON files found in %s", outputs_dir)
        return

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")

    if reset:
        logger.info("Dropping existing tables")
        con.execute("DROP VIEW IF EXISTS drugs_unified")
        con.execute("DROP VIEW IF EXISTS drug_access_summary")
        for table in (
            "excluded_indications",
            "dosing_limits",
            "step_therapy",
            "covered_indications",
            "drugs",
            "policies",
        ):
            con.execute(f"DROP TABLE IF EXISTS {table}")
        con.commit()

    con.executescript(DDL)
    con.commit()

    file_data: list[tuple[Path, dict]] = []
    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Skipping %s (invalid JSON): %s", path.name, exc)
            continue
        file_data.append((path, data))

    trusted_lookup = _build_global_code_lookup(file_data)

    file_meta: list[tuple[Path, dict, str, str, int, tuple[int, int, int, str], str]] = []
    for path, data in file_data:
        doc_type = data.get("document_type") or ""
        payer = (_resolve_payer(data) or "").lower().strip()
        count = _entry_count(data)
        file_meta.append((path, data, doc_type, payer, count, _source_rank(path, data), _filename_family(path, data)))

    skip_paths: set[Path] = set()
    for i, (p_i, _, dt_i, pay_i, cnt_i, rank_i, fam_i) in enumerate(file_meta):
        for j, (p_j, _, dt_j, pay_j, cnt_j, rank_j, fam_j) in enumerate(file_meta):
            if i >= j or dt_i != dt_j:
                continue
            payers_overlap = pay_i and pay_j and (pay_i.startswith(pay_j) or pay_j.startswith(pay_i))
            family_overlap = (
                (not pay_i or not pay_j)
                and min(len(fam_i), len(fam_j)) >= 8
                and (fam_i in fam_j or fam_j in fam_i)
            )
            if not payers_overlap and not family_overlap:
                continue
            loser = None
            if rank_i > rank_j:
                loser = p_j
            elif rank_j > rank_i:
                loser = p_i
            else:
                loser = p_i if cnt_i <= cnt_j else p_j
            skip_paths.add(loser)

    for path, data in file_data:
        if path in skip_paths:
            logger.info("Skipping %s because a higher-ranked source was chosen", path.name)
            continue

        logger.info("Processing %s", path.name)
        already = con.execute(
            "SELECT id FROM policies WHERE source_filename = ?",
            (path.name,),
        ).fetchone()
        if already:
            logger.info("Already loaded as policy row %d", already[0])
            continue

        doc_type = data.get("document_type")
        if doc_type == "drug_list":
            _load_drug_list(con, data, path.name, trusted_lookup)
        elif doc_type == "single_drug_policy":
            _load_policy_document(con, data, path.name)
        else:
            logger.warning("Unknown document_type=%r in %s", doc_type, path.name)

    con.close()
    logger.info("Done. Database written to %s", db_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    root = Path(__file__).resolve().parent.parent
    default_outputs = root / "outputs"
    default_db = default_outputs / "policies.db"

    parser = argparse.ArgumentParser(description="Normalize policy JSON outputs to SQLite")
    parser.add_argument("--outputs-dir", type=Path, default=default_outputs)
    parser.add_argument("--db", type=Path, default=default_db)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if not args.outputs_dir.is_dir():
        logger.error("outputs-dir not found: %s", args.outputs_dir)
        sys.exit(1)

    normalize(args.outputs_dir, args.db, reset=args.reset)


if __name__ == "__main__":
    main()
