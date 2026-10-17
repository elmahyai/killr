"""Proof: mclust.sim_vev_vii_vvi_vvv.simVVV (mclust 6.1.3, model VVV) against R on the same fixtures.

Run after proof/simVVV-r.R, from packages/mclust:
    Rscript proof/simVVV-r.R && python3 proof/simVVV-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_vev_vii_vvi_vvv import simVVV  # noqa: E402

p = sim_params("VVV")
pm = sim_params_missing("VVV")

if __name__ == "__main__":
    run_sim_proof("simVVV", [
        ("main", lambda: simVVV(p, 500, seed=20260917)),
        ("small", lambda: simVVV(p, 5, seed=7)),
        ("odd", lambda: simVVV(p, 37, seed=123)),
        ("missing", lambda: simVVV(pm, 20, seed=5)),
        ("chol", lambda: simVVV(sim_params("VVV", use_chol=True), 500, seed=20260917))
    ])
