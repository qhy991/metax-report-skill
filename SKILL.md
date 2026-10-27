---
name: metax-report-skill
description: Profile MetaX (沐曦) GPU kernels with MACA SDK mcTracer and mcProfiler on C550 / MXC550 and C500. Use when the user asks to profile a CUDA-compatible MetaX kernel, analyze mcTracer JSON or mcProfiler CSV, diagnose dram_pct/sm_pct bottlenecks, or write an optimization plan — including Chinese triggers ("profile 一下", "为什么慢", "mcTracer 报告", "沐曦 profiling").
---

# Skill: MetaX GPU Kernel Profiling (C550 / mcTracer + mcProfiler)

**When to use:** user asks to profile a kernel on MetaX (沐曦) hardware, analyze performance, find bottlenecks, or write an optimization plan from mcTracer / mcProfiler evidence. Triggers include: "profile X on MetaX", "为什么这个 kernel 慢", "mcTracer 说...", "HBM 带宽不够", "SM 利用率低", "沐曦 GPU profiling".

**Target hardware (default):** MetaX C550 (MXC550, 64 GB HBM, MACA SDK 3.7.x). For **MetaX C500** read [`reference/10-c500.md`](reference/10-c500.md) first: the device, tool locations and verified facts differ, and C550 numbers do not transfer.

**Runtime note:** GPU compute and profiling usually run inside the MACA Docker container (`--device=/dev/mxcd --group-add video`). Host users without the `video` group often cannot access `/dev/mxcd` even when `mx-smi` works.

---

## Golden rule

**Profile → Diagnose → Plan, in that order. Never guess.**

MetaX kernels are CUDA-source compatible, but **profiling is not NCU-compatible**. Do not run `ncu` or `nsys` on MetaX. Collect mcProfiler CSV (preferred) or mcTracer timeline JSON (fallback), map to canonical `latency_ms` / `dram_pct` / `sm_pct`, then rank fixes by evidence.

---

## Quickstart

0. **Create a new run directory** under `profile/<run_name>/` — one directory per run, never reuse. See [`reference/00-directory-layout.md`](reference/00-directory-layout.md).

1. **Frame the problem.** Kernel name, input shapes, dispatch path (standalone `.cu` / PyTorch / Triton), and the question ("memory-bound?" vs "launch overhead?").

2. **Build or reuse a harness** compiled with `mxcc`. See [`reference/02-harness-guide.md`](reference/02-harness-guide.md) and [`helpers/harness_template.cpp`](helpers/harness_template.cpp).

3. **Collect profiling data** — mcProfiler CSV first; mcTracer JSON if counters are unavailable. Write raw output to `profile/<run_name>/reports/`. See [`reference/03-collection.md`](reference/03-collection.md).

4. **Parse with helpers** — `helpers/analyze_reports.py` or `helpers/parse_mctrace.py`. Write extracts to `profile/<run_name>/analysis/`. See [`reference/04-analysis-guide.md`](reference/04-analysis-guide.md).

5. **Walk the six analysis dimensions.** See [`reference/05-analysis-dimensions.md`](reference/05-analysis-dimensions.md).

6. **Match patterns to the diagnosis playbook.** See [`reference/06-diagnosis-playbook.md`](reference/06-diagnosis-playbook.md).

7. **Write `profile/<run_name>/REPORT.md`** using [`reference/07-report-template.md`](reference/07-report-template.md).

---

## File index

### Reference docs

| File | Purpose |
|---|---|
| [`reference/00-directory-layout.md`](reference/00-directory-layout.md) | Run directory conventions |
| [`reference/01-workflow.md`](reference/01-workflow.md) | End-to-end checklist |
| [`reference/02-harness-guide.md`](reference/02-harness-guide.md) | Standalone harness with mxcc / PyTorch |
| [`reference/03-collection.md`](reference/03-collection.md) | mcTracer + mcProfiler command recipes |
| [`reference/04-analysis-guide.md`](reference/04-analysis-guide.md) | Parse traces, map to canonical metrics |
| [`reference/05-analysis-dimensions.md`](reference/05-analysis-dimensions.md) | Six dimensions for MetaX SIMT GPUs |
| [`reference/06-diagnosis-playbook.md`](reference/06-diagnosis-playbook.md) | Signal → cause → fix |
| [`reference/07-report-template.md`](reference/07-report-template.md) | Final report structure |
| [`reference/08-metax-metric-guide.md`](reference/08-metax-metric-guide.md) | mcProfiler columns, canonical mapping, thresholds |
| [`reference/09-common-issues.md`](reference/09-common-issues.md) | Container, `/dev/mxcd`, `--odname` path traps |
| [`reference/10-c500.md`](reference/10-c500.md) | MetaX C500: verified device facts, tool locations, what is not yet checked |

### Helpers (reusable code)

