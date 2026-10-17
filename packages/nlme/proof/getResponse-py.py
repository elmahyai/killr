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
from nlme.astable import GroupedData, asTable
from nlme.balancedgrouped import balancedGrouped
from nlme.getgroups import GroupedDataFrame
from nlme.getresponse import Lme, getResponse

_SUBJECT_CODES = (
    15, 15, 15, 15, 3, 3, 3, 3, 7, 7, 7, 7, 14, 14, 14, 14, 2, 2, 2, 2, 13, 13,
    13, 13, 5, 5, 5, 5, 6, 6, 6, 6, 11, 11, 11, 11, 16, 16, 16, 16, 4, 4, 4, 4,
    8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 12, 12, 12, 12, 1, 1, 1, 1, 20, 20,
    20, 20, 23, 23, 23, 23, 25, 25, 25, 25, 26, 26, 26, 26, 21, 21, 21, 21, 19,
    19, 19, 19, 22, 22, 22, 22, 24, 24, 24, 24, 18, 18, 18, 18, 17, 17, 17, 17,
    27, 27, 27, 27,
)
_FM1_RESPONSE = (
    21, 20, 21.5, 23, 21, 21.5, 24, 25.5, 20.5, 24, 24.5, 26, 23.5, 24.5, 25,
    26.5, 21.5, 23, 22.5, 23.5, 20, 21, 21, 22.5, 21.5, 22.5, 23, 25, 23, 23,
    23.5, 24, 20, 21, 22, 21.5, 16.5, 19, 19, 19.5, 24.5, 25, 28, 28,
)


def orthodont():
    response = (
        26, 25, 29, 31, 21.5, 22.5, 23, 26.5, 23, 22.5, 24, 27.5, 25.5, 27.5, 26.5,
        27, 20, 23.5, 22.5, 26, 24.5, 25.5, 27, 28.5, 22, 22, 24.5, 26.5, 24, 21.5,
        24.5, 25.5, 23, 20.5, 31, 26, 27.5, 28, 31, 31.5, 23, 23, 23.5, 25, 21.5,
        23.5, 24, 28, 17, 24.5, 26, 29.5, 22.5, 25.5, 25.5, 26, 23, 24.5, 26, 30,
        22, 21.5, 23.5, 25, 21, 20, 21.5, 23, 21, 21.5, 24, 25.5, 20.5, 24, 24.5,
        26, 23.5, 24.5, 25, 26.5, 21.5, 23, 22.5, 23.5, 20, 21, 21, 22.5, 21.5,
        22.5, 23, 25, 23, 23, 23.5, 24, 20, 21, 22, 21.5, 16.5, 19, 19, 19.5, 24.5,
        25, 28, 28,
    )
    covariate = (8, 10, 12, 14) * 27
    groups = (
        "M01", "M01", "M01", "M01", "M02", "M02", "M02", "M02", "M03", "M03", "M03",
        "M03", "M04", "M04", "M04", "M04", "M05", "M05", "M05", "M05", "M06", "M06",
        "M06", "M06", "M07", "M07", "M07", "M07", "M08", "M08", "M08", "M08", "M09",
        "M09", "M09", "M09", "M10", "M10", "M10", "M10", "M11", "M11", "M11", "M11",
        "M12", "M12", "M12", "M12", "M13", "M13", "M13", "M13", "M14", "M14", "M14",
        "M14", "M15", "M15", "M15", "M15", "M16", "M16", "M16", "M16", "F01", "F01",
        "F01", "F01", "F02", "F02", "F02", "F02", "F03", "F03", "F03", "F03", "F04",
        "F04", "F04", "F04", "F05", "F05", "F05", "F05", "F06", "F06", "F06", "F06",
        "F07", "F07", "F07", "F07", "F08", "F08", "F08", "F08", "F09", "F09", "F09",
        "F09", "F10", "F10", "F10", "F10", "F11", "F11", "F11", "F11",
    )
    group_levels = (
        "M16", "M05", "M02", "M11", "M07", "M08", "M03", "M12", "M13", "M14", "M09",
        "M15", "M06", "M04", "M01", "M10", "F10", "F09", "F06", "F01", "F05", "F07",
        "F02", "F08", "F03", "F04", "F11",
    )
    return GroupedData(
        response=response,
        covariate=covariate,
        groups=groups,
        group_levels=group_levels,
        covariate_levels=(8, 10, 12, 14),
    )


def one():
    orth2 = balancedGrouped(
        "distance ~ age | Subject",
        data=asTable(orthodont()),
        labels={"x": "Age", "y": "Distance"},
        units={"x": "(yr)", "y": "(mm)"},
    )
    orth = GroupedDataFrame(
        {
            "distance": np.asarray(orthodont().response, dtype=np.float64),
            "age": np.asarray(orthodont().covariate, dtype=np.float64),
            "Subject": np.asarray(_SUBJECT_CODES, dtype=np.float64),
        },
        formula="distance ~ age | Subject",
    )
    fm1 = Lme(
        fitted=np.asarray(_FM1_RESPONSE, dtype=np.float64),
        resid=np.zeros(len(_FM1_RESPONSE), dtype=np.float64),
    )
    parts = [
        np.asarray(getResponse(orth2), dtype=np.float64),
        np.asarray(getResponse(orth, "distance ~ age | Subject"), dtype=np.float64),
        np.asarray(getResponse(fm1), dtype=np.float64),
    ]
    return np.concatenate(parts)


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
