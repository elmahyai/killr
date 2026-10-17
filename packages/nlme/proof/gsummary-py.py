import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.groupeddata import DataFrame, Factor, groupedData
from nlme.gsummary import gsummary

# Orthodont rows (nlme 3.1-171), dumped from R with format(digits = 15).
DISTANCE = ( 26.0, 25.0, 29.0, 31.0, 21.5, 22.5, 23.0, 26.5, 23.0, 22.5, 24.0, 27.5, 25.5, 27.5, 26.5, 27.0, 20.0, 23.5, 22.5, 26.0, 24.5, 25.5, 27.0, 28.5, 22.0, 22.0, 24.5, 26.5, 24.0, 21.5, 24.5, 25.5, 23.0, 20.5, 31.0, 26.0, 27.5, 28.0, 31.0, 31.5, 23.0, 23.0, 23.5, 25.0, 21.5, 23.5, 24.0, 28.0, 17.0, 24.5, 26.0, 29.5, 22.5, 25.5, 25.5, 26.0, 23.0, 24.5, 26.0, 30.0, 22.0, 21.5, 23.5, 25.0, 21.0, 20.0, 21.5, 23.0, 21.0, 21.5, 24.0, 25.5, 20.5, 24.0, 24.5, 26.0, 23.5, 24.5, 25.0, 26.5, 21.5, 23.0, 22.5, 23.5, 20.0, 21.0, 21.0, 22.5, 21.5, 22.5, 23.0, 25.0, 23.0, 23.0, 23.5, 24.0, 20.0, 21.0, 22.0, 21.5, 16.5, 19.0, 19.0, 19.5, 24.5, 25.0, 28.0, 28.0 )
AGE = (  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14,  8, 10, 12, 14 )
SUBJECT = ( "M01", "M01", "M01", "M01", "M02", "M02", "M02", "M02", "M03", "M03", "M03", "M03", "M04", "M04", "M04", "M04", "M05", "M05", "M05", "M05", "M06", "M06", "M06", "M06", "M07", "M07", "M07", "M07", "M08", "M08", "M08", "M08", "M09", "M09", "M09", "M09", "M10", "M10", "M10", "M10", "M11", "M11", "M11", "M11", "M12", "M12", "M12", "M12", "M13", "M13", "M13", "M13", "M14", "M14", "M14", "M14", "M15", "M15", "M15", "M15", "M16", "M16", "M16", "M16", "F01", "F01", "F01", "F01", "F02", "F02", "F02", "F02", "F03", "F03", "F03", "F03", "F04", "F04", "F04", "F04", "F05", "F05", "F05", "F05", "F06", "F06", "F06", "F06", "F07", "F07", "F07", "F07", "F08", "F08", "F08", "F08", "F09", "F09", "F09", "F09", "F10", "F10", "F10", "F10", "F11", "F11", "F11", "F11" )
SUBJECT_LEVELS = ( "M16", "M05", "M02", "M11", "M07", "M08", "M03", "M12", "M13", "M14", "M09", "M15", "M06", "M04", "M01", "M10", "F10", "F09", "F06", "F01", "F05", "F07", "F02", "F08", "F03", "F04", "F11" )
SEX = ( "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Male", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female", "Female" )

LEVELS = SUBJECT_LEVELS


def orthodont():
    return DataFrame(
        columns={
            "distance": np.asarray(DISTANCE, dtype=np.float64),
            "age": np.asarray(AGE, dtype=np.float64),
            "Subject": Factor.from_values(SUBJECT, levels=LEVELS, ordered=True),
            "Sex": Factor.from_values(SEX, levels=("Male", "Female")),
        },
        attributes={"formula": "distance ~ age | Subject"},
    )


def flat(x):
    if isinstance(x, Factor):
        return x.codes.astype(np.float64) + 1.0
    return np.asarray(x, dtype=np.float64)


def one():
    obj = orthodont()
    a = gsummary(obj)
    b = gsummary(obj, FUN=np.max)
    d = gsummary(obj, invariantsOnly=True)
    e = gsummary(obj, omitGroupingFactor=True)
    parts = [
        flat(a["distance"]),
        flat(a["age"]),
        flat(a["Sex"]),
        flat(a["Subject"]),
        flat(b["distance"]),
        flat(b["age"]),
        flat(b["Sex"]),
        flat(d["Subject"]),
        flat(d["Sex"]),
        flat(e["Sex"]),
        flat(e["distance"]),
        flat(e["age"]),
    ]
    return np.concatenate(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
