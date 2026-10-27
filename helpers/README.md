# Helpers — metax-report-skill

| Script | Purpose |
|---|---|
| `metax_utils.py` | Core library: CSV/JSON parsing, canonical mapping, bottleneck class |
| `analyze_reports.py` | One-shot metrics extraction + A/B compare |
| `parse_mctrace.py` | mcTracer JSON → kernel latency ranking |
| `summarize_profile_run.sh` | Inventory run directory |
| `harness_template.cpp` | Minimal mxcc harness for mcTracer |

All scripts use **stdlib + metax_utils only** (no pip dependencies).

## Examples

```bash
SKILL=skills/metax-report-skill
RUN=profile/vecadd_baseline

bash "$SKILL/helpers/summarize_profile_run.sh" "$RUN"

python3 "$SKILL/helpers/parse_mctrace.py" \
  --trace "$RUN/reports/mctrace/trace-"*.json \
  --out "$RUN/analysis/mctrace_summary.json"

python3 "$SKILL/helpers/analyze_reports.py" \
  --run-dir "$RUN" --tag baseline \
  --mcprof "$RUN/reports/mcprof.csv"
```

Canonical metrics align with AKW `_substrate/backends/_evidence_metax.py` and `diagnose.py` threshold profile `metax`.
