from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from shuffle_harness import Case, run_proof  # noqa: E402
from permute import shuffle, how, Within, Plots  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
cases = [
    Case("sh_free", 41, lambda: shuffle(6, how(within=Within(type="free")))),
    Case("sh_series", 42, lambda: shuffle(6, how(within=Within(type="series")))),
    Case("sh_series_mirror", 43, lambda: shuffle(6, how(within=Within(type="series", mirror=True)))),
    Case("sh_grid", 44, lambda: shuffle(8, how(within=Within(type="grid", nrow=2, ncol=4)))),
    Case("sh_grid_mirror", 45, lambda: shuffle(8, how(within=Within(type="grid", nrow=2, ncol=4, mirror=True)))),
    Case("sh_none", 46, lambda: shuffle(6, how(within=Within(type="none")))),
    Case("sh_vector_n", 47, lambda: shuffle(np.array([5, 6, 7, 8, 9, 10]), how(within=Within(type="free")))),
    Case("sh_plots_free", 48, lambda: shuffle(8, how(plots=Plots(strata=np.repeat([1, 2, 3, 4], 2), type="free"), within=Within(type="none")))),
    Case("sh_plots_free_within", 49, lambda: shuffle(8, how(plots=Plots(strata=np.repeat([1, 2], 4), type="free"), within=Within(type="free")))),
    Case("sh_plots_series_within_const", 50, lambda: shuffle(12, how(plots=Plots(strata=np.repeat([1, 2, 3, 4], 3), type="series", mirror=True), within=Within(type="free", constant=True)))),
    Case("sh_plots_free_within_series_const", 51, lambda: shuffle(12, how(plots=Plots(strata=np.repeat([1, 2, 3], 4), type="free"), within=Within(type="series", constant=True, mirror=True)))),
    Case("sh_plots_free_within_grid_const", 52, lambda: shuffle(16, how(plots=Plots(strata=np.repeat([1, 2, 3, 4], 4), type="free"), within=Within(type="grid", nrow=2, ncol=2, constant=True, mirror=True)))),
    Case("sh_plots_series_within_series", 53, lambda: shuffle(12, how(plots=Plots(strata=np.repeat([1, 2, 3], 4), type="series", mirror=True), within=Within(type="series", mirror=True)))),
    Case("sh_blocks", 54, lambda: shuffle(8, how(blocks=np.repeat([1, 2], 4), within=Within(type="free")))),
    Case("sh_blocks_interleaved", 55, lambda: shuffle(8, how(blocks=np.array([1, 2, 1, 2, 1, 2, 1, 2]), within=Within(type="series", mirror=True)))),
    Case("sh_blocks_plots", 56, lambda: shuffle(12, how(blocks=np.repeat(["x", "y"], 6), plots=Plots(strata=np.tile(np.repeat([1, 2, 3], 2), 2), type="free"), within=Within(type="free")))),
    Case("sh_blocks_zero_levels", 57, lambda: shuffle(8, how(blocks=np.repeat([1, 2], 4), plots=Plots(strata=np.array([1, 1, 2, 2, 3, 3, 4, 4]), type="free"), within=Within(type="free")))),
]
run_proof("shuffle", cases, OUT)
