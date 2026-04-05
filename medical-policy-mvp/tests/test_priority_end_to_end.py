from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from build_master_table import build_master_table
from normalize import normalize


class PriorityEndToEndTests(unittest.TestCase):
    def test_priority_clean_source_is_preferred_and_master_table_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            outputs_dir = tmp_path / "outputs"
            outputs_dir.mkdir()

            for name in (
                "Priority Health 2026 MDL - Priority Health Commercial (Employer Group) and MyPriority.json",
                "priority_health_2026_mdl_extracted.json",
                "Florida Blue MCG Bevecizumab policy.json",
            ):
                shutil.copy2(ROOT / "outputs" / name, outputs_dir / name)

            synthetic = {
                "payer": "Test Payer",
                "document_type": "drug_list",
                "source_filename": "test_category.json",
                "entries": [
                    {
                        "payer": "Test Payer",
                        "hcpcs_code": "J1001",
                        "drug_name": "DRUGA",
                        "description": "Injection, druga, 1 mg",
                        "coverage_level": "Preferred Specialty",
                        "notes": "PA; SOS; ICD-10 codes A12.34-A12.39.",
                        "covered_alternatives": [],
                        "therapeutic_class": "Category A",
                        "source_page": 1,
                    },
                    {
                        "payer": "Test Payer",
                        "hcpcs_code": "J1002",
                        "drug_name": "DRUGB",
                        "description": "Injection, drugb, 1 mg",
                        "coverage_level": "Preferred Specialty",
                        "notes": "PA; ICD-10 codes B10.0.",
                        "covered_alternatives": [],
                        "therapeutic_class": "Category A",
                        "source_page": 1,
                    },
                    {
                        "payer": "Test Payer",
                        "hcpcs_code": "J1003",
                        "drug_name": "DRUGC",
                        "description": "Injection, drugc, 1 mg",
                        "coverage_level": "Non-Preferred",
                        "notes": "PA; Step therapy required after DRUGA.",
                        "covered_alternatives": [],
                        "therapeutic_class": "Category A",
                        "source_page": 1,
                    },
                ],
            }
            (outputs_dir / "test_category.json").write_text(json.dumps(synthetic), encoding="utf-8")

            db_path = outputs_dir / "policies.db"
            normalize(outputs_dir, db_path, reset=True)

            con = sqlite3.connect(db_path)
            policy_files = {
                row[0]
                for row in con.execute("SELECT source_filename FROM policies").fetchall()
            }
            self.assertIn(
                "Priority Health 2026 MDL - Priority Health Commercial (Employer Group) and MyPriority.json",
                policy_files,
            )
            self.assertNotIn("priority_health_2026_mdl_extracted.json", policy_files)

            def names_for(code: str) -> list[tuple[str, str | None]]:
                rows = con.execute(
                    """
                    SELECT drug_name_normalized, drug_name_raw
                    FROM drugs
                    WHERE hcpcs_code = ?
                    ORDER BY drug_name_normalized, COALESCE(drug_name_raw, '')
                    """,
                    (code,),
                ).fetchall()
                return [(row[0], row[1]) for row in rows]

            self.assertIn(("Leuprolide injectable (camcevi etm)", None), names_for("J9003"))
            self.assertIn(("aflibercept-abzv (enzeevu)", None), names_for("Q5149"))
            self.assertIn(("deferoxamine", "deferoxamine"), names_for("J0895"))
            self.assertIn(("DESFERAL", "DESFERAL"), names_for("J0895"))
            self.assertIn(("mesna intravenous", "mesna intravenous"), names_for("J9209"))
            self.assertIn(("MESNEX INTRAVENOUS", "MESNEX INTRAVENOUS"), names_for("J9209"))

            c9257 = names_for("C9257")
            self.assertTrue(any("AVASTIN" in normalized for normalized, _ in c9257))
            self.assertFalse(any(normalized == "VIAL P/F,SUV" for normalized, _ in c9257))

            j9035 = names_for("J9035")
            self.assertTrue(any("AVASTIN" in normalized for normalized, _ in j9035))
            self.assertFalse(any(normalized == "ML VIAL P/F,SUV" for normalized, _ in j9035))

            access_row = con.execute(
                """
                SELECT drug_category, access_status_group, category_access_position,
                       category_total_drugs, category_preferred_drugs,
                       prior_auth_required, covered_diagnoses
                FROM drug_access_summary
                WHERE hcpcs_code = 'J1003' AND drug_name_normalized = 'DRUGC'
                LIMIT 1
                """
            ).fetchone()
            self.assertIsNotNone(access_row)
            self.assertEqual(access_row[0], "Category A")
            self.assertEqual(access_row[1], "non_preferred")
            self.assertEqual(access_row[2], "non-preferred 1 of 1")
            self.assertEqual(access_row[3], 3)
            self.assertEqual(access_row[4], 2)
            self.assertEqual(access_row[5], 1)
            self.assertEqual(access_row[6], "[]")

            con.close()

            md_path = outputs_dir / "priority_master.md"
            build_master_table(db_path, md_path)
            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("Priority Health 2026 MDL - Priority Health Commercial (Employer Group) and MyPriority.json", markdown)
            self.assertIn("J9003", markdown)
            self.assertIn("Leuprolide injectable (camcevi etm)", markdown)
            self.assertIn("Q5149", markdown)
            self.assertIn("aflibercept-abzv (enzeevu)", markdown)
            self.assertIn("category_access_position", markdown)
            self.assertIn("non-preferred 1 of 1", markdown)
            self.assertNotIn("priority_health_2026_mdl_extracted.json", markdown)


if __name__ == "__main__":
    unittest.main()
