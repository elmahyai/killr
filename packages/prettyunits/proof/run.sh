#!/usr/bin/env bash
# Run every prettyunits proof: R, then Python, then compare.
# Usage: bash proof/run.sh   (from packages/prettyunits, or from anywhere)
cd "$(dirname "$0")/.." || exit 1
FUNCTIONS="compute_bytes compute_num pretty_bytes pretty_color pretty_colour pretty_dt pretty_ms pretty_num pretty_p_value pretty_round pretty_sec pretty_signif time_ago vague_dt"
for f in $FUNCTIONS; do
  Rscript "proof/$f-r.R" > /dev/null 2> "docs/output/$f-r.err" || echo "R failed: $f"
  python3 "proof/$f-py.py" > /dev/null 2> "docs/output/$f-python.err" || echo "Python failed: $f"
done
find docs/output -name '*.err' -empty -delete
python3 proof/compare.py
