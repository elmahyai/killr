import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nlme.lme_family as lme_family
from nlme.lme_family import lme, numeric_lme
from nlme.var_ident import varIdent
from nlme.var_power import varPower
from nlme.varconstpower import varConstPower
from nlme.varexp import varExp

SUBJECTS = [f"M{i:02d}" for i in range(1, 17)] + [f"F{i:02d}" for i in range(1, 12)]
LEVELS = (
    "M16", "M05", "M02", "M11", "M07", "M08", "M03", "M12", "M13", "M14", "M09",
    "M15", "M06", "M04", "M01", "M10", "F10", "F09", "F06", "F01", "F05", "F07",
    "F02", "F08", "F03", "F04", "F11",
)
DISTANCE = [
    26, 25, 29, 31, 21.5, 22.5, 23, 26.5, 23, 22.5, 24, 27.5, 25.5, 27.5, 26.5, 27,
    20, 23.5, 22.5, 26, 24.5, 25.5, 27, 28.5, 22, 22, 24.5, 26.5, 24, 21.5, 24.5, 25.5,
    23, 20.5, 31, 26, 27.5, 28, 31, 31.5, 23, 23, 23.5, 25, 21.5, 23.5, 24, 28, 17,
    24.5, 26, 29.5, 22.5, 25.5, 25.5, 26, 23, 24.5, 26, 30, 22, 21.5, 23.5, 25, 21, 20,
    21.5, 23, 21, 21.5, 24, 25.5, 20.5, 24, 24.5, 26, 23.5, 24.5, 25, 26.5, 21.5, 23,
    22.5, 23.5, 20, 21, 21, 22.5, 21.5, 22.5, 23, 25, 23, 23, 23.5, 24, 20, 21, 22,
    21.5, 16.5, 19, 19, 19.5, 24.5, 25, 28, 28,
]
# Orthodont$Sex: Male for M01..M16 (64 rows), Female for F01..F11 (44 rows).
SEX = [("Male" if name.startswith("M") else "Female") for name in SUBJECTS for _ in range(4)]
# The nlminb limits are raised for all four fits, as in lme-varfunc-r.R.
CONTROL = {"apVar": False, "msMaxIter": 200, "msMaxEval": 400}


@dataclass
class Frame:
    columns: dict
    group_levels: tuple
    formula: str
    classes: tuple = ("groupedData", "data.frame")


def orthodont():
    return Frame(
        columns={
            "distance": DISTANCE,
            "age": [8, 10, 12, 14] * 27,
            "Subject": [name for name in SUBJECTS for _ in range(4)],
            "Sex": SEX,
        },
        group_levels=LEVELS,
        formula="distance ~ age | Subject",
    )


def one():
    data = orthodont()
    fits = [
        lme("distance ~ age", data=data, weights=varPower(form="~age"), control=CONTROL),
        lme("distance ~ age", data=data, weights=varExp(form="~age"), control=CONTROL),
        lme("distance ~ age", data=data, weights=varIdent(form="~1|Sex"), control=CONTROL),
        lme("distance ~ age", data=data, weights=varConstPower(form="~age"), control=CONTROL),
        lme("distance ~ age", data=data, weights=varPower(form="~age|Sex"), control=CONTROL),
        lme("distance ~ age", data=data, weights=varExp(form="~age|Sex"), control=CONTROL),
    ]
    parts = []
    for fit in fits:
        parts.append(numeric_lme(fit))
    return [float(v) for part in parts for v in part]


ITERATIONS = []
_original_nlminb = lme_family.nlminb_port


def _record_nlminb(objective, start, control=None):
    fit = _original_nlminb(objective, start, control=control)
    ITERATIONS.append([fit["iterations"], fit["evaluations"]["function"], fit["evaluations"]["gradient"]])
    return fit


lme_family.nlminb_port = _record_nlminb
value = one()
lme_family.nlminb_port = _original_nlminb
iterations = ITERATIONS
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"iterations":%s,"median_ms":%.17g}'
    % (",".join("%.17g" % part for part in value), json.dumps(iterations), statistics.median(elapsed))
)
