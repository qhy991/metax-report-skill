# Final Report Template (MetaX)

Save as `$PROFILE_RUN_DIR/REPORT.md`.

```markdown
# `<kernel_name>` Profiling Report

**Kernel:** `<path / symbol>`
**Target GPU:** MetaX C550 (MXC550) | MetaX C500
**Stack:** mxcc standalone | PyTorch MACA | Triton MacaDriver
**MACA SDK version:** `<mxcc --version / image tag>`
**Profile date:** YYYY-MM-DD
**Run directory:** `profile/<run_name>/`
**Environment:** host | container `<name>`

---

## 0. Profiling setup

- Harness: `profile/<run_name>/harness/...`
- Build command: `<exact mxcc line>`
- Shapes / dtypes: `<e.g. M=4096, N=4096, K=4096, fp16>`
- Collection:
  - mcTracer: `mcTracer --mctx --debug --odname tracer_out --name trace ...`
  - mcProfiler: `mcProfiler --csv --target ...` (or "not available")

### Artifacts

    profile/<run_name>/
    ├── REPORT.md
    ├── harness/
    ├── reports/mctrace/trace-*.json
    ├── reports/mcprof.csv
    └── analysis/

---

## 1. Headline numbers

| Metric | Value | Source | Notes |
|---|---:|---|---|
| Kernel latency (ms) | | mcTracer / mcProfiler | |
| dram_pct | | mcProfiler | null if N/A |
| sm_pct | | mcProfiler | null if N/A |
| occupancy | — | — | not measured on MetaX |
| Bottleneck class | | classify_bottleneck | |

**One-line read:** <dominant bottleneck in plain language>

---

## 2. Per-dimension findings

### 2.1 Launch geometry
### 2.2 Host dispatch
### 2.3 DRAM / HBM
### 2.4 SM compute
### 2.5 Sync / pipeline
### 2.6 Registers / shared memory

---

## 3. Summary diagnosis

| Pattern | Status | Impact |
|---|---|---|
| Launch overhead | | |
| DRAM bandwidth bound | | |
| Compute bound | | |
| Underutilized | | |
| Environment / profiler gap | | |

---

## 4. Optimization directions (ranked)

### Priority 1 — <name>
**Evidence:** ...
**Expected impact:** ...
**Effort:** low / medium / high

### Priority 2 — ...

---

## 5. Confidence & caveats

- Profiler used: mcProfiler | mcTracer-only | timing harness
- Missing counters: occupancy, dram_pct, etc.
- Container vs host notes

---

## 6. Reproduction

    export PROFILE_RUN_DIR=profile/<run_name>
    export MACA_PATH=/opt/maca
    # build + mcTracer + analyze_reports.py
```

## Style rules

- Cite metric values — not generic CUDA tips.
- Never claim NCU results on MetaX.
- Max 3–5 priorities.
- If only mcTracer available, state `confidence: inferred` for bandwidth/compute conclusions.
