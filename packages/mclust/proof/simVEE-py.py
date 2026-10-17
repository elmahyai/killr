"""Proof: mclust.sim_evv_vee_eve_vve.simVEE (mclust 6.1.3, model VEE) against R on the same fixtures.

Run after proof/simVEE-r.R, from packages/mclust:
    Rscript proof/simVEE-r.R && python3 proof/simVEE-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_evv_vee_eve_vve import simVEE  # noqa: E402

p = sim_params("VEE")
pm = sim_params_missing("VEE")

if __name__ == "__main__":
    run_sim_proof("simVEE", [
        ("main", lambda: simVEE(p, 500, seed=20260917)),
        ("small", lambda: simVEE(p, 5, seed=7)),
        ("odd", lambda: simVEE(p, 37, seed=123)),
        ("missing", lambda: simVEE(pm, 20, seed=5))
    ])
