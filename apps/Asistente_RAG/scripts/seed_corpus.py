"""Seed Chroma with PDFs from section 2.4 resources."""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from config.settings import RESOURCES_DIR
from services.ingestion import ingest_pdf_path
from services import chroma_store


def main() -> None:
    pdfs = sorted(RESOURCES_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {RESOURCES_DIR}")
        sys.exit(1)
    print(f"Seeding {len(pdfs)} PDFs from {RESOURCES_DIR}")
    for pdf in pdfs:
        print(f"→ {pdf.name}")
        result = ingest_pdf_path(pdf)
        if result.get("ok"):
            print(f"   ok chunks={result['n_chunks']} doc_id={result['doc_id']}")
        else:
            print(f"   FAIL {result.get('error')}")
    print("Stats:", chroma_store.collection_stats())


if __name__ == "__main__":
    main()
