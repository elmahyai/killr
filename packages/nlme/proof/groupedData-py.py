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

def one():
    frame = {
        "distance": DISTANCE,
        "age": AGE,
        "Subject": SUBJECT,
        "Sex": SEX,
    }
    g = groupedData("distance ~ age | Subject", data=frame)
    h = groupedData("distance ~ age | Sex/Subject", data=frame)
    subject_codes = g.columns["Subject"].codes.astype(np.float64) + 1.0
    return np.concatenate(
        [
            subject_codes,
            g.columns["age"],
            g.columns["distance"],
            [
                float("nfnGroupedData" in g.classes),
                float("nmGroupedData" in h.classes),
                float("groupedData" in h.classes),
            ],
            h.columns["age"],
            h.columns["distance"],
        ]
    ).astype(np.float64)


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
