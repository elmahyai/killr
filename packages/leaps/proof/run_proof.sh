#!/usr/bin/env bash
# Run the leaps proof end to end.
#
# Needs leaps 3.2 installed for R. Set LEAPS_RLIB to the library that holds it,
# for example: R CMD INSTALL -l /some/lib /path/to/leaps_3.2.tar.gz
# The Rust extension must already be built:
#   .venv/bin/maturin develop --release --manifest-path crates/leaps/Cargo.toml
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
PROOF="$REPO/packages/leaps/proof"
PY="$REPO/.venv/bin/python"

cd "$PROOF"
"$PY" make_design.py
Rscript r_proof.R
"$PY" rust_proof.py
"$PY" compare.py
