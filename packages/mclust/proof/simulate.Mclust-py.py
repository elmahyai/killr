"""Proof: mclust.simulate_mclust.simulate_Mclust (mclust 6.1.3 simulate.Mclust) against R, all 16 models.

Each case is one simulate_Mclust call through the default dispatch. The timed unit is the same
sweep of 18 calls as in proof/simulate.Mclust-r.R. Run from packages/mclust:
    Rscript proof/simulate.Mclust-r.R && python3 proof/simulate.Mclust-py.py
"""

import copy
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

import sim_core_fixtures as core  # noqa: E402
from sim_fixtures import sim_params  # noqa: E402
from sim_proof_common import run_sim_proof  # noqa: E402
from mclust.simulate_mclust import simulate_Mclust  # noqa: E402

GROUP_A = {
    "E": core.pars_E,
    "V": core.pars_V,
    "EII": core.pars_EII,
    "EEI": core.pars_EEI,
    "VEI": core.pars_VEI,
    "EVI": core.pars_EVI,
    "EEE": core.pars_EEE,
    "EEV": core.pars_EEV,
}


def pars_for(model):
    if model in GROUP_A:
        return copy.deepcopy(GROUP_A[model])
    return sim_params(model)


def mk(model):
    return {"modelName": model, "parameters": pars_for(model)}


MODELS16 = ["E", "V", "EII", "VII", "EEI", "VEI", "EVI", "VVI",
            "EEE", "VEE", "EVE", "VVE", "EEV", "VEV", "EVV", "VVV"]

CASES = [
    ("VEV-main", lambda: simulate_Mclust(mk("VEV"), 500, seed=20260917)),
    ("VEV-small", lambda: simulate_Mclust(mk("VEV"), 5, seed=7)),
] + [(m, (lambda m=m: simulate_Mclust(mk(m), 37, seed=123))) for m in MODELS16]


def sweep():
    return [fn() for _, fn in CASES]


if __name__ == "__main__":
    run_sim_proof("simulate.Mclust", CASES, timed=sweep, per_case=True)
