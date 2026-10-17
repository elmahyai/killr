"""Proof: mclust.sim_evv_vee_eve_vve.simVVE (mclust 6.1.3, model VVE) against R on the same fixtures.

Run after proof/simVVE-r.R, from packages/mclust:
    Rscript proof/simVVE-r.R && python3 proof/simVVE-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_evv_vee_eve_vve import simVVE  # noqa: E402

p = sim_params("VVE")
pm = sim_params_missing("VVE")

if __name__ == "__main__":
    run_sim_proof("simVVE", [
        ("main", lambda: simVVE(p, 500, seed=20260917)),
        ("small", lambda: simVVE(p, 5, seed=7)),
        ("odd", lambda: simVVE(p, 37, seed=123)),
        ("missing", lambda: simVVE(pm, 20, seed=5))
    ])