| File | Purpose |
|---|---|
| [`helpers/metax_utils.py`](helpers/metax_utils.py) | CSV/JSON parsing, column alias tolerance, bottleneck classification |
| [`helpers/analyze_reports.py`](helpers/analyze_reports.py) | Extract key metrics, A/B comparison |
| [`helpers/parse_mctrace.py`](helpers/parse_mctrace.py) | mcTracer JSON timeline → kernel latency table |
| [`helpers/summarize_profile_run.sh`](helpers/summarize_profile_run.sh) | Inventory a run dir and print next steps |
| [`helpers/harness_template.cpp`](helpers/harness_template.cpp) | Minimal mxcc-compilable CUDA harness template |

---

## Critical lessons

1. **Never use NCU on MetaX.** `ncu` and `nsys` are not available. KerSor's `resolve-args.sh` maps `backend=metax` → `mcProfiler`; follow this skill instead of `ncu-report-skill`.

2. **mcTracer `--odname` must be a relative path** when cwd is `/workspace`. Absolute paths like `/tmp/tracer_out` are silently rewritten to broken locations (`/workspace//tmp/...`). See [`reference/09-common-issues.md`](reference/09-common-issues.md).

3. **mcProfiler counter dump may be empty** on some MACA images (API exits 0 but no `tdump.txt`). Treat mcTracer timeline as the reliable first pass; mcProfiler CSV as a bonus when present.

4. **Occupancy is always null on MetaX.** AKW's `_evidence_metax.py` never populates `occupancy` — there is no warp-occupancy counter. Do not diagnose `latency_occupancy` from metrics alone; use launch-config analysis or block-size sweeps.

5. **CUDA source ≠ NVIDIA hardware.** MetaX lacks dedicated tensor cores like Hopper/Blackwell. High `sm_pct` with hand-unrolled SIMT may still underperform vs library GEMM — check [`reference/06-diagnosis-playbook.md`](reference/06-diagnosis-playbook.md) pattern F.

6. **Cite evidence.** Write "`dram_pct` 78%, `sm_pct` 12%, kernel latency 0.41 ms on M=4096" — not "memory bound". Helpers produce the numbers; you interpret them.

7. **One run = one hypothesis.** Baseline and optimized builds get separate `profile/<run_name>/` directories. Use `analyze_reports.py` with two `--report` flags for A/B.

8. **Profile inside the container** when host `/dev/mxcd` permission fails. `torch.cuda.is_available()` may be False on the host even when `mx-smi` lists 7 devices.

---

## CUDA / NCU → MetaX mapping (for migrants)

| CUDA / NCU | MetaX / MACA SDK |
|---|---|
| `nvcc -lineinfo` | `mxcc -x maca -offload-arch native` (or `-march=<target>`) |
| Nsight Compute (`ncu`) | `mcProfiler --csv` (hardware counters, when available) |
| Nsight Systems (`nsys`) | `mcTracer --mctx` (timeline JSON) |
| `nvidia-smi` | `mx-smi` (monitoring; not a profiler) |
| `dram__bytes_read.sum.pct_of_peak` | `dram_pct` / `hbm_bandwidth_pct` (mcProfiler CSV, alias-matched) |
| `sm__throughput.avg.pct_of_peak` | `sm_pct` / `sm_utilization` (mcProfiler CSV) |
| `sm__warps_active` (occupancy) | **not available** — always null |
| `ncu_report` Python API | `helpers/metax_utils.py` + AKW `_evidence_metax.py` |
| `torch.cuda` | `torch.cuda` (MACA registers as CUDA-compatible device) |
| Triton `MacaDriver` | Same `@triton.jit` source; profile via mcTracer on generated binary or PyTorch harness |

---

## Typical workflow with helpers

```bash
export MACA_PATH=/opt/maca
export PATH=${MACA_PATH}/bin:$PATH
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/mxgpu_llvm/lib:$LD_LIBRARY_PATH

export PROFILE_RUN_DIR=profile/my_kernel_baseline
mkdir -p "$PROFILE_RUN_DIR"/{harness,reports,analysis}

# 1. Build harness (see reference/02-harness-guide.md)
# 2. Collect mcTracer (from /workspace, relative --odname)
cd /workspace && mcTracer --mctx --debug --odname tracer_out --name trace \
  "$PROFILE_RUN_DIR/harness/kernel_harness"

# 3. Inventory
./skills/metax-report-skill/helpers/summarize_profile_run.sh "$PROFILE_RUN_DIR"

# 4. Parse timeline
python3 skills/metax-report-skill/helpers/parse_mctrace.py \
  --trace /workspace/tracer_out/trace-*.json \
  --out "$PROFILE_RUN_DIR/analysis/mctrace_summary_baseline.json"

# 5. Key metrics (mcProfiler CSV if you have one)
python3 skills/metax-report-skill/helpers/analyze_reports.py \
  --run-dir "$PROFILE_RUN_DIR" --tag baseline \
  --mcprof "$PROFILE_RUN_DIR/reports/mcprof.csv"
```

---

## Related KerSor integration

This repository is a standalone copy of KerSor's `skills/metax-report-skill/`. The paths below refer to the KerSor tree.

- AKW backend: `_substrate/backends/metax/` (`build.sh`, `profile.sh`, `to_evidence.py`)
- Canonical metric mapper: `_substrate/backends/_evidence_metax.py`
- KerSor config: `profiling_guides` entry for `backend: metax` points at this skill
