#!/usr/bin/env bash
# Inventory a MetaX profile run directory and print analysis hints.
set -euo pipefail

RUN_DIR="${1:-.}"
RUN_DIR="$(cd "$RUN_DIR" && pwd)"

echo "=== MetaX profile run summary ==="
echo "run_dir: $RUN_DIR"
echo

for sub in harness reports analysis; do
  if [[ -d "$RUN_DIR/$sub" ]]; then
    echo "[$sub] $(find "$RUN_DIR/$sub" -type f 2>/dev/null | wc -l) files"
  else
    echo "[$sub] MISSING"
  fi
done
echo

# mcTracer traces
TRACES=()
while IFS= read -r f; do
  TRACES+=("$f")
done < <(find "$RUN_DIR/reports" -name 'trace-*.json' 2>/dev/null | sort)

if [[ ${#TRACES[@]} -eq 0 ]]; then
  echo "WARN: no trace-*.json under reports/ — mcTracer collection may have failed."
  echo "      See reference/03-collection.md (--odname must be relative to cwd)."
else
  echo "Found ${#TRACES[@]} mcTracer JSON file(s):"
  for f in "${TRACES[@]}"; do
    echo "  - $f ($(du -sh "$f" 2>/dev/null | cut -f1))"
  done
fi
echo

if [[ -f "$RUN_DIR/reports/mcprof.csv" ]]; then
  lines=$(wc -l < "$RUN_DIR/reports/mcprof.csv")
  echo "[mcprof.csv] $lines lines"
else
  echo "[mcprof.csv] MISSING (optional — use mcTracer-only path)"
fi
echo

echo "=== environment (quick) ==="
command -v mxcc >/dev/null 2>&1 && echo "  mxcc: $(command -v mxcc)" || echo "  mxcc: NOT FOUND"
command -v mcTracer >/dev/null 2>&1 && echo "  mcTracer: OK" || echo "  mcTracer: NOT FOUND"
command -v mcProfiler >/dev/null 2>&1 && echo "  mcProfiler: OK" || echo "  mcProfiler: NOT FOUND"
python3 -c "import torch; print('  torch.cuda:', torch.cuda.is_available())" 2>/dev/null || true
echo

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== next steps ==="
echo "1. python3 $SCRIPT_DIR/parse_mctrace.py --trace <trace.json> --out $RUN_DIR/analysis/mctrace_summary.json"
echo "2. python3 $SCRIPT_DIR/analyze_reports.py --run-dir $RUN_DIR --tag baseline --mcprof $RUN_DIR/reports/mcprof.csv"
echo "3. Read dram_pct/sm_pct thresholds: reference/08-metax-metric-guide.md"
echo "4. Write $RUN_DIR/REPORT.md (reference/07-report-template.md)"
