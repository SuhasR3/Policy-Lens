"""
Structured extraction for single-drug policies and consolidated drug lists.
Supports Anthropic (Claude) and OpenRouter as LLM providers, controlled via LLM_PROVIDER in .env.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI

from schema import DrugListChunkExtraction, DrugListDocument, DrugListEntry, PolicyDocument

logger = logging.getLogger(__name__)

ANTHROPIC_MODEL = "claude-sonnet-4-6"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# OPENROUTER_DEFAULT_MODEL = "openrouter/free"
OPENROUTER_DEFAULT_MODEL = "qwen/qwen3.6-plus:free"

# Long clinical policies need a large output budget.
MAX_TOKENS_SINGLE = 16384
MAX_TOKENS_SINGLE_OPENROUTER = 4096   # free models cap well below 16k
MAX_TOKENS_DRUG_LIST_CHUNK = 8192
MAX_TOKENS_DRUG_LIST_CHUNK_OPENROUTER = 4096
# OpenRouter: step-3.5-flash:free has a 256k token context window (~1M chars).
# Truncate conservatively to leave headroom for output tokens.
OPENROUTER_MAX_DOC_CHARS = 800_000
DRUG_LIST_PAGE_CHUNK = 5    # ~1.5-2k input tokens each; safe within 10k token/min free tier
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


def _build_client(provider: str) -> Anthropic | OpenAI:
    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set in environment")
        return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in environment")
    return Anthropic(api_key=api_key)


def _active_model(provider: str) -> str:
    if provider == "openrouter":
        return os.environ.get("OPENROUTER_MODEL") or OPENROUTER_DEFAULT_MODEL
    return ANTHROPIC_MODEL


def _anthropic_tool_call(
    client: Anthropic,
    model: str,
    system: str,
    user_message: str,
    max_tokens: int,
    output_type: type,
):
    """
    Use Anthropic tool-calling to get structured output.

    client.messages.parse uses constrained grammar decoding which rejects complex
    nested schemas. Tool-calling has no such limitation and returns well-formed JSON
    that we validate with Pydantic ourselves.

    Retries on 429 rate-limit errors, honouring the retry-after header when present.
    """
    import anthropic as _anthropic

    tool_name = output_type.__name__
    tool_schema = output_type.model_json_schema()
    tool_schema = _inline_refs(tool_schema)

    max_attempts = 8
    base_wait = 60.0

    for attempt in range(max_attempts):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                tools=[
                    {
                        "name": tool_name,
                        "description": f"Structured extraction result matching {tool_name}",
                        "input_schema": tool_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[{"role": "user", "content": user_message}],
            )
            break
        except _anthropic.RateLimitError as exc:
            if attempt == max_attempts - 1:
                raise
            # Try to read retry-after from the response headers
            wait = base_wait * (2 ** attempt)
            try:
                retry_after = float(exc.response.headers.get("retry-after", wait))
                wait = max(wait, retry_after)
            except Exception:
                pass
            logger.warning(
                "Rate limited (attempt %d/%d). Waiting %.0fs before retry...",
                attempt + 1, max_attempts, wait,
            )
            time.sleep(wait)

    for block in resp.content:
        if block.type == "tool_use" and block.name == tool_name:
            return output_type.model_validate(block.input)
    raise RuntimeError(f"No tool_use block returned for {tool_name}")


def _inline_refs(schema: dict) -> dict:
    """
    Inline all $ref entries from $defs so the schema has no references.
    Anthropic's tool API does not support JSON Schema $ref.
    """
    import copy
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})

    def _resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_name = obj["$ref"].split("/")[-1]
                resolved = copy.deepcopy(defs.get(ref_name, {}))
                obj.clear()
                obj.update(_resolve(resolved))
            else:
                for k, v in obj.items():
                    obj[k] = _resolve(v)
        elif isinstance(obj, list):
            return [_resolve(item) for item in obj]
        return obj

    _resolve(schema)
    return schema


def _openrouter_tool_call(
    client: OpenAI,
    model: str,
    system: str,
    user_message: str,
    max_tokens: int,
    output_type: type,
):
    """
    Get structured output from an OpenRouter model via JSON prompt.

    Free OpenRouter models don't reliably follow tool_choice directives.
    Instead we ask the model to return a raw JSON object matching the schema,
    then validate with Pydantic. We strip markdown fences if present.
    """
    schema = output_type.model_json_schema()
    schema = _inline_refs(schema)
    schema_str = json.dumps(schema, indent=2)

    json_prompt = (
        f"{user_message}\n\n"
        "Return ONLY a valid JSON object matching this schema (no markdown, no explanation):\n"
        f"{schema_str}"
    )

    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json_prompt},
        ],
    )
    raw = resp.choices[0].message.content or ""
    # Strip markdown code fences if the model wrapped the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw.strip())
    raw = raw.strip()
    if not raw:
        logger.warning("OpenRouter model returned empty content — returning empty result.")
        return output_type()
    try:
        return output_type.model_validate_json(raw)
    except Exception as exc:
        logger.warning("Failed to parse OpenRouter JSON response (%s) — returning empty result.", exc)
        return output_type()


def _call_structured(
    client: Anthropic | OpenAI,
    provider: str,
    model: str,
    system: str,
    user_message: str,
    max_tokens: int,
    output_type: type,
):
    """Call the model and return a parsed Pydantic instance regardless of provider."""
    if provider == "openrouter":
        assert isinstance(client, OpenAI)
        return _openrouter_tool_call(client, model, system, user_message, max_tokens, output_type)
    else:
        assert isinstance(client, Anthropic)
        return _anthropic_tool_call(client, model, system, user_message, max_tokens, output_type)


def extract_single_policy(
    client: Anthropic | OpenAI,
    provider: str,
    model: str,
    document_text: str,
) -> PolicyDocument:
    max_tokens = MAX_TOKENS_SINGLE_OPENROUTER if provider == "openrouter" else MAX_TOKENS_SINGLE
    if provider == "openrouter" and len(document_text) > OPENROUTER_MAX_DOC_CHARS:
        logger.warning(
            "Document is %d chars; truncating to %d for OpenRouter free model.",
            len(document_text),
            OPENROUTER_MAX_DOC_CHARS,
        )
        document_text = document_text[:OPENROUTER_MAX_DOC_CHARS]
    user_message = (
        "Extract the policy into the required JSON fields. "
        "Leave unknown fields null or empty arrays. "
        "Do not include the full document in raw_text; that field may be null.\n\n"
        f"{document_text}"
    )
    parsed = _call_structured(client, provider, model, SYSTEM_SINGLE, user_message, max_tokens, PolicyDocument)
    if parsed is None:
        raise RuntimeError("Model returned no parsed output for single-drug policy")
    return parsed


def extract_drug_list(
    client: Anthropic | OpenAI,
    provider: str,
    model: str,
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
    for i, (start_p, end_p, body) in enumerate(chunks):
        user_parts = [
            f"This is pages {start_p}-{end_p} of a consolidated medical drug list PDF.",
            "Extract every drug row you see in this section into `entries`.",
        ]
        if tables_block and start_p == 1:
            user_parts.append(tables_block)
        user_parts.append(body)
        user_message = "\n\n".join(user_parts)

        chunk_result = _call_structured(
            client, provider, model, SYSTEM_DRUG_LIST, user_message,
            MAX_TOKENS_DRUG_LIST_CHUNK_OPENROUTER if provider == "openrouter" else MAX_TOKENS_DRUG_LIST_CHUNK,
            DrugListChunkExtraction,
        )
        if chunk_result and chunk_result.entries:
            all_entries.extend(chunk_result.entries)
            logger.info("Chunk %d/%d: extracted %d entries (total so far: %d)", i + 1, len(chunks), len(chunk_result.entries), len(all_entries))
        else:
            logger.warning("Empty chunk extraction for pages %s-%s", start_p, end_p)

    return DrugListDocument(
        source_filename=filename,
        entries=all_entries,
    )


def run_extraction_on_ingest(
    ingest_payload: dict[str, Any],
    client: Anthropic | OpenAI,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Return a JSON-serializable dict for one ingested document."""
    combined = ingest_payload.get("combined") or ""
    page_texts = ingest_payload.get("page_texts") or []
    first = page_texts[0] if page_texts else (combined[:8000] if combined else "")
    doc_type = detect_document_type(first)

    if doc_type == "drug_list":
        result = extract_drug_list(client, provider, model, ingest_payload)
        return result.model_dump(mode="json")

    policy = extract_single_policy(client, provider, model, combined)
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
        "--output",
        metavar="FILENAME",
        default=None,
        help="Custom output filename (relative to outputs/ or absolute path). Overrides default <stem>.json when using --single.",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=_repo_root() / "docs",
        help="Directory of PDFs when not using --single",
    )
    args = parser.parse_args()

    provider = (os.environ.get("LLM_PROVIDER") or "anthropic").lower()
    model = _active_model(provider)

    try:
        client = _build_client(provider)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    logger.info("Using provider=%s model=%s", provider, model)

    from ingest import ingest_directory, ingest_pdf
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
        logger.info("Calling %s (%s)...", provider, model)
        data = run_extraction_on_ingest(payload, client, provider, model)
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
        data = run_extraction_on_ingest(payload, client, provider, model)
        out_path = out_dir / f"{stem}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Wrote %s", out_path)


if __name__ == "__main__":
    main()
