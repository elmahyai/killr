import json
import statistics
import time
from pathlib import Path

import numpy as np

from survival.is_ratetable import is_ratetable


class _RatetableDate:
    class_ = "Date"

    def __init__(self, values):
        self.values = list(values)

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)


def _load_survexp_us():
    here = Path(__file__).resolve().parent
    meta = json.loads((here / "is.ratetable_survexp_us.json").read_text())
    data = np.fromfile(here / "is.ratetable_survexp_us.bin", dtype="<f8")
    cutpoints = []
    for values, is_date in zip(meta["cutpoints"], meta["cutpoints_is_date"]):
        if not values:
            cutpoints.append(None)
        elif is_date:
            cutpoints.append(_RatetableDate(values))
        else:
            cutpoints.append(values)
    dimnames = [meta["dimnames"][name] for name in meta["dimnames_names"]]
    return {
        "class": "ratetable",
        "data": data,
        "dim": meta["dim"],
        "dimnames": dimnames,
        "dimnames_names": meta["dimnames_names"],
        "type": meta["type"],
        "cutpoints": cutpoints,
    }


def _make_rt():
    return {
        "class": "ratetable",
        "data": np.arange(1, 7, dtype=float),
        "dim": [2, 3],
        "dimnames": [["a", "b"], ["x", "y", "z"]],
        "dimnames_names": ["dim1", "dim2"],
        "type": [2, 1],
        "cutpoints": [[0, 1], None],
    }


def _serialize_bool(value):
    if isinstance(value, bool):
        return str(int(value))
    return "|".join(value)


def one():
    lung = {"class": "data.frame", "data": {}}
    return [
        _serialize_bool(is_ratetable(_load_survexp_us())),
        _serialize_bool(is_ratetable(lung)),
        _serialize_bool(is_ratetable(_make_rt())),
        _serialize_bool(is_ratetable([1, 2, 3])),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
