#!/usr/bin/env python3
"""
Build a deterministic markdown master drug table from the normalized SQLite DB.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def _markdown_table(headers: list[str], rows: list[tuple[object, ...]]) -> str:
    string_rows = [[("" if value is None else str(value)) for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in string_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def fmt_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    lines = [
        fmt_row(headers),
        "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |",
    ]
    lines.extend(fmt_row(row) for row in string_rows)
    return "\n".join(lines)


def build_master_table(db_path: Path, output_path: Path, payer_filter: str | None = None) -> Path:
    con = sqlite3.connect(db_path)
    query = """
        SELECT DISTINCT
            p.payer AS insurance_provider,
            COALESCE(p.policy_title, p.source_filename) AS policy_title,
            p.effective_date,
            COALESCE(d.hcpcs_code, json_extract(d.hcpcs_codes, '$[0]')) AS hcpcs_code,
            COALESCE(d.drug_name_normalized, d.drug_name, d.generic_name) AS drug_name_normalized,
            d.drug_name_raw,
            d.generic_name,
            d.brand_names,
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
            d.source_page,
            p.document_type,
            d.therapeutic_class
        FROM drugs d
        JOIN policies p ON p.id = d.policy_id
        WHERE COALESCE(d.hcpcs_code, json_extract(d.hcpcs_codes, '$[0]')) IS NOT NULL
          AND COALESCE(d.drug_name_normalized, d.drug_name, d.generic_name) IS NOT NULL
    """
    params: list[object] = []
    if payer_filter:
        query += " AND LOWER(p.payer) LIKE LOWER(?)"
        params.append(f"%{payer_filter}%")
    query += """
        ORDER BY
            insurance_provider,
            policy_title,
            effective_date,
            hcpcs_code,
            drug_name_normalized,
            COALESCE(d.drug_name_raw, ''),
            COALESCE(d.source_page, 0),
            COALESCE(d.therapeutic_class, '')
    """
    rows = con.execute(query, params).fetchall()
    con.close()

    headers = [
        "insurance_provider",
        "policy_title",
        "effective_date",
        "hcpcs_code",
        "drug_name_normalized",
        "drug_name_raw",
        "generic_name",
        "brand_names",
        "drug_category",
        "access_status_raw",
        "access_status_group",
        "category_access_position",
        "category_total_drugs",
        "category_preferred_drugs",
        "category_nonpreferred_drugs",
        "covered_diagnoses",
        "prior_auth_required",
        "prior_auth_criteria",
        "step_therapy_required",
        "step_therapy_details",
        "site_of_care_required",
        "site_of_care_details",
        "dosing_limit_summary",
        "source_filename",
        "source_page",
        "document_type",
        "therapeutic_class",
    ]

    markdown = "# Master Drug Table\n\n"
    markdown += f"Rows: {len(rows)}\n\n"
    markdown += _markdown_table(headers, rows)
    output_path.write_text(markdown + "\n", encoding="utf-8")
    logger.info("Wrote %s (%d rows)", output_path, len(rows))
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    root = Path(__file__).resolve().parent
    default_db = root / "outputs" / "policies.db"
    default_output = root / "outputs" / "master_drug_table.md"

    parser = argparse.ArgumentParser(description="Build markdown master drug table from SQLite")
    parser.add_argument("--db", type=Path, default=default_db)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--payer", default=None, help="Optional payer substring filter")
    args = parser.parse_args()

    build_master_table(args.db, args.output, payer_filter=args.payer)


if __name__ == "__main__":
    main()
