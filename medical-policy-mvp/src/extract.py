"""
Structured extraction for single-drug policies, preferred product programs, and drug lists.

Three extraction paths:
  Prompt A — single_drug_policy   (UHC, Florida Blue, Cigna, EmblemHealth)
  Prompt B — drug_list            (Priority Health 194-page list)
  Prompt C — preferred_product_program (BCBS NC)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from schema import (
    DrugListDocument,
    DrugListEntry,
    PolicyDocument,
)

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OLLAMA_MODEL = "qwen2.5:14b-instruct"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
MAX_TOKENS_POLICY = 16000
MAX_TOKENS_DRUG_LIST_CHUNK = 8192
DEFAULT_POLICY_DIRECT_MAX_CHARS = 12000
DEFAULT_POLICY_CHUNK_MAX_CHARS = 7000
DEFAULT_POLICY_CHUNK_OVERLAP_CHARS = 800
DEFAULT_POLICY_CHUNK_MAX_CALLS = 24

# Priority Health: only extract these two sections for hackathon demo (1-based page numbers)
PRIORITY_HEALTH_SECTIONS: list[tuple[str, int, int]] = [
    ("Antineoplastic Agents", 23, 54),
    ("Immunomodulatory Agents", 149, 178),
]


# ---------------------------------------------------------------------------
# Internal wrapper for drug list chunk parsing
# ---------------------------------------------------------------------------


class _DrugListChunkResult(BaseModel):
    entries: list[DrugListEntry] = []


class _LLMClient:
    """Provider-agnostic LLM transport used by extraction functions."""

    def __init__(
        self,
        provider: str,
        model: str,
        gemini_client: genai.Client | None = None,
        ollama_client: Any | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self._gemini_client = gemini_client
        self._ollama_client = ollama_client

    def generate(self, system: str, user_content: str, max_tokens: int) -> str:
        if self.provider == "gemini":
            if self._gemini_client is None:
                raise RuntimeError("Gemini client is not configured")
            response = self._gemini_client.models.generate_content(
                model=self.model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                    temperature=0,
                ),
            )
            return response.text or ""

        if self.provider == "ollama":
            if self._ollama_client is None:
                raise RuntimeError("Ollama client is not configured")
            response = self._ollama_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_tokens,
                temperature=0,
                response_format={"type": "json_object"},
            )
            if not response.choices:
                return ""
            content = response.choices[0].message.content
            return content if isinstance(content, str) else ""

        raise RuntimeError(f"Unsupported provider: {self.provider}")


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

PROMPT_A_SYSTEM = """\
You extract structured medical-benefit coverage from one policy document.

Requirements:
- Keep indications per product separate; never merge across products.
- Keep step therapy types separate:
  - clinical_step_therapy = different class tried first
  - biosimilar_step_therapy = cheaper same-molecule tried first
- Preserve PA logic in pa_criteria: prefix each item with "ALL:" or "ONE:".
- Extract excluded/unproven/not-covered indications with applies_to_products.
- Extract most recent policy_changes from policy history/revision section.
- For each drug capture access_status and category_position if hierarchy exists.
- Extract approval_duration_initial and approval_duration_renewal separately.
- Extract HCPCS and ICD-10 per relevant drug/indication.
- Capture general_requirements that apply to all drugs/indications.

Use verbatim policy wording for criteria when possible. Do not invent facts.\
"""

PROMPT_B_SYSTEM = """\
Parse a payer medical drug list table into structured rows.

Rules:
- One entry per row.
- Abbreviations: PA=prior auth, SOS=site of service, CC=coverage change, CA=covered alternative.
- If coverage_level contains PA, set pa_required=true.
- If notes contain SOS, set site_of_service=true.
- If notes contain CA alternatives, populate covered_alternatives.
- therapeutic_class is the section header provided by the user message.
- Do not create clinical criteria not present in the table.\
"""

PROMPT_C_SYSTEM = """\
Extract preferred product program data (preferred/unrestricted vs non-preferred/restricted).

For each category:
- list preferred and non-preferred products (brand + generic),
- capture access_status and category_position (e.g., preferred 1 of 2),
- capture non-preferred use criteria,
- capture biosimilar/reference-product mapping,
- capture HCPCS codes,
- create coverage_entries for listed indications with correct access tier.

