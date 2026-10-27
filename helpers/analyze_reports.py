#!/usr/bin/env python3
"""Extract key metrics from MetaX mcProfiler CSV and/or mcTracer JSON.

Produces in `<run_dir>/analysis/`:
    metrics_key_<tag>.json
    metrics_key_<tag>.txt
    compare_<tag1>_vs_<tag2>.txt  (when >= 2 tags)

Usage:
    python3 analyze_reports.py --run-dir profile/my_kernel --tag baseline \\
        --mcprof profile/my_kernel/reports/mcprof.csv

    python3 analyze_reports.py --run-dir profile/compare \\
        --mcprof profile/v1/reports/mcprof.csv --tag v1 \\
        --mcprof profile/v2/reports/mcprof.csv --tag v2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from metax_utils import (  # noqa: E402
    HEADLINE_FIELDS,
    classify_bottleneck,
    load_mcprof_csv,
    parse_mctrace_json,
    summarize_trace,
    to_canonical,
)


def collect_one(
    tag: str,
    mcprof: Path | None,
    trace: Path | None,
    analysis_dir: Path,
) -> dict:
    summary: dict = {"__tag__": tag}
    native: dict = {}

    if mcprof and mcprof.is_file():
        native = load_mcprof_csv(mcprof)
        summary["__mcprof__"] = str(mcprof)
        if not native:
            print(f"[{tag}] WARN: mcprof CSV empty or unparseable: {mcprof}", file=sys.stderr)

    canonical = to_canonical(native)
    summary["canonical"] = canonical
    summary["bottleneck"] = classify_bottleneck(canonical)

    if trace and trace.is_file():
        events = parse_mctrace_json(trace)
        ts = summarize_trace(events)
        summary["__trace__"] = str(trace)
        summary["mctrace"] = ts
        if canonical["latency_ms"] is None and ts.get("latency_ms") is not None:
            canonical["latency_ms"] = ts["latency_ms"]
            summary["canonical"] = canonical

    coverage = sorted(k for k, v in canonical.items() if v is not None and k != "occupancy")
    summary["coverage"] = coverage

    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / f"metrics_key_{tag}.json").write_text(
        json.dumps(summary, indent=2, default=str)
    )

    txt = analysis_dir / f"metrics_key_{tag}.txt"
    with open(txt, "w") as f:
        f.write(f"===== {tag} =====\n")
        if mcprof:
            f.write(f"mcprof: {mcprof}\n")
        if trace:
            f.write(f"trace: {trace}\n")
        f.write(f"bottleneck: {summary['bottleneck']}\n")
        f.write(f"coverage: {coverage}\n\n")
        f.write("Canonical metrics:\n")
        for k in ("latency_ms", "dram_pct", "sm_pct", "occupancy"):
            f.write(f"  {k}: {canonical.get(k)}\n")
        if summary.get("mctrace"):
            f.write(f"\nmcTracer: {summary['mctrace']['kernel_count']} kernels, "
                    f"total {summary['mctrace']['total_duration_ms']:.4f} ms\n")
            for i, ev in enumerate(summary["mctrace"].get("top_kernels", [])[:5]):
                f.write(f"  top{i}: {ev['name']} = {ev['duration_us']:.2f} us\n")

    print(f"[{tag}] wrote {txt}")
    return summary


def write_compare(summaries: list[dict], analysis_dir: Path) -> None:
    if len(summaries) < 2:
        return
    a, b = summaries[0], summaries[1]
    ta, tb = a["__tag__"], b["__tag__"]
    path = analysis_dir / f"compare_{ta}_vs_{tb}.txt"
    ca = a.get("canonical", {})
    cb = b.get("canonical", {})
    with open(path, "w") as f:
        f.write(f"===== {ta} vs {tb} =====\n\n")
        f.write(f"{'metric':<16} {ta:>14} {tb:>14} {'delta':>14}\n")
        for k in ("latency_ms", "dram_pct", "sm_pct"):
            va, vb = ca.get(k), cb.get(k)
            delta = ""
            if va is not None and vb is not None:
                delta = f"{vb - va:+.4f}"
            f.write(f"{k:<16} {str(va):>14} {str(vb):>14} {delta:>14}\n")
        f.write(f"\nbottleneck: {a.get('bottleneck')} -> {b.get('bottleneck')}\n")
    print(f"Wrote {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="MetaX profile report analyzer")
    ap.add_argument("--run-dir", required=True, help="profile/<run_name> directory")
    ap.add_argument("--tag", action="append", default=[], help="tag per --mcprof/--trace pair")
    ap.add_argument("--mcprof", action="append", default=[], help="mcProfiler CSV path")
    ap.add_argument("--trace", action="append", default=[], help="mcTracer JSON path")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    analysis_dir = run_dir / "analysis"

    mcprofs = [Path(p) for p in args.mcprof]
    traces = [Path(p) for p in args.trace]
    tags = list(args.tag)

    n = max(len(mcprofs), len(traces), 1)
    while len(tags) < n:
        tags.append(f"run{len(tags)}")

    summaries = []
    for i in range(n):
        mc = mcprofs[i] if i < len(mcprofs) else None
        tr = traces[i] if i < len(traces) else None
        if tr is None:
            # Auto-discover trace under run dir
            candidates = sorted((run_dir / "reports" / "mctrace").glob("trace-*.json"))
            if not candidates:
                candidates = sorted(run_dir.glob("reports/mctrace/**/*.json"))
            tr = candidates[0] if candidates and i == 0 else tr
        summaries.append(collect_one(tags[i], mc, tr, analysis_dir))

    write_compare(summaries, analysis_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
