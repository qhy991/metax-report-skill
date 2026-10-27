# Harness Guide — MetaX Kernels

Build a **minimal, reproducible** driver before profiling. The harness pins: kernel source version, mxcc flags, and input shapes.

---

## When a standalone harness is mandatory

- Kernel inside a large framework build where you cannot inject profiler hooks cleanly
- Comparing mxcc-compiled `.so` candidates via AKW substrate `run.sh`
- Fast iteration — harness rebuilds in seconds vs full vLLM / training stack
- mcTracer needs a **runnable binary** with a stable entry point

---

## Option A — Standalone C++/CUDA binary (mcTracer default)

Copy `helpers/harness_template.cpp` to `profile/<run_name>/harness/` and fill in:

- `launch_kernel()` — your `__global__` kernel launch
- `main()` — allocation, warmup loop, timed loop

Build (record exact command in `build_command.sh`):

```bash
export MACA_PATH=/opt/maca
mxcc -x maca -offload-arch native -gcc-version=11 \
  "$PROFILE_RUN_DIR/harness/kernel.cpp" \
  -o "$PROFILE_RUN_DIR/harness/kernel_harness" \
  --maca-path=$MACA_PATH
```

For shared-library substrate workflow (PYBIND11):

```bash
mxcc -shared -fPIC -o "$PROFILE_RUN_DIR/harness/artifact.so" \
  "$PROFILE_RUN_DIR/harness/kernel.cu"
```

---

## Option B — PyTorch harness

```python
import torch, time

def target():
    # your op here
    ...

device = torch.device("cuda")
# warmup
for _ in range(10):
    target()
torch.cuda.synchronize()

start = torch.cuda.Event(enable_timing=True)
end = torch.cuda.Event(enable_timing=True)
start.record()
for _ in range(100):
    target()
end.record()
torch.cuda.synchronize()
print(f"avg_ms={start.elapsed_time(end)/100:.4f}")
```

Profile options:
- Wrap the script with mcProfiler if it supports Python entry points in your MACA version
- Or build a tiny C++ launcher that calls the same CUDA kernels extracted from the project

---

## Option C — Triton on MacaDriver

Triton kernels compile through MACA's Triton backend. For profiling:

1. Run correctness + timing via PyTorch harness first
2. Use mcTracer on a standalone binary if you can AOT-compile the hot kernel
3. Otherwise use timeline + wall-clock from harness; treat as `perf_heuristic` when hardware counters are missing

---

## Warmup rules

- **First run:** JIT compile, driver init — exclude from analysis or run extra warmup iterations
- **Steady state:** 10+ warmup iterations before timed region
- **Synchronize:** `torch.cuda.synchronize()` before stopping host timer

---

## Input shape selection

- Use shapes from the task contract — not arbitrary powers of two
- For variable-length workloads, profile **p50 and p99** separately
- Record dtype (fp32 / fp16 / bf16) in `REPORT.md`

---

## Anti-patterns

- Profiling on host when `/dev/mxcd` is not writable (always fails silently or with init errors)
- Using absolute `--odname` with mcTracer (see `09-common-issues.md`)
- Profiling debug builds (`-g -O0`) then comparing to `-O3` release without documenting
