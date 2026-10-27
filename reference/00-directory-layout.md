# Profile Directory Layout & Naming (MetaX)

**Read this first.** Same discipline as `ncu-report-skill` and `msprof-report-skill`: one run per subdirectory, no cross-contamination.

---

## Top-level rule

All profiling artifacts live under `profile/` at the repo or task root:

```
<repo_root>/
├── profile/
│   ├── <run_1>/
│   └── <run_2>/
├── src/
└── ...
```

Never scatter mcTracer JSON or mcProfiler CSV across `/tmp` without copying into the run directory.

---

## One run = one subdirectory

Every profile attempt — new kernel, new version, new workload shape — gets a **new** `profile/<run_name>/`.

Good names:

```
profile/gemm_v1_baseline/
profile/gemm_v2_tiled/
profile/vecadd_c550_smoke/
profile/triton_matmul_maca_baseline/
```

---

## Standard run layout

```
profile/<run_name>/
├── REPORT.md
├── harness/
│   ├── kernel.cu              # or .cpp — exact source compiled
│   ├── kernel_harness         # mxcc binary
│   └── build_command.sh       # exact mxcc invocation
├── reports/
│   ├── mcprof.csv             # mcProfiler --csv output (optional)
│   ├── mctrace/               # copied from mcTracer --odname dir
│   │   └── trace-<pid>.json
│   └── mx-smi_snapshot.txt    # optional: mx-smi at profile time
└── analysis/
    ├── metrics_key_<tag>.json
    ├── metrics_key_<tag>.txt
    ├── mctrace_summary_<tag>.json
    └── compare_<a>_vs_<b>.txt
```

---

## mcTracer output handling

mcTracer writes under the **current working directory** combined with `--odname`:

| cwd | `--odname` | Actual output |
|---|---|---|
| `/workspace` | `tracer_out` | `/workspace/tracer_out/trace-*.json` ✅ |
| `/workspace` | `/tmp/out` | `/workspace//tmp/out/...` ❌ |

**After collection**, copy trace files into `reports/mctrace/` so the run is self-contained:

```bash
cp -a /workspace/tracer_out "$PROFILE_RUN_DIR/reports/mctrace/"
```

---

## Environment variable convention

```bash
export PROFILE_RUN_DIR=/abs/path/to/profile/my_kernel_baseline
export MACA_PATH=/opt/maca
export PATH=${MACA_PATH}/bin:$PATH
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/mxgpu_llvm/lib:$LD_LIBRARY_PATH
mkdir -p "$PROFILE_RUN_DIR"/{harness,reports,analysis}
```

---

## Checklist before starting

1. `mkdir -p profile/<new_run_name>/{harness,reports,analysis}`
2. Write harness source into `harness/`
3. Compile with `mxcc` — record exact flags in `build_command.sh`
4. Run mcTracer from `/workspace` (or another fixed cwd) with **relative** `--odname`
5. Copy trace JSON into `reports/mctrace/`
6. Run helpers → `analysis/`
7. Write `REPORT.md`
