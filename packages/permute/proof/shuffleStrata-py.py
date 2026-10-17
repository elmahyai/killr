from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from shuffle_harness import Case, run_proof  # noqa: E402
from permute import shuffleStrata  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
cases = [
    Case("st_free", 31, lambda: shuffleStrata(np.array(["a", "a", "b", "b", "c", "c"]), "free")),
    Case("st_series", 32, lambda: shuffleStrata(np.repeat([1, 2, 3, 4], 2), "series")),
    Case("st_series_mirror", 33, lambda: shuffleStrata(np.repeat([1, 2, 3, 4], 2), "series", mirror=True)),
    Case("st_series_start_flip", 34, lambda: shuffleStrata(np.repeat([1, 2, 3], 2), "series", mirror=True, start=2, flip=True)),
    Case("st_grid", 35, lambda: shuffleStrata(np.repeat([1, 2, 3, 4], 2), "grid", nrow=2, ncol=2)),
    Case("st_grid_mirror", 36, lambda: shuffleStrata(np.repeat(["p", "q", "r", "s"], 3), "grid", nrow=2, ncol=2, mirror=True)),
    Case("st_free_unused", 37, lambda: shuffleStrata(np.repeat([1, 3, 5], 2), "free")),
    Case("st_free_numeric", 38, lambda: shuffleStrata(np.array([10, 10, 2, 2, 33, 33]), "free")),
]
run_proof("shuffleStrata", cases, OUT)
