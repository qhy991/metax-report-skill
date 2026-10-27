# metax-report-skill

Structured profiling workflow for **MetaX (沐曦) GPU** kernels using the MACA SDK tools **mcTracer** and **mcProfiler**.

Standalone copy of the KerSor plugin's `skills/metax-report-skill/` (KerSor commit b31148ec), with a MetaX C500 section added (`reference/10-c500.md`).

Mirrors the workflow of `ncu-report-skill` and `msprof-report-skill` but targets MetaX C550 / MXC550 (and C500, see `reference/10-c500.md`) with CUDA-compatible source (`mxcc`, `torch.cuda`, Triton MacaDriver).

## When to use

- Profiling a `.cu` kernel compiled with `mxcc`
- Reading mcTracer JSON timeline or mcProfiler CSV
- Diagnosing memory vs compute bottlenecks on MetaX (`dram_pct`, `sm_pct`)
- Writing evidence-backed optimization reports for KerSor / AKW `metax` backend sessions

## Quick install (optional global symlink)

```bash
git clone https://github.com/qhy991/metax-report-skill
ln -sf "$PWD/metax-report-skill" ~/.claude/skills/metax-report-skill
```

## Layout

Same run-directory convention as `ncu-report-skill`:

```
profile/<run_name>/
├── REPORT.md
├── harness/
├── reports/          # mcprof.csv, mctrace logs, copied trace JSON
└── analysis/         # helpers output
```

## Helpers

| Script | Purpose |
|---|---|
| `helpers/summarize_profile_run.sh` | Inventory run dir |
| `helpers/parse_mctrace.py` | mcTracer JSON → kernel latency table |
| `helpers/analyze_reports.py` | mcProfiler CSV → canonical metrics + A/B |
| `helpers/metax_utils.py` | Shared parsing library |

See `SKILL.md` for the full workflow.
