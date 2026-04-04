"""
Claude structured extraction for single-drug policies and consolidated drug lists.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from anthropic import Anthropic
from dotenv import load_dotenv

from schema import DrugListChunkExtraction, DrugListDocument, DrugListEntry, PolicyDocument

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
# Long clinical policies need a large output budget.
MAX_TOKENS_SINGLE = 16384
MAX_TOKENS_DRUG_LIST_CHUNK = 8192
DRUG_LIST_PAGE_CHUNK = 25
LARGE_DOC_PAGES = 50

SYSTEM_SINGLE = (
    "You are a medical policy analyst specializing in medical benefit drug coverage. "
    "Extract all structured data from this policy document. Be thorough — capture every "
    "covered indication, every step therapy requirement, every HCPCS code, every clinical criterion. "
    "Do not summarize or paraphrase the criteria — extract them verbatim."
)

SYSTEM_DRUG_LIST = (
    "You are a medical policy analyst. Parse this drug list into structured entries. "
    "For each drug row, extract the HCPCS/CPT code, drug name, coverage level, site of service "
    "if present, and any notes or covered alternatives. Preserve wording from the document."
)


def _repo_root() -> Path:
    return _SRC.parent


def detect_document_type(first_page_text: str) -> str:
    t = first_page_text.lower()
    if "medical drug list" in t or re.search(r"\bdrug list\b", t):
        return "drug_list"
    return "single_drug_policy"


def _chunk_page_texts(page_texts: list[str], chunk_size: int) -> list[tuple[int, int, str]]:
    """Return list of (start_page_1based, end_page_1based, chunk_body)."""
    chunks: list[tuple[int, int, str]] = []
    n = len(page_texts)
    i = 0
    while i < n:
        j = min(i + chunk_size, n)
        parts = []
        for k in range(i, j):
            parts.append(f"--- Page {k + 1} ---\n{page_texts[k]}")
        chunks.append((i + 1, j, "\n\n".join(parts)))
        i = j
    return chunks


def _split_on_toc_sections(page_texts: list[str]) -> list[tuple[int, int, str]] | None:
    """
    If we detect numbered major sections (e.g. therapeutic class headings), merge into larger chunks.
    Returns None to signal fallback to fixed page chunks.
    """
    # Lines that look like "12. Antineoplastic Agents" or "3. Immunomodulatory"
    heading = re.compile(r"^\s*\d{1,3}\.\s+[A-Z][A-Za-z0-9 ,/&\-]{6,80}\s*$", re.MULTILINE)
    break_pages: list[int] = []
    for idx, pt in enumerate(page_texts):
        if heading.search(pt):
            break_pages.append(idx)
    if len(break_pages) < 3:
        return None
    ranges: list[tuple[int, int, str]] = []
    breaks = sorted(set(break_pages))
    for bi, start_page in enumerate(breaks):
        end_page = (breaks[bi + 1] - 1) if bi + 1 < len(breaks) else (len(page_texts) - 1)
        if end_page < start_page:
            continue
        parts = []
        for k in range(start_page, end_page + 1):
            parts.append(f"--- Page {k + 1} ---\n{page_texts[k]}")
        ranges.append((start_page + 1, end_page + 1, "\n\n".join(parts)))
    return ranges if ranges else None


def extract_single_policy(client: Anthropic, document_text: str) -> PolicyDocument:
    msg = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS_SINGLE,
        system=SYSTEM_SINGLE,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the policy into the required JSON fields. "
                    "Leave unknown fields null or empty arrays. "
                    "Do not include the full document in raw_text; that field may be null.\n\n"
                    f"{document_text}"
                ),
            }
        ],
        output_format=PolicyDocument,
    )
    parsed = msg.parsed_output
    if parsed is None:
        raise RuntimeError("Claude returned no parsed_output for single-drug policy")
    return parsed


def extract_drug_list(
    client: Anthropic,
    ingest_payload: dict[str, Any],
) -> DrugListDocument:
    page_texts: list[str] = ingest_payload.get("page_texts") or []
    tables: list[str] = ingest_payload.get("tables") or []
    filename = ingest_payload.get("filename") or ""

    if len(page_texts) > LARGE_DOC_PAGES:
        toc_chunks = _split_on_toc_sections(page_texts)
        if toc_chunks:
            chunks = toc_chunks
            logger.info("Drug list: using %d TOC-based chunks", len(chunks))
        else:
            flat = _chunk_page_texts(page_texts, DRUG_LIST_PAGE_CHUNK)
            chunks = [(a, b, c) for a, b, c in flat]
            logger.info("Drug list: using %d fixed page chunks", len(chunks))
    else:
        chunks = [(1, len(page_texts), ingest_payload.get("combined") or ingest_payload.get("text") or "")]

    tables_block = ""
    if tables:
        tables_block = "--- Camelot lattice tables (full document) ---\n\n" + "\n\n".join(tables)

    all_entries: list[DrugListEntry] = []
    for start_p, end_p, body in chunks:
        user_parts = [
            f"This is pages {start_p}-{end_p} of a consolidated medical drug list PDF.",
            "Extract every drug row you see in this section into `entries`.",
        ]
        if tables_block and start_p == 1:
            user_parts.append(tables_block)
        user_parts.append(body)
        user_message = "\n\n".join(user_parts)

        msg = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS_DRUG_LIST_CHUNK,
            system=SYSTEM_DRUG_LIST,
            messages=[{"role": "user", "content": user_message}],
            output_format=DrugListChunkExtraction,
        )
        chunk_result = msg.parsed_output
        if chunk_result and chunk_result.entries:
            all_entries.extend(chunk_result.entries)
        else:
            logger.warning("Empty chunk extraction for pages %s-%s", start_p, end_p)

    return DrugListDocument(
        source_filename=filename,
        entries=all_entries,
    )


def run_extraction_on_ingest(ingest_payload: dict[str, Any], client: Anthropic) -> dict[str, Any]:
    """Return a JSON-serializable dict for one ingested document."""
    combined = ingest_payload.get("combined") or ""
    page_texts = ingest_payload.get("page_texts") or []
    first = page_texts[0] if page_texts else (combined[:8000] if combined else "")
    doc_type = detect_document_type(first)

    if doc_type == "drug_list":
        result = extract_drug_list(client, ingest_payload)
        return result.model_dump(mode="json")

    policy = extract_single_policy(client, combined)
    policy.document_type = "single_drug_policy"
    policy.raw_text = combined
    return policy.model_dump(mode="json")


def main() -> None:
    load_dotenv(_repo_root() / ".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Extract structured policy JSON via Claude")
    parser.add_argument(
        "--single",
        metavar="PATH",
        help="Process one PDF (or mislabeled .docx PDF) and write outputs/<stem>.json",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=_repo_root() / "docs",
        help="Directory of PDFs when not using --single",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set (.env or environment).", file=sys.stderr)
        sys.exit(1)

    from ingest import ingest_directory, ingest_pdf

    client = Anthropic(api_key=api_key)
    out_dir = _repo_root() / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.single:
        pattern = args.single
        matches = sorted(glob.glob(pattern, recursive=False)) if any(ch in pattern for ch in "*?[]") else None
        if matches:
            path = Path(matches[0]).expanduser().resolve()
            if len(matches) > 1:
                logger.warning("Multiple matches for %r; using %s", pattern, path)
        else:
            path = Path(pattern).expanduser().resolve()
        if not path.is_file():
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)
        logger.info("Ingesting %s", path.name)
        payload = ingest_pdf(path)
        logger.info("Calling Claude (%s)...", MODEL)
        data = run_extraction_on_ingest(payload, client)
        out_path = out_dir / f"{path.stem}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Wrote %s", out_path)
        print(json.dumps(data, indent=2))
        return

    if not args.docs_dir.is_dir():
        print(f"Docs directory not found: {args.docs_dir}", file=sys.stderr)
        sys.exit(1)

    ingested = ingest_directory(args.docs_dir)
    for fname, payload in ingested.items():
        stem = Path(fname).stem
        logger.info("Extracting %s", fname)
        data = run_extraction_on_ingest(payload, client)
        out_path = out_dir / f"{stem}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Wrote %s", out_path)


if __name__ == "__main__":
    main()
