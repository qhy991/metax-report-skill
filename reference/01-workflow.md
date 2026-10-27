# Profiling Workflow — End-to-End (MetaX)

## Phase 0 — Create run directory

```bash
export PROFILE_RUN_DIR=profile/<descriptive_run_name>
export MACA_PATH=${MACA_PATH:-/opt/maca}
export PATH=${MACA_PATH}/bin:$PATH
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/mxgpu_llvm/lib:$LD_LIBRARY_PATH
mkdir -p "$PROFILE_RUN_DIR"/{harness,reports,analysis}
```

## Phase 0.5 — Frame the problem

1. **What kernel?** `.cu` symbol, Triton `@triton.jit` name, or PyTorch op path.
2. **Which shapes?** Real workload shapes from the task contract.
3. **Which path?** Standalone mxcc binary vs in-process PyTorch/Triton.
4. **What question?** e.g. "Is DRAM bandwidth saturated?" or "Is launch overhead dominating?"
5. **Baseline?** Reference implementation or previous candidate for A/B.

## Phase 1 — Environment check

```bash
# GPU visible (monitoring)
mx-smi

# Compiler + profilers
which mxcc mcTracer mcProfiler

# PyTorch MACA runtime
python3 -c "import torch; print(torch.__version__, 'cuda=', torch.cuda.is_available()); \
  print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no device')"

# Device node (container / permissions)
ls -l /dev/mxcd
```

If `torch.cuda.is_available()` is False but `mx-smi` works, check `/dev/mxcd` permissions or run inside the MACA Docker container with `--device=/dev/mxcd --group-add video`.

## Phase 2 — Harness

- **Standalone C++/CUDA:** adapt `helpers/harness_template.cpp` — compile with `mxcc`
- **PyTorch:** small script that warms up then times `torch.cuda.Event`
- **Triton:** run through PyTorch harness; profile the generated kernel via mcTracer on the process binary or a saved standalone build

See `02-harness-guide.md`.

## Phase 3 — Collection

**Recipe 1 (recommended first):** mcTracer timeline

```bash
cd /workspace
mkdir -p tracer_out
mcTracer --mctx --debug --odname tracer_out --name trace \
  "$PROFILE_RUN_DIR/harness/kernel_harness" [args]
cp -a tracer_out "$PROFILE_RUN_DIR/reports/mctrace/"
```

**Recipe 2 (when counters work):** mcProfiler CSV

```bash
mcProfiler --csv --target "$PROFILE_RUN_DIR/harness/kernel_harness" \
  > "$PROFILE_RUN_DIR/reports/mcprof.csv"
```

See `03-collection.md` for full recipes.

## Phase 4 — Parse and analyze

```bash
SKILL_ROOT=/path/to/kersor/skills/metax-report-skill

"$SKILL_ROOT/helpers/summarize_profile_run.sh" "$PROFILE_RUN_DIR"

python3 "$SKILL_ROOT/helpers/parse_mctrace.py" \
  --trace "$PROFILE_RUN_DIR/reports/mctrace/trace-"*.json \
  --out "$PROFILE_RUN_DIR/analysis/mctrace_summary_baseline.json"

python3 "$SKILL_ROOT/helpers/analyze_reports.py" \
  --run-dir "$PROFILE_RUN_DIR" --tag baseline \
  --mcprof "$PROFILE_RUN_DIR/reports/mcprof.csv"
```

## Phase 5 — Six dimensions

Work through `05-analysis-dimensions.md`. Identify the 1–2 dominant dimensions.

## Phase 6 — Diagnose

Map signals to fixes using `06-diagnosis-playbook.md`.

## Phase 7 — Report

Write `REPORT.md` from `07-report-template.md`.

## Phase 8 (optional) — A/B comparison

```bash
python3 "$SKILL_ROOT/helpers/analyze_reports.py" \
  --run-dir profile/comparison \
  --mcprof profile/baseline/reports/mcprof.csv --tag baseline \
  --mcprof profile/optimized/reports/mcprof.csv --tag optimized
```
