// Minimal MetaX / MACA harness template for mcTracer profiling.
// Copy to profile/<run_name>/harness/kernel.cpp and customize launch_kernel().
//
// Build:
//   export MACA_PATH=/opt/maca
//   mxcc -x maca -offload-arch native -gcc-version=11 \
//     kernel.cpp -o kernel_harness --maca-path=$MACA_PATH
//
// Profile (from /workspace, relative --odname):
//   mcTracer --mctx --debug --odname tracer_out --name trace /path/to/kernel_harness

#include <cstdio>
#include <cstdlib>
#include <vector>

// MACA provides CUDA-compatible runtime headers when MACA_PATH is set.
#include <mcr/mc_runtime.h>

#define CHECK(call)                                                          \
  do {                                                                       \
    mcError_t err = (call);                                                \
    if (err != mcSuccess) {                                                \
      fprintf(stderr, "MACA error %s:%d %s\n", __FILE__, __LINE__, mcGetErrorString(err)); \
      std::exit(1);                                                          \
    }                                                                        \
  } while (0)

__global__ void vector_add(const float* a, const float* b, float* c, int n) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) {
    c[i] = a[i] + b[i];
  }
}

static void launch_kernel(int n, int reps) {
  std::vector<float> ha(n, 1.0f), hb(n, 2.0f);
  float *da = nullptr, *db = nullptr, *dc = nullptr;
  size_t bytes = static_cast<size_t>(n) * sizeof(float);

  CHECK(mcMalloc(&da, bytes));
  CHECK(mcMalloc(&db, bytes));
  CHECK(mcMalloc(&dc, bytes));
  CHECK(mcMemcpy(da, ha.data(), bytes, mcMemcpyHostToDevice));
  CHECK(mcMemcpy(db, hb.data(), bytes, mcMemcpyHostToDevice));

  int threads = 256;
  int blocks = (n + threads - 1) / threads;

  // Warmup
  for (int i = 0; i < 10; ++i) {
    vector_add<<<blocks, threads>>>(da, db, dc, n);
  }
  CHECK(mcDeviceSynchronize());

  // Timed region (mcTracer captures this)
  for (int i = 0; i < reps; ++i) {
    vector_add<<<blocks, threads>>>(da, db, dc, n);
  }
  CHECK(mcDeviceSynchronize());

  CHECK(mcFree(da));
  CHECK(mcFree(db));
  CHECK(mcFree(dc));
}

int main(int argc, char** argv) {
  int n = 1 << 20;
  int reps = 100;
  if (argc > 1) n = std::atoi(argv[1]);
  if (argc > 2) reps = std::atoi(argv[2]);

  int dev = 0;
  CHECK(mcSetDevice(dev));
  mcDeviceProp_t prop{};
  CHECK(mcGetDeviceProperties(&prop, dev));
  printf("device: %s n=%d reps=%d\n", prop.name, n, reps);

  launch_kernel(n, reps);
  printf("done\n");
  return 0;
}

// NOTE: MACA 3.7 ships the runtime as <mcr/mc_runtime.h> with mc* names (mcMalloc,
// mcMemcpy, mcDeviceSynchronize). Checked by compiling this file with
// `mxcc -x maca -offload-arch native -gcc-version=11` on a C500 with MACA 3.7.0.38.
// Without -gcc-version, mxcc may fail to find <tuple> from the runtime headers.
