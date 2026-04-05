from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from extract import _extract_drug_list_page_entries


class PriorityPageExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pdf_path = ROOT / "docs" / "Priority Health 2026 MDL - Priority Health Commercial (Employer Group) and MyPriority.pdf"

    def _page_payload(self, page_number: int) -> tuple[str, list[list[list[str | None]]]]:
        with pdfplumber.open(self.pdf_path) as pdf:
            page = pdf.pages[page_number - 1]
            return (page.extract_text() or ""), (page.extract_tables() or [])

    def test_page_four_rows_do_not_bleed(self) -> None:
        page_text, page_tables = self._page_payload(4)
        entries, section = _extract_drug_list_page_entries(
            4,
            page_text,
            page_tables,
            None,
            "Priority Health Commercial and MyPriority Plans",
        )
        by_code = {}
        for entry in entries:
            by_code.setdefault(entry.hcpcs_code, []).append(entry)

        self.assertEqual(section, "Antidote Therapeutics")
        self.assertEqual([e.drug_name for e in by_code["J0895"]], ["deferoxamine", "DESFERAL"])
        self.assertEqual(by_code["J1610"][0].drug_name, "GLUCAGON EMERGENCY KIT (HUMAN)")
        self.assertEqual(by_code["J0895"][0].source_page, 4)

    def test_page_five_rows_keep_mesna_separate(self) -> None:
        page_text, page_tables = self._page_payload(5)
        entries, section = _extract_drug_list_page_entries(
            5,
            page_text,
            page_tables,
            "Antidote Therapeutics",
            "Priority Health Commercial and MyPriority Plans",
        )
        by_code = {}
        for entry in entries:
            by_code.setdefault(entry.hcpcs_code, []).append(entry)

        self.assertEqual(section, "Chemotherapy Antidotes/Protectants")
        self.assertEqual([e.drug_name for e in by_code["J9209"]], ["mesna intravenous", "MESNEX INTRAVENOUS"])


if __name__ == "__main__":
    unittest.main()
