# Analysis Guide — MetaX Profiling Output

How to parse mcTracer JSON and mcProfiler CSV and map them to AKW canonical metrics.

---

## Canonical metric contract (KerSor / AKW)

Substrate `diagnose.py` expects up to four keys:

| Key | Unit | MetaX source |
|---|---|---|
| `latency_ms` | milliseconds | mcTracer kernel duration or mcProfiler `kernel_time_us` / 1000 |
| `dram_pct` | 0–100 | mcProfiler DRAM/HBM bandwidth utilization columns |
| `sm_pct` | 0–100 | mcProfiler SM / compute utilization columns |
| `occupancy` | 0–1 | **always null** on MetaX |

Null keys are omitted from `coverage`; `diagnose.py` yields `unknown` for missing dimensions rather than guessing.

---

## mcProfiler CSV

Column names **drift across MACA SDK versions**. `helpers/metax_utils.py` and AKW `_evidence_metax.py` match by normalised alias, not exact header strings.

Common aliases:

| Concept | Example column names |
|---|---|
| Kernel time | `kernel_time_us`, `duration_us`, `elapsed_us`, `gpu_time_us` |
| DRAM / HBM | `dram_bandwidth_utilization`, `hbm_bandwidth_pct`, `dram_bw_pct` |
| DRAM read+write | `dram_read_bw`, `dram_write_bw` (summed when combined column absent) |
| SM compute | `sm_utilization`, `compute_utilization`, `core_utilization`, `alu_utilization` |

Parse:

```bash
python3 helpers/analyze_reports.py \
  --run-dir "$PROFILE_RUN_DIR" --tag baseline \
  --mcprof "$PROFILE_RUN_DIR/reports/mcprof.csv"
```

Outputs `analysis/metrics_key_<tag>.{json,txt}` with canonical mapping and bottleneck classification.

---

## mcTracer JSON timeline

mcTracer writes `trace-<pid>.json` under the `--odname` directory. Structure varies by SDK version; the parser handles:

- Chrome-trace-style event arrays (`traceEvents` with `dur`, `name`, `cat`)
- Flat `events` / `kernels` lists with duration fields
- Line-oriented log files (fallback) via regex kernel latency extraction

Parse:

```bash
python3 helpers/parse_mctrace.py \
  --trace "$PROFILE_RUN_DIR/reports/mctrace/trace-"*.json \
  --out "$PROFILE_RUN_DIR/analysis/mctrace_summary_baseline.json" \
  --top 20
```

**mcTracer-only runs** provide reliable `latency_ms` but usually **not** `dram_pct` / `sm_pct`. State this explicitly in the report and use timing + source analysis for diagnosis.

---

## Bottleneck classification (`classify_bottleneck`)

When mcProfiler CSV is available, helpers apply rough rules aligned with AKW `metax` threshold profile (`diagnose.py`):

| Pattern | Typical signals |
|---|---|
| `memory_bound` | `dram_pct` ≥ 70%, `sm_pct` < 50% |
| `compute_bound` | `sm_pct` ≥ 70%, `dram_pct` < 50% |
| `balanced` | both `dram_pct` and `sm_pct` ≥ 40% |
| `underutilized` | both < 40% — launch overhead, occupancy, or too little work |
| `unknown` | no mcProfiler CSV or missing columns |

---

## A/B comparison

```bash
python3 helpers/analyze_reports.py \
  --run-dir profile/gemm_comparison \
  --mcprof profile/gemm_v1/reports/mcprof.csv --tag v1 \
  --mcprof profile/gemm_v2/reports/mcprof.csv --tag v2
```

Produces `analysis/compare_v1_vs_v2.txt` with side-by-side canonical metrics and latency deltas from mcTracer when provided via `--trace`.

---

## Integration with AKW `to_evidence.py`

For substrate driver workflow:

```bash
python3 _substrate/backends/metax/to_evidence.py \
  --native "$PROFILE_RUN_DIR/reports/mcprof.csv" \
  --format mcprof-csv

python3 _substrate/diagnose.py --metrics metrics.json
```

---

## What to put in analysis/

| Artifact | Tool | Content |
|---|---|---|
| `metrics_key_<tag>.json` | `analyze_reports.py` | Canonical metrics + bottleneck |
| `metrics_key_<tag>.txt` | `analyze_reports.py` | Human-readable summary |
| `mctrace_summary_<tag>.json` | `parse_mctrace.py` | Per-kernel latency ranking |
| `compare_<a>_vs_<b>.txt` | `analyze_reports.py` | A/B table |
