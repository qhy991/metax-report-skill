"""Shared helpers for parsing MetaX mcProfiler CSV and mcTracer output.

Aligned with AKW _substrate/backends/_evidence_metax.py canonical mapping.

Usage:
    from metax_utils import (
        load_mcprof_csv, parse_mctrace_json, to_canonical,
        classify_bottleneck, HEADLINE_FIELDS,
    )
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

# Column alias table (normalised name -> internal key)
MCPROF_COLUMN_ALIASES = {
    "kernel time us": "latency_us",
    "duration us": "latency_us",
    "elapsed us": "latency_us",
    "gpu time us": "latency_us",
    "kernel duration": "latency_us",
    "time": "latency_us",
    "dram read bw": "dram_read_pct",
    "dram write bw": "dram_write_pct",
    "dram bandwidth utilization": "dram_pct",
    "dram bw pct": "dram_pct",
    "global memory bandwidth pct": "dram_pct",
    "hbm bandwidth pct": "dram_pct",
    "sm utilization": "sm_pct",
    "sm util pct": "sm_pct",
    "compute utilization": "sm_pct",
    "compute util pct": "sm_pct",
    "core utilization": "sm_pct",
    "alu utilization": "sm_pct",
}

MCTRACE_LATENCY_PATTERN = re.compile(
    r"(?:kernel|Kernel)\s+[\"']?(\S+?)[\"']?\s*[:=]\s*([\d.]+)\s*(us|ms|ns|µs)",
    re.IGNORECASE,
)

HEADLINE_FIELDS = ("latency_ms", "dram_pct", "sm_pct", "bottleneck")


def _normalise_name(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip().lower().replace("_", " "))


def _parse_float(raw: Any) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().strip('"').strip("'").replace(",", "")
    if not s or s.lower() in ("n/a", "null", "none", "nan", "-", "--"):
        return None
    m = re.match(r"([\d.eE+-]+)", s)
    if m:
        return float(m.group(1))
    return None


def _read_csv(path: Path) -> list[dict]:
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            with open(path, newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except (UnicodeDecodeError, csv.Error):
            continue
    return []


def load_mcprof_csv(path: str | Path) -> dict[str, float]:
    """Parse first data row of mcProfiler CSV into internal metric dict."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {}

    col_map: dict[str, str] = {}
    for col in reader.fieldnames:
        norm = _normalise_name(col)
        if norm in MCPROF_COLUMN_ALIASES:
            col_map[col] = MCPROF_COLUMN_ALIASES[norm]

    for row in reader:
        result: dict[str, float] = {}
        for col, key in col_map.items():
            val = _parse_float(row.get(col, ""))
            if val is not None:
                result[key] = val
        return result
    return {}


def to_canonical(native: dict[str, float]) -> dict[str, float | None]:
    """Map internal metrics to AKW canonical 4-key dict."""
    canonical: dict[str, float | None] = {
        "latency_ms": None,
        "dram_pct": None,
        "sm_pct": None,
        "occupancy": None,
    }
    if "latency_us" in native:
        canonical["latency_ms"] = native["latency_us"] / 1000.0

    dram = native.get("dram_pct")
    dr = native.get("dram_read_pct")
    dw = native.get("dram_write_pct")
    if dram is not None:
        canonical["dram_pct"] = dram
    elif dr is not None and dw is not None:
        canonical["dram_pct"] = round(dr + dw, 2)
    elif dr is not None:
        canonical["dram_pct"] = dr
    elif dw is not None:
        canonical["dram_pct"] = dw

    canonical["sm_pct"] = native.get("sm_pct")
    return canonical


def classify_bottleneck(metrics: dict[str, float | None]) -> str:
    """Rough bottleneck class aligned with diagnose.py metax thresholds."""
    dram = metrics.get("dram_pct")
    sm = metrics.get("sm_pct")
    if dram is None and sm is None:
        return "unknown"
    dram = dram or 0.0
    sm = sm or 0.0
    if dram >= 70 and sm < 50:
        return "memory_bound"
    if sm >= 70 and dram < 50:
        return "compute_bound"
    if dram >= 40 and sm >= 40:
        return "balanced"
    if dram < 40 and sm < 40:
        return "underutilized"
    if dram > sm:
        return "memory_bound"
    return "compute_bound"


def _dur_to_us(dur: Any, unit: str = "us") -> float | None:
    v = _parse_float(dur)
    if v is None:
        return None
    unit = (unit or "us").lower()
    if unit == "ns":
        return v / 1000.0
    if unit == "ms":
        return v * 1000.0
    return v


def _events_from_json(data: Any) -> list[dict]:
    """Extract normalised events from mcTracer JSON (flexible schema)."""
    events: list[dict] = []

    if isinstance(data, dict):
        if "traceEvents" in data:
            raw = data["traceEvents"]
        elif "events" in data:
            raw = data["events"]
        elif "kernels" in data:
            raw = data["kernels"]
        else:
            raw = []
        if isinstance(raw, list):
            for ev in raw:
                if not isinstance(ev, dict):
                    continue
                name = ev.get("name") or ev.get("kernel") or ev.get("cat") or "unknown"
                dur_us = None
                if "dur" in ev:
                    dur_us = _dur_to_us(ev["dur"], ev.get("unit", "us"))
                elif "duration_us" in ev:
                    dur_us = _parse_float(ev["duration_us"])
                elif "elapsed_us" in ev:
                    dur_us = _parse_float(ev["elapsed_us"])
                elif "latency_us" in ev:
                    dur_us = _parse_float(ev["latency_us"])
                if dur_us is not None and dur_us > 0:
                    events.append({"name": str(name), "duration_us": dur_us})
    elif isinstance(data, list):
        for ev in data:
            if isinstance(ev, dict):
                events.extend(_events_from_json(ev))

    return events


def parse_mctrace_json(path: str | Path) -> list[dict]:
    """Parse mcTracer JSON file into sorted kernel events (longest first)."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace").strip()

    # JSON file
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            events = _events_from_json(data)
            if events:
                events.sort(key=lambda e: e["duration_us"], reverse=True)
                return events
        except json.JSONDecodeError:
            pass

    # Line-oriented log fallback
    events = []
    for line in text.splitlines():
        m = MCTRACE_LATENCY_PATTERN.search(line)
        if m:
            name, val, unit = m.group(1), float(m.group(2)), m.group(3)
            dur_us = _dur_to_us(val, unit)
            if dur_us:
                events.append({"name": name, "duration_us": dur_us})
    events.sort(key=lambda e: e["duration_us"], reverse=True)
    return events


def summarize_trace(events: list[dict], top_n: int = 10) -> dict[str, Any]:
    total_us = sum(e["duration_us"] for e in events)
    top = events[:top_n]
    return {
        "kernel_count": len(events),
        "total_duration_us": total_us,
        "total_duration_ms": total_us / 1000.0,
        "top_kernels": top,
        "latency_ms": (top[0]["duration_us"] / 1000.0) if top else None,
    }
