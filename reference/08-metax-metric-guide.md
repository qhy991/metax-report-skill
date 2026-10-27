# MetaX Metric Guide (C550 / MACA SDK)

Maps mcProfiler CSV columns and mcTracer output to AKW canonical metrics. Column names **vary by MACA SDK version** — parsers use alias matching, not exact strings.

Target: **MetaX C550 (MXC550)** — 64 GB HBM, SIMT CUDA-compatible ISA via `mxcc`.

---

## Canonical mapping (AKW contract)

| Canonical key | mcProfiler source (alias-matched) | mcTracer | Unit |
|---|---|---|---|
| `latency_ms` | `kernel_time_us`, `duration_us`, … | kernel event `dur` / regex log | ms |
| `dram_pct` | `dram_bandwidth_utilization`, `hbm_bandwidth_pct`, or read+write sum | **null** | 0–100 |
| `sm_pct` | `sm_utilization`, `compute_utilization`, … | **null** | 0–100 |
| `occupancy` | **always null** | **always null** | 0–1 |

Null rule: omitted from `coverage` → `diagnose.py` returns `unknown` for that dimension.

---

## mcProfiler column aliases

Handled by `helpers/metax_utils.py` (same table as AKW `_evidence_metax.py`):

| Concept | Normalised aliases |
|---|---|
| Latency | `kernel_time_us`, `duration_us`, `elapsed_us`, `gpu_time_us`, `kernel_duration`, `time` |
| DRAM combined | `dram_bandwidth_utilization`, `dram_bw_pct`, `global_memory_bandwidth_pct`, `hbm_bandwidth_pct` |
| DRAM read | `dram_read_bw`, `dram_read_pct` |
| DRAM write | `dram_write_bw`, `dram_write_pct` |
| SM / compute | `sm_utilization`, `sm_util_pct`, `compute_utilization`, `compute_util_pct`, `core_utilization`, `alu_utilization` |

If a column reads zero but the header looks related, **print raw CSV headers** and extend aliases — SDK drift is expected.

---

## Thresholds (AKW `diagnose.py` metax profile)

From `_substrate/diagnose.py`:

```python
"metax": dict(occ_lat=0.40, dram_mem=70, sm_mem=50, sm_comp=70, both_low=40)
```

Interpretation:

| Condition | `diagnose.py` class |
|---|---|
| `dram_pct` ≥ 70%, `sm_pct` < 50% | `memory_bound` |
| `sm_pct` ≥ 70%, `dram_pct` < 50% | `compute_bound` |
| both ≥ 40% | `balanced` (lean compute if `sm_pct` > `dram_pct`) |
| both < 40% | `underutilized` / `unknown` |
| `occupancy` | never used (null rule) |

Helpers `classify_bottleneck()` mirrors these rules for quick reports.

---

## Healthy vs unhealthy patterns (rules of thumb)

### Healthy memory-bound GEMM (large, fp16)

- `dram_pct` 60–90%
- `sm_pct` 20–50%
- Single dominant kernel in mcTracer summary

### Healthy compute-bound elementwise

- `sm_pct` 60–90%
- `dram_pct` 10–40%
- High arithmetic intensity in source

### Unhealthy — launch overhead

- mcTracer: many kernels < 0.05 ms each
- `dram_pct` and `sm_pct` both low when mcProfiler works
- Wall time >> sum(kernel latencies)

### Unhealthy — underfilled GPU

- Small grid (e.g. `<<<1, 32>>>` for large N)
- Both metrics < 40%
- Fix: grid-stride loop, larger block size

---

## mcTracer JSON fields

Parser (`parse_mctrace.py`) searches for:

- Chrome trace: `traceEvents[]` with `ph` in (`X`, `i`), `dur` in microseconds, `name` / `cat` for kernel label
- Custom: top-level `kernels[]` or `events[]` with `duration_us`, `elapsed_us`, `name`

Always inspect one raw JSON file when upgrading MACA SDK — extend parser if layout changes.

---

## mx-smi (monitoring only)

`mx-smi` reports device memory, utilization, temperature — useful for sanity checks, **not** a kernel-level profiler.

```bash
mx-smi
# Snapshot into run dir:
mx-smi > "$PROFILE_RUN_DIR/reports/mx-smi_snapshot.txt"
```

Do not substitute `mx-smi` device utilization for `sm_pct` in diagnosis — granularity differs.

---

## Comparison with NVIDIA NCU metrics

| NCU (B200/H100) | MetaX mcProfiler |
|---|---|
| `dram__bytes_read.sum.pct_of_peak_sustained_elapsed` | `dram_pct` (alias-matched) |
| `sm__throughput.avg.pct_of_peak_sustained_elapsed` | `sm_pct` |
| `sm__warps_active.avg.pct_of_peak_sustained_elapsed` | **not available** |
| Per-line `long_scoreboard` stalls | **not available** — use source review |
| PM sampling timeline | mcTracer JSON timeline |

When migrating optimization playbooks from `ncu-report-skill`, drop occupancy and stall-counter sections; keep memory/compute balance logic.
