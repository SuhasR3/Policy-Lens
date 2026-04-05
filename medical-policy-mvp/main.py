#!/usr/bin/env python3
"""
Orchestrate ingest → extract → JSON outputs (Phase 1–4: no SQLite/Chroma yet).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from extract import _active_model, _build_client, run_extraction_on_ingest
from ingest import ingest_directory, ingest_pdf

logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv(_ROOT / ".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Medical policy MVP pipeline (ingest + extract)")
    parser.add_argument("--docs-dir", type=Path, default=_ROOT / "docs")
    parser.add_argument(
        "--only",
        type=Path,
        default=None,
        help="Process a single file instead of the whole docs directory",
    )
    args = parser.parse_args()

    provider = (os.environ.get("LLM_PROVIDER") or "anthropic").lower()
    model = _active_model(provider)

    try:
        client = _build_client(provider)
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)

    logger.info("Using provider=%s model=%s", provider, model)

    out_dir = _ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.only:
        p = args.only.expanduser().resolve()
        if not p.is_file():
            logger.error("File not found: %s", p)
            sys.exit(1)
        payload = ingest_pdf(p)
        data = run_extraction_on_ingest(payload, client, provider, model)
        out_path = out_dir / f"{p.stem}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Wrote %s", out_path)
        print(json.dumps(data, indent=2))
        return

    if not args.docs_dir.is_dir():
        logger.error("Docs directory not found: %s", args.docs_dir)
        sys.exit(1)

    for fname, payload in ingest_directory(args.docs_dir).items():
        stem = Path(fname).stem
        logger.info("Extracting %s", fname)
        data = run_extraction_on_ingest(payload, client, provider, model)
        out_path = out_dir / f"{stem}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Wrote %s", out_path)


if __name__ == "__main__":
    main()
