"""Lightweight smoke evaluation for RAG Triad traces (tools + grounded answers).

Full ADK `adk eval` can be run later against eval_config_rag_triad.json.
This script validates the two critical tool paths and prints a trace summary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from agents.runner_service import ask
from tools.nowcast_dfm import run_nowcast_dfm
from tools.retrieve_docs import retrieve_docs


CASES = [
    {
        "id": "retrieve_ceed",
        "q": "¿Qué indica el boletín CEED I trimestre 2026 sobre área causada o licencias?",
        "expect_tools": {"retrieve_docs"},
    },
    {
        "id": "nowcast_dfm",
        "q": "Dame el nowcast DFM de frecuencia AT para 2025-T1 con IC80%.",
        "expect_tools": {"run_nowcast_dfm"},
    },
]


def main() -> None:
    print("=== Tool unit checks ===")
    nc = json.loads(run_nowcast_dfm("2025-T1"))
    assert nc.get("ok"), nc
    print(f"nowcast_dfm ok y_hat={nc['y_hat']} IC80=[{nc['ic80_lo']}, {nc['ic80_hi']}]")

    hits = json.loads(retrieve_docs("CEED construcción área causada trimestre"))
    print(f"retrieve_docs n_hits={hits.get('n_hits')}")

    print("\n=== Agent trace smoke ===")
    results = []
    for case in CASES:
        print(f"→ {case['id']}: {case['q'][:60]}…")
        out = ask(case["q"], session_id=f"eval-{case['id']}")
        tools = set(out.get("tool_calls") or [])
        ok_tools = bool(case["expect_tools"] & tools) or (
            case["id"] == "nowcast_dfm" and out.get("nowcast")
        )
        row = {
            "id": case["id"],
            "tools": list(tools),
            "ok_tools": ok_tools,
            "has_answer": bool(out.get("answer")),
            "n_citations": len(out.get("citations") or []),
            "answer_preview": (out.get("answer") or "")[:200],
        }
        results.append(row)
        print(json.dumps(row, ensure_ascii=False, indent=2))

    out_path = APP_DIR / "eval" / "last_smoke_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {out_path}")
    if not all(r["ok_tools"] and r["has_answer"] for r in results):
        sys.exit(2)


if __name__ == "__main__":
    main()
