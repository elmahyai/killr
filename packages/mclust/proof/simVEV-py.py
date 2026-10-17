"""Proof: mclust.sim_vev_vii_vvi_vvv.simVEV (mclust 6.1.3, model VEV) against R on the same fixtures.

Run after proof/simVEV-r.R, from packages/mclust:
    Rscript proof/simVEV-r.R && python3 proof/simVEV-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_vev_vii_vvi_vvv import simVEV  # noqa: E402

p = sim_params("VEV")
pm = sim_params_missing("VEV")

if __name__ == "__main__":
    run_sim_proof("simVEV", [
        ("main", lambda: simVEV(p, 500, seed=20260917)),
        ("small", lambda: simVEV(p, 5, seed=7)),
        ("odd", lambda: simVEV(p, 37, seed=123)),
        ("missing", lambda: simVEV(pm, 20, seed=5))
    ])
