from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from shuffle_harness import Case, run_proof  # noqa: E402
from permute import shuffleSet, how, Within, Plots  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
cases = [
    Case("sset_free_nocheck", 61, lambda: shuffleSet(6, 4, how(within=Within(type="free")), check=False)),
    Case("sset_free_check_complete", 62, lambda: shuffleSet(6, 4, how(within=Within(type="free")), quietly=True)),
    Case("sset_free_check_small", 60, lambda: shuffleSet(5, 2, how(within=Within(type="free")), quietly=True)),
    Case("sset_series_mirror", 63, lambda: shuffleSet(10, 3, how(within=Within(type="series", mirror=True)), check=False)),
    Case("sset_grid", 64, lambda: shuffleSet(8, 3, how(within=Within(type="grid", nrow=2, ncol=4)), check=False)),
    Case("sset_plots_free", 65, lambda: shuffleSet(8, 3, how(plots=Plots(strata=np.repeat([1, 2, 3, 4], 2), type="free"), within=Within(type="none")), check=False)),
    Case("sset_plots_free_within_free", 66, lambda: shuffleSet(8, 3, how(plots=Plots(strata=np.repeat([1, 2], 4), type="free"), within=Within(type="free")), check=False)),
    Case("sset_const_series", 67, lambda: shuffleSet(12, 3, how(plots=Plots(strata=np.repeat([1, 2, 3], 4), type="free"), within=Within(type="series", constant=True, mirror=True)), check=False)),
    Case("sset_const_grid_plots_series", 68, lambda: shuffleSet(16, 2, how(plots=Plots(strata=np.repeat([1, 2, 3, 4], 4), type="series", mirror=True), within=Within(type="grid", nrow=2, ncol=2, constant=True, mirror=True)), check=False)),
    Case("sset_const_free", 69, lambda: shuffleSet(12, 3, how(plots=Plots(strata=np.repeat([1, 2, 3], 4), type="free"), within=Within(type="free", constant=True)), check=False)),
    Case("sset_blocks", 70, lambda: shuffleSet(8, 3, how(blocks=np.repeat([1, 2], 4), within=Within(type="free")), check=False)),
    Case("sset_nperm_missing", 71, lambda: shuffleSet(8, None, how(within=Within(type="series"), nperm=3), check=False)),
    Case("sset_within_none", 72, lambda: shuffleSet(5, 2, how(within=Within(type="none")), check=False)),
    Case("sset_check_series", 73, lambda: shuffleSet(4, 3, how(within=Within(type="series", mirror=True)), quietly=True)),
]
run_proof("shuffleSet", cases, OUT)
