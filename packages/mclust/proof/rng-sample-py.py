import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "boot"))

from boot.rng import sample_int, set_seed, unif  # noqa: E402

seeds = [1, 42, 2026, 123456789]
cases = [
    ("sample.int(10,10,TRUE)", lambda: sample_int(10, 10, replace=True)),
    ("sample.int(5)", lambda: sample_int(5)),
    ("sample.int(100,7)", lambda: sample_int(100, 7)),
    ("sample.int(1000,5,TRUE)", lambda: sample_int(1000, 5, replace=True)),
    ("sample.int(1,3,TRUE)", lambda: sample_int(1, 3, replace=True)),
    ("sample.int(2,1)", lambda: sample_int(2, 1)),
    ("sample.int(7,0)", lambda: sample_int(7, 0)),
    ("sample.int(65537,20,TRUE)", lambda: sample_int(65537, 20, replace=True)),
    ("sample.int(100000,30,TRUE)", lambda: sample_int(100000, 30, replace=True)),
    ("sample.int(300000,5)", lambda: sample_int(300000, 5)),
    ("sample.int(2e7,5)", lambda: sample_int(20000000, 5)),
    ("sample.int(2e7,20000)", lambda: sample_int(20000000, 20000)),
]


def emit(label, values):
    print(" ".join([label] + ["%.17g" % float(v) for v in values]))


for s in seeds:
    set_seed(s)
    emit(f"seed {s} runif20", [unif() for _ in range(20)])
    for name, draw in cases:
        set_seed(s)
        emit(f"seed {s} {name}", draw())
