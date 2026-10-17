"""Proof: mclust.sim_vev_vii_vvi_vvv.simVVI (mclust 6.1.3, model VVI) against R on the same fixtures.

Run after proof/simVVI-r.R, from packages/mclust:
    Rscript proof/simVVI-r.R && python3 proof/simVVI-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_vev_vii_vvi_vvv import simVVI  # noqa: E402

p = sim_params("VVI")
pm = sim_params_missing("VVI")

if __name__ == "__main__":
    run_sim_proof("simVVI", [
        ("main", lambda: simVVI(p, 500, seed=20260917)),
        ("small", lambda: simVVI(p, 5, seed=7)),
        ("odd", lambda: simVVI(p, 37, seed=123)),
        ("missing", lambda: simVVI(pm, 20, seed=5))
    ])
