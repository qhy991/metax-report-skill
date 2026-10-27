#!/usr/bin/env python3
"""Parse mcTracer JSON timeline into a kernel latency summary.

Usage:
    python3 parse_mctrace.py \\
        --trace profile/run/reports/mctrace/trace-12345.json \\
        --out profile/run/analysis/mctrace_summary_baseline.json \\
        --top 20
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from metax_utils import parse_mctrace_json, summarize_trace  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="mcTracer JSON parser")
    ap.add_argument("--trace", required=True, help="path to trace-*.json (glob expanded by shell)")
    ap.add_argument("--out", required=True, help="output JSON path")
    ap.add_argument("--top", type=int, default=10, help="top kernels to keep")
    args = ap.parse_args()

    trace_path = Path(args.trace)
    if not trace_path.is_file():
        print(f"ERROR: trace not found: {trace_path}", file=sys.stderr)
        return 1

    events = parse_mctrace_json(trace_path)
    if not events:
        print(f"WARN: no kernel events parsed from {trace_path}", file=sys.stderr)

    summary = summarize_trace(events, top_n=args.top)
    summary["source_trace"] = str(trace_path.resolve())

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {out} ({summary['kernel_count']} kernels, "
          f"total {summary.get('total_duration_ms', 0):.4f} ms)")

    if summary.get("top_kernels"):
        print("Top kernels:")
        for i, ev in enumerate(summary["top_kernels"][:5]):
            print(f"  {i}: {ev['name']} — {ev['duration_us']:.2f} us")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
