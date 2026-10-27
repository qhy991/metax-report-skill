# Six Analysis Dimensions (MetaX)

Walk all six; usually 1–2 dominate. MetaX uses a SIMT programming model similar to CUDA, but **without NCU-style warp-occupancy counters** and **without Hopper-style tensor cores**.

---

## 1 — Launch geometry & grid occupancy

**Question:** Is enough parallel work launched to fill the GPU?

**Signals:**
- Very small grid for problem size (few blocks × few threads)
- Low `sm_pct` despite non-trivial arithmetic
- mcTracer shows many tiny kernels instead of one fused launch

**Read:** block/grid dimensions in harness; kernel count in mcTracer summary.

**Fix direction:** increase block size (256–512 threads typical on MetaX), fuse launches, grid-stride loops for large N.

---

## 2 — Host dispatch & framework overhead

**Question:** Is the GPU idle waiting for the host?

**Signals:**
- mcTracer timeline gaps between kernel bursts
- Wall time ≫ sum of kernel `latency_ms`
- Many small PyTorch ops each < 0.05 ms

**Read:** compare `torch.cuda.Event` wall time vs summed mcTracer kernel durations.

**Fix:** `torch.compile`, CUDA graphs (if supported), kernel fusion, batch larger work per launch.

---

## 3 — DRAM / HBM bandwidth

**Question:** Is memory movement the bottleneck?

**Signals:**
- High `dram_pct` (≥ 70%) with low `sm_pct` (< 50%) from mcProfiler
- Memory-bound arithmetic intensity (low FLOPs/byte)
- Non-coalesced access patterns in source (stride-K loads)

**Fix:** vectorized loads (`float4`/`int4`), shared-memory tiling, reduce redundant global reads, fuse memory-bound ops.

**Wiki / idioms:** AKW `metax/idioms.json` → `vectorized_load_store`, `memory_coalescing`, `shared_memory_tiling`.

---

## 4 — SM / compute utilization

**Question:** Are compute units busy when data is available?

**Signals:**
- High `sm_pct` (≥ 70%) with low `dram_pct`
- Compute-bound kernel (high FLOPs/byte) but still slow → instruction mix or register pressure

**Fix:** register blocking, loop unrolling, reduce divergent branches, avoid spilling to local memory.

**Caveat:** MetaX may lack dedicated tensor cores — hand-unrolled SIMT GEMM can show high `sm_pct` but still lose to library kernels.

---

## 5 — Synchronization & pipeline stalls

**Question:** Are threads stalled on barriers or dependencies?

**Signals:**
- Excessive `__syncthreads()` in tight loops
- Double-buffer pipeline not overlapped (load then compute serially)
- mcTracer shows long gaps between back-to-back kernels that should be fused

**Fix:** double-buffered `__shared__` tiles, reduce sync points, fuse copy+compute phases.

**Note:** Without NCU stall counters, rely on source inspection + mcTracer spacing + A/B after sync reduction.

---

## 6 — Precision, registers & shared memory limits

**Question:** Is on-chip resource pressure limiting occupancy?

**Signals:**
- Register spill warnings from `mxcc`
- Shared memory usage near per-SM limit (~48–64 KB typical)
- Forced small tile sizes → low throughput despite "correct" algorithm

**Fix:** split tiles, reduce live ranges, use narrower dtypes (fp16/bf16), algorithmic reformulation.

**Note:** `occupancy` canonical metric is always null — infer from block-size sweeps and compiler feedback, not from a counter.
