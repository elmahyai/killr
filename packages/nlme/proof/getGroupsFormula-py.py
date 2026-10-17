import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.astable import GroupedData
from nlme.corar1 import corAR1
from nlme.getgroupsformula import getGroupsFormula
from nlme.lmlistformula import lmList_formula
from nlme.restruct import reStruct


def fmt(x):
    if x is None:
        return "NULL"
    if isinstance(x, list):
        return "&".join(f"{name}={formula}" for name, formula in x)
    return x


@dataclass(slots=True)
class OrthodontFrame:
    columns: dict[str, list]
    group_levels: tuple[str, ...]


def orthodont() -> OrthodontFrame:
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
    return OrthodontFrame(
        columns={
            "distance": list(gd.response),
            "age": list(gd.covariate),
            "Subject": list(gd.groups),
        },
        group_levels=gd.group_levels,
    )


def one():
    fm1 = SimpleNamespace(modelStruct=SimpleNamespace(reStruct=reStruct("~age | Subject", data={"age": [8.0, 10.0, 12.0, 14.0]})))
    lml = lmList_formula("distance ~ age | Subject", data=orthodont())
    rs = reStruct("~1 | Subject")
    cs = corAR1(0.3, form="~ 1 | Subject")
    parts = [
        getGroupsFormula("distance ~ age | Subject"),
        getGroupsFormula("distance ~ age | Subject", asList=True),
        getGroupsFormula("distance ~ age | Subject/Sex"),
        getGroupsFormula("distance ~ age | Subject/Sex", asList=True),
        getGroupsFormula("distance ~ age"),
        getGroupsFormula(fm1),
        getGroupsFormula(fm1, asList=True),
        getGroupsFormula(lml),
        getGroupsFormula(lml, asList=True),
        getGroupsFormula(rs),
        getGroupsFormula(rs, asList=True),
        getGroupsFormula(cs),
        getGroupsFormula(cs, asList=True),
    ]
    return ";".join(fmt(part) for part in parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
