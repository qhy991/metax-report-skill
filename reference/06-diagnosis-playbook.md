# Diagnosis Playbook — MetaX

Pattern → signals → first fix. Rank by evidence magnitude. Fix the dominant pattern first.

Cross-reference AKW `metax/idioms.json` for prompt-level guidance.

---

## A — Launch overhead / too many small kernels

**Signals:** mcTracer shows >10 kernels each < 0.1 ms; wall time dominated by gaps; `sm_pct` and `dram_pct` both low.

**First fix:** fuse kernels; enlarge per-launch work; use single kernel with grid-stride loop.

**Deeper:** CUDA graph / compiled PyTorch path; reduce Python dispatch.

---

## B — DRAM / HBM bandwidth bound

**Signals:** `dram_pct` ≥ 70%, `sm_pct` < 50%; memory-bound roofline (low FLOPs/byte).

**First fix:** `float4`/`int4` vectorized loads; ensure consecutive threads hit consecutive addresses.

**Deeper:** `__shared__` tiling + double buffer; reduce redundant global reads; fuse elementwise into GEMM epilogue.

**Idiom:** `vectorized_load_store`, `memory_coalescing`, `shared_memory_tiling`

---

## C — Compute bound (SIMT)

**Signals:** `sm_pct` ≥ 70%, `dram_pct` < 50%; high arithmetic intensity.

**First fix:** register blocking, manual unroll, reduce branch divergence.

**Deeper:** restructure loops for `mxcc` auto-vectorization; tune block size 256–512.

**Idiom:** `register_blocking`, `launch_config_tuning`

---

## D — Underutilized (both metrics low)

**Signals:** `dram_pct` < 40% and `sm_pct` < 40%; kernel finishes quickly but throughput poor.

**First fix:** increase grid size / block count; check if problem size is too small for GPU.

**Deeper:** occupancy tuning via block-size sweep (no occupancy counter — empirical).

**Idiom:** `launch_config_tuning`

---

## E — Shared-memory / sync pipeline stall

**Signals:** source has serial load→sync→compute→sync; timeline shows kernel much longer than memory/compute estimate.

**First fix:** double-buffer `__shared__` tiles; overlap load of tile N+1 with compute on tile N.

**Idiom:** `async_copy_pipeline`, `shared_memory_tiling`

---

## F — Tensor-core assumption mismatch

**Signals:** kernel uses `wmma` / `mma.sync` / CUTLASS tensor-op paths; compile errors or fallback to slow SIMT.

**First fix:** rewrite for SIMT vector math — MetaX lacks NVIDIA-style tensor cores.

**Idiom:** `tensor_core_mma` → marked **N/A** in `metax/idioms.json`

---

## G — Host / device permission or environment

**Signals:** `torch.cuda.is_available()` False; `mcMalloc initialization error`; empty mcTracer output.

**First fix:** run in MACA container with `--device=/dev/mxcd --group-add video`; export `MACA_PATH` and `LD_LIBRARY_PATH`.

**See:** `09-common-issues.md`

---

## H — Profiler unavailable (mcProfiler empty)

**Signals:** mcProfiler exits 0 but CSV empty; no `tdump.txt`.

**First fix:** use mcTracer Recipe 1; diagnose from `latency_ms` + source + block-size sweeps.

**Honest reporting:** mark `profiler_available: false`, `confidence: inferred` in report.

---

## Decision tree (quick)

```
Has mcProfiler CSV with dram_pct/sm_pct?
├─ Yes → classify_bottleneck → playbook B/C/D
└─ No  → parse mcTracer latency
         ├─ many tiny kernels → A
         ├─ one kernel, still slow → source dims 1,3,5,6
         └─ env errors → G
```
