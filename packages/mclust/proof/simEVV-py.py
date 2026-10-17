"""Proof: mclust.sim_evv_vee_eve_vve.simEVV (mclust 6.1.3, model EVV) against R on the same fixtures.

Run after proof/simEVV-r.R, from packages/mclust:
    Rscript proof/simEVV-r.R && python3 proof/simEVV-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_evv_vee_eve_vve import simEVV  # noqa: E402

p = sim_params("EVV")
pm = sim_params_missing("EVV")

if __name__ == "__main__":
    run_sim_proof("simEVV", [
        ("main", lambda: simEVV(p, 500, seed=20260917)),
        ("small", lambda: simEVV(p, 5, seed=7)),
        ("odd", lambda: simEVV(p, 37, seed=123)),
        ("missing", lambda: simEVV(pm, 20, seed=5))
    ])
