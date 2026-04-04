"""
Hybrid PDF ingestion: pdfplumber for prose, camelot (lattice) for tables.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

import camelot
import pdfplumber

logger = logging.getLogger(__name__)

# Camelot processes PDFs in page batches to limit memory (esp. 194-page drug lists).
CAMELOT_PAGE_BATCH = 20


def _df_to_markdown_table(df) -> str:
    """Render a DataFrame as a GitHub-flavored markdown table without extra deps."""
    cols = [str(c).replace("|", "\\|") for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        cells = [str(v).replace("|", "\\|").replace("\n", " ") for v in row.tolist()]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _page_batches(num_pages: int, batch_size: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 1
    while start <= num_pages:
        end = min(start + batch_size - 1, num_pages)
        ranges.append((start, end))
        start = end + 1
    return ranges


def _prepare_pdf_path(path: Path) -> tuple[Path, Path | None]:
    """
    Return (path_to_pdf, temp_path_to_delete_or_none).
    EmblemHealth ships a PDF with a .docx extension; copy to a temp .pdf for camelot/pdfplumber.
    """
    path = path.resolve()
    suffix = path.suffix.lower()
    if suffix == ".docx":
        tmp = Path(tempfile.mkstemp(suffix=".pdf", prefix="policy_ingest_")[1])
        shutil.copyfile(path, tmp)
        logger.info("Copied mislabeled .docx (PDF payload) to temporary PDF: %s", tmp)
        return tmp, tmp
    return path, None


def ingest_pdf(path: str | Path) -> dict[str, Any]:
    """
    Extract prose (per page), tables (lattice), and a combined document string.

    Returns:
        filename: basename of original file
        text: full prose
        tables: list of markdown table strings
        combined: prose interleaved with table blocks
        page_texts: list of strings, one per page (for downstream chunking)
    """
    path = Path(path)
    pdf_path, temp_to_cleanup = _prepare_pdf_path(path)
    original_name = path.name

    page_texts: list[str] = []
    markdown_tables: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_texts.append((page.extract_text() or "").strip())

        num_pages = len(page_texts)
        for start, end in _page_batches(num_pages, CAMELOT_PAGE_BATCH):
            pages_arg = f"{start}-{end}"
            try:
                tables = camelot.read_pdf(
                    str(pdf_path),
                    pages=pages_arg,
                    flavor="lattice",
                    suppress_stdout=True,
                )
            except Exception as e:
                logger.debug("Camelot lattice batch %s: %s", pages_arg, e)
                continue
            for ti, table in enumerate(tables):
                try:
                    md = _df_to_markdown_table(table.df)
                    markdown_tables.append(
                        f"<!-- camelot pages {pages_arg} table {ti + 1} (accuracy {table.accuracy:.1f}) -->\n{md}"
                    )
                except Exception as e:
                    logger.debug("Markdown render failed for table on %s: %s", pages_arg, e)
    finally:
        if temp_to_cleanup and temp_to_cleanup.exists():
            try:
                temp_to_cleanup.unlink()
            except OSError:
                pass

    full_text = "\n\n".join(t for t in page_texts if t)

    combined_parts: list[str] = []
    for i, pt in enumerate(page_texts, start=1):
        combined_parts.append(f"--- Page {i} ---\n{pt}")
    if markdown_tables:
        combined_parts.append("--- Extracted tables (lattice) ---\n\n" + "\n\n".join(markdown_tables))

    combined = "\n\n".join(combined_parts)

    return {
        "filename": original_name,
        "text": full_text,
        "tables": markdown_tables,
        "combined": combined,
        "page_texts": page_texts,
    }


def ingest_directory(
    docs_dir: str | Path,
    *,
    patterns: tuple[str, ...] = ("*.pdf", "*.docx"),
) -> dict[str, dict[str, Any]]:
    """Ingest all matching documents under docs_dir. Keys are original filenames."""
    docs_dir = Path(docs_dir)
    out: dict[str, dict[str, Any]] = {}
    seen: set[Path] = set()
    for pat in patterns:
        for p in sorted(docs_dir.glob(pat)):
            if p in seen:
                continue
            seen.add(p)
            logger.info("Ingesting %s", p.name)
            data = ingest_pdf(p)
            out[data["filename"]] = data
    return out


def first_page_text(path: str | Path) -> str:
    """Lightweight first-page text for document-type detection (no camelot)."""
    path = Path(path)
    pdf_path, temp_to_cleanup = _prepare_pdf_path(path)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return ""
            return (pdf.pages[0].extract_text() or "").strip()
    finally:
        if temp_to_cleanup and temp_to_cleanup.exists():
            try:
                temp_to_cleanup.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    import sys

    _here = Path(__file__).resolve().parent
    if str(_here) not in sys.path:
        sys.path.insert(0, str(_here))

    logging.basicConfig(level=logging.INFO)
    root = Path(__file__).resolve().parents[1]
    doc_dir = root / "docs"
    if len(sys.argv) > 1:
        doc_dir = Path(sys.argv[1])
    if not doc_dir.is_dir():
        print(f"No docs directory: {doc_dir}", file=sys.stderr)
        sys.exit(1)
    results = ingest_directory(doc_dir)
    for name, payload in results.items():
        print("=" * 72)
        print(name)
        print("-" * 72)
        print("Prose length:", len(payload["text"]))
        print("Tables:", len(payload["tables"]))
        snippet = payload["combined"][:4000]
        if len(payload["combined"]) > 4000:
            snippet += "\n\n[... truncated ...]"
        print(snippet)
