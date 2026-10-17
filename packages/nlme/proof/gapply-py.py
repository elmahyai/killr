import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.gapply import gapply
from nlme.getgroups import GroupedDataFrame


_RESPONSE = (
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
_SUBJECT_LEVELS = (
    "M16", "M05", "M02", "M11", "M07", "M08", "M03", "M12", "M13", "M14", "M09",
    "M15", "M06", "M04", "M01", "M10", "F10", "F09", "F06", "F01", "F05", "F07",
    "F02", "F08", "F03", "F04", "F11",
)
_SUBJECT_CODES = (
    15, 15, 15, 15, 3, 3, 3, 3, 7, 7, 7, 7, 14, 14, 14, 14, 2, 2, 2, 2, 13, 13,
    13, 13, 5, 5, 5, 5, 6, 6, 6, 6, 11, 11, 11, 11, 16, 16, 16, 16, 4, 4, 4, 4,
    8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 12, 12, 12, 12, 1, 1, 1, 1, 20, 20,
    20, 20, 23, 23, 23, 23, 25, 25, 25, 25, 26, 26, 26, 26, 21, 21, 21, 21, 19,
    19, 19, 19, 22, 22, 22, 22, 24, 24, 24, 24, 18, 18, 18, 18, 17, 17, 17, 17,
    27, 27, 27, 27,
)


def orthodont():
    """Orthodont as a groupedData stand-in: distance ~ age | Subject."""
    return GroupedDataFrame(
        columns={
            "distance": np.asarray(_RESPONSE, dtype=np.float64),
            "age": np.asarray(_AGE, dtype=np.float64),
            "Subject": np.asarray(_SUBJECT_CODES, dtype=np.float64),
        },
        formula="distance ~ age | Subject",
        group_levels=_SUBJECT_LEVELS,
    )


def one():
    data = orthodont()
    m1 = gapply(data, FUN=lambda x: float(np.mean(x.columns["distance"])), form="distance ~ age | Subject")
    m2 = gapply(
        data,
        which=[1, 2],
        FUN=lambda x: len(x.columns["age"]) + float(np.mean(x.columns["age"])),
    )
    m3 = gapply(
        data,
        which="distance",
        FUN=lambda x: float(np.max(x.columns["distance"]) - np.min(x.columns["distance"])),
        form="distance ~ age | Subject",
    )
    return np.concatenate([np.asarray(m1, dtype=np.float64), np.asarray(m2, dtype=np.float64), np.asarray(m3, dtype=np.float64)])


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
