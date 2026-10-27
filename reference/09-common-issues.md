# Common Issues — MetaX Profiling

## mxcc / mcTracer not found

```bash
export MACA_PATH=${MACA_PATH:-/opt/maca}
export PATH=${MACA_PATH}/bin:$PATH
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/mxgpu_llvm/lib:$LD_LIBRARY_PATH
which mxcc mcTracer mcProfiler
```

Run inside the MACA Docker image if host SDK is incomplete.

---

## `/dev/mxcd` permission denied (host)

Symptoms:
- `torch.cuda.is_available()` → False (but `device_count` may show GPUs)
- `mcMalloc` → `initialization error`
- mcTracer → `getModuleInfo err`, RPC timeout

Fix (admin):
```bash
sudo usermod -aG video <user>
# re-login
```

Workaround: profile inside container with `--device=/dev/mxcd --group-add video`.

---

## mcTracer `--odname` path trap

**Symptom:** empty `tracer_out/` or files under a weird doubled path.

| `--odname` | cwd | Result |
|---|---|---|
| `tracer_out` | `/workspace` | `/workspace/tracer_out/` ✅ |
| `/tmp/out` | `/workspace` | `/workspace//tmp/out/` ❌ |
| `/workspace/out` | `/workspace` | `/workspace//workspace/out/` ❌ |

Always use a **relative** `--odname` and a known cwd (typically `/workspace` in containers).

---

## mcProfiler exits 0 but no counters

Observed on some MACA 3.7.x container images: `profilerScope` API succeeds but `tdump.mem` / `tdump.txt` missing.

**Workaround:** use mcTracer timeline (Recipe 1 in `03-collection.md`); mark report as `profiler_available: false` for hardware counters.

---

## Empty mcProfiler CSV

- Harness crashed before GPU launch — run binary alone first
- Wrong `--target` (script vs binary path)
- Check stderr: `"$PROFILE_RUN_DIR/reports/mcprof.stderr"`

---

## torch.cuda False in container

Usually missing env:
```bash
export MACA_PATH=/opt/maca
export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/mxgpu_llvm/lib:$LD_LIBRARY_PATH
```

Or container started without `--device=/dev/mxcd`.

---

## Do not use NCU / nsys

`ncu` and `nsys` are not part of MACA SDK. KerSor on `backend=metax` resolves `profile_binary=mcProfiler` — follow `metax-report-skill`, not `ncu-report-skill`.

---

## Comparing runs unfairly

- Different MACA SDK / image versions
- Different `mxcc` flags (`-offload-arch native` vs explicit arch)
- Debug vs release builds
- Host vs container without documenting

---

## Triton profiling gaps

Triton JIT kernel names are mangled (`triton_<fn>_<hash>`). mcTracer may not attribute cleanly without a standalone binary. Prefer PyTorch timing harness + mcTracer on extracted hot path, or honest `perf_heuristic` when counters missing.

---

## AKW substrate `metax/profile.sh` mcTracer CLI

Substrate may use simplified `mcTracer --output` flags that differ from container-verified `--mctx --odname`. **Prefer skill Recipe 1** until substrate script is aligned with your MACA version.

---

## Dynamic shapes

Variable shapes may trigger recompilation / autotune. Profile **fixed representative shapes**; document warmup iterations in `REPORT.md`.

---

## When metax profiling is insufficient

- Need instruction-level source correlation like NCU `--set source` → not available; use code review + block-size sweeps
- Need multi-GPU timeline → check MACA multi-device docs / FAE for HCCL-equivalent tools
- Need framework-integrated profiling → sol-execbench timing + mcTracer on isolated harness
