from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from normalize import (
    _categorize_access_status,
    _drug_name_from_description,
    _looks_contaminated,
    _parse_row_management_fields,
    _repair_drug_name,
)


class NormalizeHelperTests(unittest.TestCase):
    def test_looks_contaminated_flags_known_bad_names(self) -> None:
        self.assertTrue(_looks_contaminated("DESFERAL GLUCAGON"))
        self.assertTrue(_looks_contaminated("mesna intravenous MESNEX"))
        self.assertTrue(_looks_contaminated("VIAL P/F,SUV"))
        self.assertTrue(_looks_contaminated("Commercial and MyPriority Drugs"))
        self.assertFalse(_looks_contaminated("DESFERAL"))
        self.assertFalse(_looks_contaminated("aflibercept-abzv (enzeevu)"))

    def test_drug_name_from_description(self) -> None:
        self.assertEqual(
            _drug_name_from_description("Injection, aflibercept-abzv (enzeevu), biosimilar, 1 mg"),
            "aflibercept-abzv (enzeevu)",
        )
        self.assertEqual(
            _drug_name_from_description("Injection, glucagon hydrochloride, per 1 mg"),
            "glucagon hydrochloride",
        )
        self.assertEqual(
            _drug_name_from_description("Leuprolide injectable (camcevi etm), 1 mg"),
            "Leuprolide injectable (camcevi etm)",
        )

    def test_repair_prefers_lookup_then_description(self) -> None:
        repaired, desc_name = _repair_drug_name(
            "J9003",
            "N/A",
            "Leuprolide injectable (camcevi etm), 1 mg Injection, aflibercept-abzv",
            {"J9003": "Leuprolide injectable (camcevi etm)"},
        )
        self.assertEqual(repaired, "Leuprolide injectable (camcevi etm)")
        self.assertEqual(desc_name, "Leuprolide injectable (camcevi etm)")

        repaired, desc_name = _repair_drug_name(
            "Q5149",
            None,
            "Injection, aflibercept-abzv (enzeevu), biosimilar, 1 mg",
            {},
        )
        self.assertEqual(repaired, "aflibercept-abzv (enzeevu)")
        self.assertEqual(desc_name, "aflibercept-abzv (enzeevu)")

    def test_access_status_and_management_fields(self) -> None:
        self.assertEqual(_categorize_access_status("Preferred Specialty"), "preferred")
        self.assertEqual(_categorize_access_status("Non-Preferred"), "non_preferred")
        self.assertEqual(_categorize_access_status("Not Covered"), "not_covered")

        parsed = _parse_row_management_fields(
            "PA; SOS; No PA required for ICD-10 codes D56.0-D56.9.",
            "Preferred Specialty",
        )
        self.assertTrue(parsed["prior_auth_required"])
        self.assertTrue(parsed["site_of_care_required"])
        self.assertEqual(parsed["access_status_group"], "preferred")
        self.assertIn("D56.0-D56.9", parsed["covered_diagnoses"])


if __name__ == "__main__":
    unittest.main()
