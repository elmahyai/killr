import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
_py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
_site = ROOT / ".venv" / "lib" / _py_ver / "site-packages"
sys.path[:0] = [
    str(ROOT / "packages" / "nlme"),
    str(_site),
    str(ROOT / "crates" / "onecomp"),
]
from nlme.getdata import Lme, LmeCall, ModelFrame, getData

_DISTANCE = (
    26, 25, 29, 31, 21.5, 22.5, 23, 26.5, 23, 22.5, 24, 27.5, 25.5, 27.5, 26.5,
    27, 20, 23.5, 22.5, 26, 24.5, 25.5, 27, 28.5, 22, 22, 24.5, 26.5, 24, 21.5,
    24.5, 25.5, 23, 20.5, 31, 26, 27.5, 28, 31, 31.5, 23, 23, 23.5, 25, 21.5,
    23.5, 24, 28, 17, 24.5, 26, 29.5, 22.5, 25.5, 25.5, 26, 23, 24.5, 26, 30,
    22, 21.5, 23.5, 25, 21, 20, 21.5, 23, 21, 21.5, 24, 25.5, 20.5, 24, 24.5,
    26, 23.5, 24.5, 25, 26.5, 21.5, 23, 22.5, 23.5, 20, 21, 21, 22.5, 21.5,
    22.5, 23, 25, 23, 23, 23.5, 24, 20, 21, 22, 21.5, 16.5, 19, 19, 19.5, 24.5,
    25, 28, 28,
)
_AGE = (8, 10, 12, 14) * 27
_SEX = ("Male",) * 64 + ("Female",) * 44
_SUBJECT_CODES = (
    15, 15, 15, 15, 3, 3, 3, 3, 7, 7, 7, 7, 14, 14, 14, 14, 2, 2, 2, 2, 13, 13,
    13, 13, 5, 5, 5, 5, 6, 6, 6, 6, 11, 11, 11, 11, 16, 16, 16, 16, 4, 4, 4, 4,
    8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 12, 12, 12, 12, 1, 1, 1, 1, 20, 20,
    20, 20, 23, 23, 23, 23, 25, 25, 25, 25, 26, 26, 26, 26, 21, 21, 21, 21, 19,
    19, 19, 19, 22, 22, 22, 22, 24, 24, 24, 24, 18, 18, 18, 18, 17, 17, 17, 17,
    27, 27, 27, 27,
)


def one():
    frame = ModelFrame(
        {
            "distance": np.asarray(_DISTANCE, dtype=np.float64),
            "age": np.asarray(_AGE, dtype=np.float64),
            "Subject": np.asarray(_SUBJECT_CODES, dtype=np.float64),
            "Sex": np.asarray(_SEX, dtype=object),
        }
    )
    fit = Lme(
        data=frame,
        call=LmeCall(subset='Sex == "Female"'),
    )
    result = getData(fit)
    return np.concatenate(
        [
            np.asarray([result.nrow, len(result.columns)], dtype=np.float64),
            np.asarray(result.columns["distance"], dtype=np.float64),
            np.asarray(result.columns["age"], dtype=np.float64),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": [float(part) for part in value],
            "median_ms": statistics.median(elapsed),
        }
    )
)