Do not invent facts.\
"""

POLICY_OUTPUT_CONTRACT = """\
Return exactly one JSON object (no markdown) with these top-level keys:
- payer (str), policy_id (str|null), policy_title (str), document_type (str),
  effective_date (str|null), revision_date (str|null), original_effective_date (str|null),
  general_requirements (list[str]), policy_changes (list[str]),
  drugs (list), coverage_entries (list), excluded_indications (list), raw_text (str|null)

drugs[] item keys:
- generic_name (str), brand_name (str|null), hcpcs_codes (list[str]), is_biosimilar (bool),
  reference_product (str|null), access_status (preferred|non_preferred|restricted|not_covered|excluded|null),
  category_position (str|null), therapeutic_class (str|null)

coverage_entries[] item keys:
- drug_generic_name (str), drug_brand_names (list[str]), hcpcs_codes (list[str]),
  indication (str), applies_to_products (list[str]), is_covered (bool),
  coverage_level (str|null), pa_required (bool), pa_criteria (list[str]),
  clinical_step_therapy (object|null), biosimilar_step_therapy (object|null),
  dosing_limits (str|null), site_of_care_restriction (str|null),
  approval_duration_initial (str|null), approval_duration_renewal (str|null),
  required_regimens (list[str]), icd10_codes (list[str])

clinical_step_therapy keys:
- required_prior_drugs (list[str]), condition (str)

biosimilar_step_therapy keys:
- preferred_products (list[str]), restricted_products (list[str]), condition (str)

excluded_indications[] item keys:
- indication (str), applies_to_products (list[str]), reason (str|null)

