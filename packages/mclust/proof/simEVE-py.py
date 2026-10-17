"""Proof: mclust.sim_evv_vee_eve_vve.simEVE (mclust 6.1.3, model EVE) against R on the same fixtures.

Run after proof/simEVE-r.R, from packages/mclust:
    Rscript proof/simEVE-r.R && python3 proof/simEVE-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_evv_vee_eve_vve import simEVE  # noqa: E402

p = sim_params("EVE")
pm = sim_params_missing("EVE")

if __name__ == "__main__":
    run_sim_proof("simEVE", [
        ("main", lambda: simEVE(p, 500, seed=20260917)),
        ("small", lambda: simEVE(p, 5, seed=7)),
        ("odd", lambda: simEVE(p, 37, seed=123)),
        ("missing", lambda: simEVE(pm, 20, seed=5))
    ])
