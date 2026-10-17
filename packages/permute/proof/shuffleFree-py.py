from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from shuffle_harness import Case, run_proof  # noqa: E402
from permute import shuffleFree  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
cases = [
    Case("ff_full10", 42, lambda: shuffleFree(10, 10)),
    Case("ff_part10_3", 1, lambda: shuffleFree(10, 3)),
    Case("ff_vec", 7, lambda: shuffleFree(np.array([10, 20, 30, 40, 50]), 5)),
    Case("ff_one", 3, lambda: shuffleFree(1, 1)),
    Case("ff_large_k", 99, lambda: shuffleFree(1000, 50)),
    Case("ff_pair", 11, lambda: shuffleFree(np.array([2, 4, 6, 8]), 2)),
    Case("ff_hash", 2024, lambda: shuffleFree(10000001, 5)),
    Case("ff_zero", 5, lambda: shuffleFree(5, 0)),
]
run_proof("shuffleFree", cases, OUT)