Missing scalar values: null. Missing lists: [].
"""

DRUG_LIST_OUTPUT_CONTRACT = """\
Return exactly one JSON object (no markdown):
{
  "entries": [
    {
      "payer": "str",
      "hcpcs_code": "str",
      "drug_name": "str|null",
      "description": "str",
      "coverage_level": "str",
      "pa_required": true|false,
      "site_of_service": true|false,
      "notes": "str|null",
      "covered_alternatives": ["str"],
      "therapeutic_class": "str|null"
    }
  ]
}
Use [] when no rows found.
"""

POLICY_CHUNK_SYSTEM_SUFFIX = """\
You are processing one chunk of a larger policy.
Extract ONLY facts explicitly present in this chunk.
If a field is not present in this chunk, return null (scalar) or [] (list).
Do not infer from missing context.
"""


# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------


def detect_document_type(text: str, num_tables: int) -> str:
    first_pages = text[:3000].lower()
    if "medical drug list" in first_pages or "drug list" in first_pages:
        if num_tables > 50:
            return "drug_list"
    if "preferred" in first_pages and "non-preferred" in first_pages:
        if "unrestricted" in first_pages or "restricted" in first_pages:
            return "preferred_product_program"
    return "single_drug_policy"


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------


def _call_and_parse(
    client: _LLMClient,
    system: str,
    user_content: str,
    max_tokens: int,
) -> dict:
    """
    Call configured LLM, strip markdown fences, extract JSON, return parsed dict.
    Raises ValueError if no valid JSON can be recovered.
    """
    raw = client.generate(system=system, user_content=user_content, max_tokens=max_tokens)

    # Strip markdown fences
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    # Attempt 1: parse the cleaned response
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract from first { to last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response. Raw (first 500 chars):\n{raw[:500]}")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r; using default %d", name, raw, default)
        return default


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        key = v.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _chunk_text_by_pages(page_texts: list[str], max_chars: int) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    current: list[str] = []
    current_chars = 0
    start_page = 0
    end_page = 0

    for idx, page_text in enumerate(page_texts, start=1):
        text = (page_text or "").strip()
        if not text:
            continue
        block = f"--- Page {idx} ---\n{text}"
        block_len = len(block) + 2

        if current and current_chars + block_len > max_chars:
            chunks.append((start_page, end_page, "\n\n".join(current)))
            current = [block]
            current_chars = block_len
            start_page = idx
            end_page = idx
            continue

        if not current:
            start_page = idx
        current.append(block)
        current_chars += block_len
        end_page = idx

    if current:
        chunks.append((start_page, end_page, "\n\n".join(current)))
    return chunks


def _chunk_text_fallback(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    clean = text.strip()
    if not clean:
        return []
    if len(clean) <= max_chars:
        return [clean]

    chunks: list[str] = []
    start = 0
    n = len(clean)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            # Prefer splitting on newline to keep criteria blocks intact.
            split_at = clean.rfind("\n", start + max_chars // 2, end)
            if split_at != -1 and split_at > start:
                end = split_at
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap_chars, start + 1)
    return chunks


def _coverage_key(entry: Any) -> str:
    payload = entry.model_dump(mode="json")
    payload["drug_brand_names"] = sorted(payload.get("drug_brand_names") or [])
    payload["hcpcs_codes"] = sorted(payload.get("hcpcs_codes") or [])
    payload["applies_to_products"] = sorted(payload.get("applies_to_products") or [])
    payload["required_regimens"] = sorted(payload.get("required_regimens") or [])
    payload["icd10_codes"] = sorted(payload.get("icd10_codes") or [])
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _excluded_key(entry: Any) -> str:
    payload = entry.model_dump(mode="json")
    payload["applies_to_products"] = sorted(payload.get("applies_to_products") or [])
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _merge_policy_docs(docs: list[PolicyDocument], document_type: str) -> PolicyDocument:
    merged = PolicyDocument(
        payer="",
        policy_title="",
        document_type=document_type,  # type: ignore[arg-type]
        policy_id=None,
        effective_date=None,
        revision_date=None,
        original_effective_date=None,
        general_requirements=[],
        policy_changes=[],
        drugs=[],
        coverage_entries=[],
        excluded_indications=[],
        raw_text=None,
    )
    if not docs:
        return merged

    drug_index: dict[tuple[str, str], Any] = {}
    coverage_seen: set[str] = set()
    excluded_seen: set[str] = set()

    for doc in docs:
        if not merged.payer and doc.payer:
            merged.payer = doc.payer
        if not merged.policy_title and doc.policy_title:
            merged.policy_title = doc.policy_title
        if not merged.policy_id and doc.policy_id:
            merged.policy_id = doc.policy_id
        if not merged.effective_date and doc.effective_date:
            merged.effective_date = doc.effective_date
        if not merged.revision_date and doc.revision_date:
            merged.revision_date = doc.revision_date
        if not merged.original_effective_date and doc.original_effective_date:
            merged.original_effective_date = doc.original_effective_date

        merged.general_requirements = _dedupe_strings(
            merged.general_requirements + doc.general_requirements
        )
        merged.policy_changes = _dedupe_strings(
            merged.policy_changes + doc.policy_changes
        )

        for drug in doc.drugs:
            key = (
                (drug.generic_name or "").strip().lower(),
                (drug.brand_name or "").strip().lower(),
            )
            existing = drug_index.get(key)
            if existing is None:
                drug_index[key] = drug.model_copy(deep=True)
                continue

            existing.hcpcs_codes = _dedupe_strings(existing.hcpcs_codes + drug.hcpcs_codes)
            existing.is_biosimilar = existing.is_biosimilar or drug.is_biosimilar
            for field in (
                "reference_product",
                "access_status",
                "category_position",
                "therapeutic_class",
            ):
                if getattr(existing, field) in (None, "") and getattr(drug, field) not in (None, ""):
                    setattr(existing, field, getattr(drug, field))

        for entry in doc.coverage_entries:
            key = _coverage_key(entry)
            if key in coverage_seen:
                continue
            coverage_seen.add(key)
            merged.coverage_entries.append(entry.model_copy(deep=True))

        for entry in doc.excluded_indications:
            key = _excluded_key(entry)
            if key in excluded_seen:
                continue
            excluded_seen.add(key)
            merged.excluded_indications.append(entry.model_copy(deep=True))

    merged.drugs = list(drug_index.values())
    return merged


def _extract_policy_doc(
    client: _LLMClient,
    *,
    system_prompt: str,
    user_content: str,
) -> PolicyDocument:
    data = _call_and_parse(
        client,
        system=system_prompt,
        user_content=user_content,
        max_tokens=MAX_TOKENS_POLICY,
    )
    return PolicyDocument.model_validate(data)


def _extract_policy_with_chunking(
    client: _LLMClient,
    *,
    combined_text: str,
    page_texts: list[str],
    base_prompt: str,
    document_type: str,
) -> PolicyDocument:
    direct_max_chars = _env_int("POLICY_DIRECT_MAX_CHARS", DEFAULT_POLICY_DIRECT_MAX_CHARS)
    chunk_max_chars = _env_int("POLICY_CHUNK_MAX_CHARS", DEFAULT_POLICY_CHUNK_MAX_CHARS)
    overlap_chars = _env_int("POLICY_CHUNK_OVERLAP_CHARS", DEFAULT_POLICY_CHUNK_OVERLAP_CHARS)
    max_calls = _env_int("POLICY_CHUNK_MAX_CALLS", DEFAULT_POLICY_CHUNK_MAX_CALLS)

    base_system = (
        base_prompt
        + f"\n\nSet document_type to '{document_type}'.\n"
        + POLICY_OUTPUT_CONTRACT
    )
    if len(combined_text) <= direct_max_chars:
        return _extract_policy_doc(
            client,
            system_prompt=base_system,
            user_content=(
                "Extract all structured data from this medical policy document:\n\n"
                f"{combined_text}"
            ),
        )

    page_chunks = _chunk_text_by_pages(page_texts, chunk_max_chars)
    text_chunks: list[tuple[str, str]] = []
    if page_chunks:
        for start_page, end_page, chunk in page_chunks:
            text_chunks.append((f"pages {start_page}-{end_page}", chunk))
    else:
        fallback_chunks = _chunk_text_fallback(combined_text, chunk_max_chars, overlap_chars)
        for i, chunk in enumerate(fallback_chunks, start=1):
            text_chunks.append((f"chunk {i}", chunk))

    if max_calls > 0 and len(text_chunks) > max_calls:
        logger.warning(
            "Policy chunk count %d exceeds POLICY_CHUNK_MAX_CALLS=%d; truncating",
            len(text_chunks),
            max_calls,
        )
        text_chunks = text_chunks[:max_calls]

    if not text_chunks:
        return _extract_policy_doc(
            client,
            system_prompt=base_system,
            user_content=(
                "Extract all structured data from this medical policy document:\n\n"
                f"{combined_text}"
            ),
        )

    chunk_system = base_system + "\n\n" + POLICY_CHUNK_SYSTEM_SUFFIX
    logger.info("Chunking policy extraction into %d chunk(s)", len(text_chunks))
    partial_docs: list[PolicyDocument] = []
    total_chunks = len(text_chunks)
    for idx, (label, chunk) in enumerate(text_chunks, start=1):
        logger.info("  Chunk %d/%d (%s)", idx, total_chunks, label)
        partial_docs.append(
            _extract_policy_doc(
                client,
                system_prompt=chunk_system,
                user_content=(
                    f"Document chunk {idx}/{total_chunks} ({label}). "
                    "Extract only facts present in this chunk.\n\n"
                    f"{chunk}"
                ),
            )
        )

    merged = _merge_policy_docs(partial_docs, document_type=document_type)
    if not merged.policy_title:
        merged.policy_title = "Unknown Policy Title"
    return merged


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------


def extract_single_drug_policy(
    client: _LLMClient,
    combined_text: str,
    page_texts: list[str],
) -> PolicyDocument:
    """Prompt A: single-drug policy, chunked automatically when large."""
    return _extract_policy_with_chunking(
        client,
        combined_text=combined_text,
        page_texts=page_texts,
        base_prompt=PROMPT_A_SYSTEM,
        document_type="single_drug_policy",
    )


def extract_preferred_program(
    client: _LLMClient,
    combined_text: str,
    page_texts: list[str],
) -> PolicyDocument:
    """Prompt C: preferred product program, chunked automatically when large."""
    return _extract_policy_with_chunking(
        client,
        combined_text=combined_text,
        page_texts=page_texts,
        base_prompt=PROMPT_C_SYSTEM,
        document_type="preferred_product_program",
    )


def _extract_drug_list_chunk(
    client: _LLMClient,
    chunk_text: str,
    payer: str,
    therapeutic_class: str,
) -> list[DrugListEntry]:
    """Prompt B: extract one section of a drug list."""
    system = (
        PROMPT_B_SYSTEM
        + "\n\n"
        + DRUG_LIST_OUTPUT_CONTRACT
    )
    user_content = (
        f"Payer: {payer}\n"
        f"Therapeutic class section: {therapeutic_class}\n\n"
        "Extract every drug row from this section:\n\n"
        f"{chunk_text}"
    )
    data = _call_and_parse(
        client,
        system=system,
        user_content=user_content,
        max_tokens=MAX_TOKENS_DRUG_LIST_CHUNK,
    )
    chunk_result = _DrugListChunkResult.model_validate(data)
    # Back-fill payer and therapeutic_class if the model left them blank
    for entry in chunk_result.entries:
        if not entry.payer:
            entry.payer = payer
        if not entry.therapeutic_class:
            entry.therapeutic_class = therapeutic_class
    return chunk_result.entries


def extract_drug_list(
    client: _LLMClient,
    ingest_payload: dict[str, Any],
) -> DrugListDocument:
    """
    Priority Health drug list: extract only the two sections needed for the
    hackathon demo (Antineoplastic Agents and Immunomodulatory Agents).
    Each section is one API call; results are merged into one DrugListDocument.
    """
    page_texts: list[str] = ingest_payload.get("page_texts") or []
    payer = "Priority Health"
    all_entries: list[DrugListEntry] = []

    for section_name, start_page, end_page in PRIORITY_HEALTH_SECTIONS:
        # Convert 1-based page numbers to 0-based slice indices
        start_idx = start_page - 1
        end_idx = end_page  # exclusive upper bound for slice

        if start_idx >= len(page_texts):
            logger.warning(
                "Section %r: start page %d exceeds document length %d — skipping",
                section_name, start_page, len(page_texts),
            )
            continue

        end_idx = min(end_idx, len(page_texts))
        section_pages = page_texts[start_idx:end_idx]
        chunk_parts = [
            f"--- Page {start_page + i} ---\n{pt}"
            for i, pt in enumerate(section_pages)
            if pt.strip()
        ]
        chunk_text = "\n\n".join(chunk_parts)

        logger.info(
            "Extracting drug list section: %s (pages %d-%d)",
            section_name, start_page, min(end_page, len(page_texts)),
        )
        entries = _extract_drug_list_chunk(client, chunk_text, payer, section_name)
        if entries:
            all_entries.extend(entries)
            logger.info("  → %d entries extracted", len(entries))
        else:
            logger.warning("  No entries extracted for section %r", section_name)

    return DrugListDocument(
        payer=payer,
        policy_title="Priority Health Medical Drug List",
        entries=all_entries,
    )


# ---------------------------------------------------------------------------
# Post-extraction validation
# ---------------------------------------------------------------------------


def validate_extraction(
    result: PolicyDocument | DrugListDocument,
    doc_type: str,
    raw_tables: list[str],
) -> list[str]:
    """Run sanity checks and return a list of warning strings."""
    warnings: list[str] = []

    if doc_type in ("single_drug_policy", "preferred_product_program"):
        assert isinstance(result, PolicyDocument)
        if not any(d.hcpcs_codes for d in result.drugs):
            warnings.append("No HCPCS codes extracted")
        if len(result.coverage_entries) == 0:
            warnings.append("No coverage entries extracted")
        # Detect merged indications — a common LLM error
        products_seen: set[str] = set()
        for entry in result.coverage_entries:
            products_seen.update(entry.applies_to_products)
        if len(products_seen) <= 1 and len(result.drugs) > 1:
            warnings.append(
                "All indications mapped to one product — possible merge error"
            )

    elif doc_type == "drug_list":
        assert isinstance(result, DrugListDocument)
        table_row_count = sum(len(t.split("\n")) for t in raw_tables)
        if table_row_count > 0 and len(result.entries) < table_row_count * 0.5:
            warnings.append(
                f"Only extracted {len(result.entries)} entries "
                f"but tables had ~{table_row_count} rows"
            )

    for w in warnings:
        logger.warning("⚠️  %s", w)
    return warnings


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------


def run_extraction_on_ingest(
    ingest_payload: dict[str, Any],
    client: _LLMClient,
) -> tuple[dict[str, Any], list[str]]:
    """
    Route to the correct extractor, run validation, return (json_dict, warnings).
    raw_text is attached to PolicyDocument results for downstream RAG use.
    """
    combined: str = ingest_payload.get("combined") or ""
    raw_tables: list[str] = ingest_payload.get("tables") or []
    page_texts: list[str] = ingest_payload.get("page_texts") or []
    first_text = page_texts[0] if page_texts else combined[:3000]

    doc_type = detect_document_type(first_text + "\n" + combined[:1000], len(raw_tables))
    logger.info("Detected document type: %s", doc_type)

    if doc_type == "drug_list":
        result = extract_drug_list(client, ingest_payload)
        warnings = validate_extraction(result, doc_type, raw_tables)
        return result.model_dump(mode="json"), warnings

    if doc_type == "preferred_product_program":
        result = extract_preferred_program(client, combined, page_texts)
        result.document_type = "preferred_product_program"
        result.raw_text = combined
        warnings = validate_extraction(result, doc_type, raw_tables)
        return result.model_dump(mode="json"), warnings

    # default: single_drug_policy
    result = extract_single_drug_policy(client, combined, page_texts)
    result.document_type = "single_drug_policy"
    result.raw_text = combined
    warnings = validate_extraction(result, doc_type, raw_tables)
    return result.model_dump(mode="json"), warnings


# ---------------------------------------------------------------------------
# Pretty-print summary
# ---------------------------------------------------------------------------


def _print_summary(data: dict[str, Any], warnings: list[str]) -> None:
    doc_type = data.get("document_type", "unknown")
    print(f"  Payer:               {data.get('payer', 'unknown')}")
    print(f"  Document type:       {doc_type}")

    if doc_type == "drug_list":
        print(f"  Entries found:       {len(data.get('entries', []))}")
    else:
        drugs = data.get("drugs", [])
        entries = data.get("coverage_entries", [])
        step_clinical = sum(1 for e in entries if e.get("clinical_step_therapy"))
        step_biosimilar = sum(1 for e in entries if e.get("biosimilar_step_therapy"))
        hcpcs_all: set[str] = set()
        for d in drugs:
            hcpcs_all.update(d.get("hcpcs_codes", []))
        print(f"  Drugs found:         {len(drugs)}")
        print(f"  Coverage entries:    {len(entries)}")
        print(
            f"  Step therapy rules:  {step_clinical + step_biosimilar} "
            f"({step_clinical} clinical, {step_biosimilar} biosimilar)"
        )
        print(f"  HCPCS codes:         {len(hcpcs_all)}")
        print(f"  Excluded indications:{len(data.get('excluded_indications', []))}")
        print(f"  Policy changes:      {len(data.get('policy_changes', []))}")

    print(f"  Warnings:            {len(warnings)}")
    for w in warnings:
        print(f"    ⚠️  {w}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return _SRC.parent


def _build_llm_client_from_env() -> _LLMClient:
    provider = (os.environ.get("MODEL_PROVIDER") or "gemini").strip().lower()

    if provider == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set (.env or environment).")
        model = (os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
        return _LLMClient(
            provider="gemini",
            model=model,
            gemini_client=genai.Client(api_key=api_key),
        )

    if provider == "ollama":
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ValueError(
                "MODEL_PROVIDER=ollama requires the openai package. "
                "Install it with: ../.venv/bin/pip install openai"
            ) from exc

        base_url = (os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).strip()
        model = (os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip()
        api_key = (os.environ.get("OLLAMA_API_KEY") or "ollama").strip()
        return _LLMClient(
            provider="ollama",
            model=model,
            ollama_client=OpenAI(base_url=base_url, api_key=api_key),
        )

    raise ValueError(
        f"Unsupported MODEL_PROVIDER={provider!r}. Use 'gemini' or 'ollama'."
    )


def main() -> None:
    load_dotenv(_repo_root() / ".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="Extract structured policy JSON via Gemini or Ollama"
    )
    parser.add_argument(
        "--single",
        metavar="PATH",
        help="Process one PDF (or mislabeled .docx PDF) and write outputs/<stem>.json",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all PDFs/DOCXs in --docs-dir",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=_repo_root() / "docs",
        help="Directory of documents when using --all (default: docs/)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print extraction summary instead of raw JSON",
    )
    args = parser.parse_args()

    if not args.single and not args.all:
        parser.print_help()
        sys.exit(0)

    try:
        client = _build_llm_client_from_env()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    from ingest import ingest_directory, ingest_pdf

    out_dir = _repo_root() / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.single:
        import glob as _glob

        pattern = args.single
        if any(ch in pattern for ch in "*?[]"):
            matches = sorted(_glob.glob(pattern, recursive=False))
            if not matches:
                print(f"No files matched: {pattern}", file=sys.stderr)
                sys.exit(1)
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
        logger.info("Calling %s (%s)...", client.provider, client.model)
        data, warnings = run_extraction_on_ingest(payload, client)

        out_path = out_dir / f"{path.stem}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Wrote %s", out_path)

        if args.pretty:
            print(f"\n--- {path.name} ---")
            _print_summary(data, warnings)
            print()
        else:
            print(json.dumps(data, indent=2))
        return

    # --all
    if not args.docs_dir.is_dir():
        print(f"Docs directory not found: {args.docs_dir}", file=sys.stderr)
        sys.exit(1)

    ingested = ingest_directory(args.docs_dir)
    for fname, payload in ingested.items():
        stem = Path(fname).stem
        logger.info("Extracting %s", fname)
        data, warnings = run_extraction_on_ingest(payload, client)

        out_path = out_dir / f"{stem}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Wrote %s", out_path)

        if args.pretty:
            print(f"\n--- {fname} ---")
            _print_summary(data, warnings)
            print()


if __name__ == "__main__":
    main()
