"""Run the SentinelOps evaluation harness and print a report.

Usage (from backend/):  ./.venv/Scripts/python.exe ../scripts/evaluate.py

Disables LLM / DB / RAG so the run is fast, free, and deterministic — it measures
the *prediction engine*, not RCA prose.
"""

import os
import sys

# Make the backend package importable regardless of CWD.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

for _k in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "GEMINI_API_KEY",
           "DATABASE_URL", "SUPABASE_URL", "NEO4J_URI"):
    os.environ[_k] = ""
os.environ["AUTO_REMEDIATE"] = "false"

import json  # noqa: E402

from app.eval.harness import evaluate  # noqa: E402

if __name__ == "__main__":
    report = evaluate(max_ticks=60)
    out = os.path.join(os.path.dirname(__file__), "..", "backend", "eval_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "runs"}, indent=2))
    print("\nPer-scenario:")
    for r in report["runs"]:
        lead = f"{r['lead_time_min']:.0f} min early" if r["lead_time_min"] is not None else "n/a"
        print(f"  {r['scenario']:22} detected={r['detected']!s:5} lead={lead}")
