import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# Load the nlme modules without running nlme/__init__.py, which imports the
# onecomp extension (phenoModel) that is not built in this environment.
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.astable import GroupedData  # noqa: E402
from nlme.getgroups import GroupedDataFrame  # noqa: E402
from nlme.isbalanced import isBalanced  # noqa: E402


def orthodont() -> GroupedDataFrame:
    gd = GroupedData(
        response=(
            26, 25, 29, 31, 21.5, 22.5, 23, 26.5, 23, 22.5, 24, 27.5, 25.5, 27.5, 26.5,
            27, 20, 23.5, 22.5, 26, 24.5, 25.5, 27, 28.5, 22, 22, 24.5, 26.5, 24, 21.5,
            24.5, 25.5, 23, 20.5, 31, 26, 27.5, 28, 31, 31.5, 23, 23, 23.5, 25, 21.5,
            23.5, 24, 28, 17, 24.5, 26, 29.5, 22.5, 25.5, 25.5, 26, 23, 24.5, 26, 30,
            22, 21.5, 23.5, 25, 21, 20, 21.5, 23, 21, 21.5, 24, 25.5, 20.5, 24, 24.5,
            26, 23.5, 24.5, 25, 26.5, 21.5, 23, 22.5, 23.5, 20, 21, 21, 22.5, 21.5,
            22.5, 23, 25, 23, 23, 23.5, 24, 20, 21, 22, 21.5, 16.5, 19, 19, 19.5, 24.5,
            25, 28, 28,
        ),
        covariate=(8, 10, 12, 14) * 27,
        groups=(
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
        ),
        group_levels=(
            "M16", "M05", "M02", "M11", "M07", "M08", "M03", "M12", "M13", "M14", "M09",
            "M15", "M06", "M04", "M01", "M10", "F10", "F09", "F06", "F01", "F05", "F07",
            "F02", "F08", "F03", "F04", "F11",
        ),
        covariate_levels=(8, 10, 12, 14),
    )
    columns = {
        "distance": np.asarray(gd.response, dtype=np.float64),
        "age": np.asarray(gd.covariate, dtype=np.float64),
        "Subject": np.asarray(gd.groups, dtype=object),
    }
    return GroupedDataFrame(
        columns=columns,
        formula="distance ~ age | Subject",
        group_levels=tuple(gd.group_levels),
    )


def drop_first_row(frame: GroupedDataFrame) -> GroupedDataFrame:
    columns = {key: values[1:] for key, values in frame.columns.items()}
    return GroupedDataFrame(columns=columns, formula=frame.formula, group_levels=frame.group_levels)


def one():
    data = orthodont()
    o2 = drop_first_row(data)
    values = [
        float(isBalanced(data)),
        float(isBalanced(data, countOnly=True)),
        float(isBalanced(o2)),
        float(isBalanced(o2, countOnly=True)),
    ]
    return np.asarray(values, dtype=np.float64)


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
