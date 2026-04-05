from __future__ import annotations

import json
from fastapi import APIRouter, Query
from database import get_db

router = APIRouter(prefix="/api/drugs", tags=["drugs"])


def _parse_json_field(val: str | None) -> list | None:
    if not val:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return None


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["covered_diagnoses"] = _parse_json_field(d.get("covered_diagnoses"))
    d["brand_names"] = _parse_json_field(d.get("brand_names"))
    d["hcpcs_codes"] = _parse_json_field(d.get("hcpcs_codes"))
    d["covered_alternatives"] = _parse_json_field(d.get("covered_alternatives"))
    return d


@router.get("/search")
async def search_drugs(q: str = Query(..., min_length=1)):
    """Search drugs by name across all payers. Returns results grouped by payer."""
    async with get_db() as db:
        query = """
            SELECT
                id, policy_id, payer, policy_title, effective_date,
                drug_name, generic_name, brand_names, hcpcs_code,
                access_status_group, drug_category,
                prior_auth_required, step_therapy_required,
                site_of_care_required, dosing_limit_summary,
                covered_diagnoses, coverage_level, notes
            FROM drugs_unified
            WHERE drug_name LIKE ? OR generic_name LIKE ? OR brand_names LIKE ?
            ORDER BY payer, drug_name
            LIMIT 100
        """
        param = f"%{q}%"
        cursor = await db.execute(query, (param, param, param))
        rows = await cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


@router.get("/trending")
async def trending_drugs():
    """Return top drugs by number of payers that list them."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT drug_name, COUNT(DISTINCT payer) as payer_count
            FROM drugs_unified
            WHERE drug_name IS NOT NULL
            GROUP BY drug_name
            ORDER BY payer_count DESC, drug_name
            LIMIT 8
        """)
        rows = await cursor.fetchall()

    return [{"drug_name": row["drug_name"], "payer_count": row["payer_count"]} for row in rows]


@router.get("/{drug_id}")
async def get_drug(drug_id: int):
    """Get full detail for a single drug entry."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT *
            FROM drugs_unified
            WHERE id = ?
            """,
            (drug_id,),
        )
        row = await cursor.fetchone()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Drug not found")

    return _row_to_dict(row)
