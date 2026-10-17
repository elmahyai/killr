"""Proof: mclust.sim_vev_vii_vvi_vvv.simVII (mclust 6.1.3, model VII) against R on the same fixtures.

Run after proof/simVII-r.R, from packages/mclust:
    Rscript proof/simVII-r.R && python3 proof/simVII-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_fixtures import sim_params, sim_params_missing  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.sim_vev_vii_vvi_vvv import simVII  # noqa: E402

p = sim_params("VII")
pm = sim_params_missing("VII")

if __name__ == "__main__":
    run_sim_proof("simVII", [
        ("main", lambda: simVII(p, 500, seed=20260917)),
        ("small", lambda: simVII(p, 5, seed=7)),
        ("odd", lambda: simVII(p, 37, seed=123)),
        ("missing", lambda: simVII(pm, 20, seed=5))
    ])
