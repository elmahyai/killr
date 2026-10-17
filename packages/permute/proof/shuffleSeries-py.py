from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from shuffle_harness import Case, run_proof  # noqa: E402
from permute import shuffleSeries  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
cases = [
    Case("ss_plain", 5, lambda: shuffleSeries(np.arange(1, 7))),
    Case("ss_mirror", 6, lambda: shuffleSeries(np.arange(1, 7), mirror=True)),
    Case("ss_mirror_vals", 8, lambda: shuffleSeries(np.array([10, 20, 30, 40, 50]), mirror=True)),
    Case("ss_start", 9, lambda: shuffleSeries(np.arange(1, 8), start=3)),
    Case("ss_start_mirror", 10, lambda: shuffleSeries(np.arange(1, 8), mirror=True, start=2)),
    Case("ss_flip_true", 11, lambda: shuffleSeries(np.arange(1, 7), mirror=True, start=4, flip=True)),
    Case("ss_flip_false", 12, lambda: shuffleSeries(np.arange(1, 7), mirror=True, start=1, flip=False)),
    Case("ss_start_big", 13, lambda: shuffleSeries(np.arange(1, 11), start=12)),
]
run_proof("shuffleSeries", cases, OUT)
