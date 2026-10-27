# mcTracer / mcProfiler Collection Commands

Exact recipes for MetaX C550 with MACA SDK 3.7.x. Run inside the MACA container unless host GPU access is confirmed.

---

## Prerequisites

```bash
export MACA_PATH=${MACA_PATH:-/opt/maca}
export PATH=${MACA_PATH}/bin:$PATH
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/mxgpu_llvm/lib:$LD_LIBRARY_PATH

export PROFILE_RUN_DIR=profile/<run_name>
mkdir -p "$PROFILE_RUN_DIR"/{harness,reports,analysis}
```

---

## Recipe 1 — mcTracer timeline (mandatory first pass)

**Use when:** you need kernel launch timeline, latency, or mcProfiler counters are unavailable.

```bash
# Build target first
mxcc -x maca -offload-arch native -gcc-version=11 \
  "$PROFILE_RUN_DIR/harness/kernel.cpp" \
  -o "$PROFILE_RUN_DIR/harness/kernel_harness" \
  --maca-path=$MACA_PATH

# mcTracer MUST run from a stable cwd; --odname is RELATIVE to cwd
cd /workspace
rm -rf tracer_out && mkdir -p tracer_out

mcTracer --mctx --debug \
  --odname tracer_out \
  --name trace \
  "$PROFILE_RUN_DIR/harness/kernel_harness" [harness args]

# Copy into run dir (do not leave traces only under /workspace)
cp -a tracer_out "$PROFILE_RUN_DIR/reports/mctrace/"
ls -la "$PROFILE_RUN_DIR/reports/mctrace/"
# Expected: trace-<pid>.json
```

| Flag | Purpose |
|---|---|
| `--mctx` | MACA profiling context |
| `--debug` | Verbose diagnostics on failure |
| `--odname <rel>` | Output directory **relative to cwd** |
| `--name trace` | Trace session name prefix |

---

## Recipe 2 — mcProfiler CSV (hardware counters)

**Use when:** `mcProfiler` is on PATH and produces non-empty CSV for your target.

```bash
mcProfiler --csv --target "$PROFILE_RUN_DIR/harness/kernel_harness" \
  > "$PROFILE_RUN_DIR/reports/mcprof.csv" 2>"$PROFILE_RUN_DIR/reports/mcprof.stderr"

# Verify non-empty
wc -l "$PROFILE_RUN_DIR/reports/mcprof.csv"
```

AKW `metax/profile.sh` uses the same invocation. Map CSV → canonical metrics via `helpers/analyze_reports.py` or AKW `_evidence_metax.py`.

---

## Recipe 3 — mcProfiler API (in-process)

For kernels instrumented with MACA `profilerScope` API:

```bash
export MCTX_TARGET_PROFILE_PATH="$PROFILE_RUN_DIR/reports/mcprof_api"
mkdir -p "$MCTX_TARGET_PROFILE_PATH"

./your_instrumented_binary --profile-from-start

# Counter dump location varies by SDK build:
#   tdump.mem / tdump.txt in cwd, or ~/mxlog/umd/
find "$MCTX_TARGET_PROFILE_PATH" . -maxdepth 3 \( -name 'tdump.*' -o -name '*.csv' \) 2>/dev/null
```

On some container images the API returns exit 0 but produces **no counter files** — fall back to Recipe 1.

---

## Recipe 4 — PyTorch op via timing harness + mcTracer on subprocess

When the hot path is Python:

```bash
# 1. Write harness/run_op.py (warmup + timed loop)
# 2. If mcProfiler supports wrapping:
mcProfiler --csv --target "python3 $PROFILE_RUN_DIR/harness/run_op.py" \
  > "$PROFILE_RUN_DIR/reports/mcprof.csv"

# 3. Otherwise: honest latency from torch.cuda.Event in harness;
#    use mcTracer only when you have a native binary entry point
```

---

## Recipe 5 — AKW substrate driver path

When KerSor dispatches with `backend=metax` and `backend_dir=.../metax/`:

```bash
BACKEND_DIR=/path/to/_substrate/backends/metax

"$BACKEND_DIR/build.sh" --source kernel.cu --out artifact.so
"$BACKEND_DIR/profile.sh" \
  --artifact artifact.so \
  --problem problem.json \
  --out prof.native

python3 "$BACKEND_DIR/to_evidence.py" --native prof.native --format mcprof-csv
```

Note: substrate `profile.sh` mcTracer fallback uses simplified CLI — prefer Recipe 1 commands until substrate is updated.

---

## Recipe 6 — A/B comparison

Run Recipe 1 + 2 separately for baseline and candidate — **different** `PROFILE_RUN_DIR`:

```bash
PROFILE_RUN_DIR=profile/gemm_v1_baseline   # ... collect ...
PROFILE_RUN_DIR=profile/gemm_v2_tiled      # ... collect ...
```

Compare with `helpers/analyze_reports.py` (two `--mcprof` or two `--trace` tags).

---

## Post-collection sanity checks

```bash
./skills/metax-report-skill/helpers/summarize_profile_run.sh "$PROFILE_RUN_DIR"
```

---

## Gotchas

- **Empty `reports/mctrace/`:** wrong `--odname`, harness crashed, or cwd not `/workspace`
- **`mcMalloc initialization error` on host:** `/dev/mxcd` permission — use container
- **Do not use `ncu` / `nsys`:** not installed on MetaX; they will not profile MACA kernels
