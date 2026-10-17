import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nlme.lme_family as lme_family
from nlme.lme_family import lme, numeric_lme
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
# The nlminb limits are raised for all cases, as in lme-varfunc2-r.R.
CTRL_NOAP = {"apVar": False, "msMaxIter": 200, "msMaxEval": 400}
CTRL_AP = {"apVar": True, "msMaxIter": 200, "msMaxEval": 400}


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
        },
        group_levels=LEVELS,
        formula="distance ~ age | Subject",
    )


CASES = [
    ("varPowerFixed", lambda d: lme("distance ~ age", data=d, weights=varPower(form="~age", fixed=0.5), control=CTRL_NOAP)),
    ("varExpFixed", lambda d: lme("distance ~ age", data=d, weights=varExp(form="~age", fixed=0.1), control=CTRL_NOAP)),
    ("varPowerFitted", lambda d: lme("distance ~ age", data=d, weights=varPower(), control=CTRL_NOAP)),
    ("varExpFitted", lambda d: lme("distance ~ age", data=d, weights=varExp(), control=CTRL_NOAP)),
    ("varConstPowerFitted", lambda d: lme("distance ~ age", data=d, weights=varConstPower(), control=CTRL_NOAP)),
    ("varPowerApVar", lambda d: lme("distance ~ age", data=d, weights=varPower(form="~age"), control=CTRL_AP)),
]


ITERATIONS = {}
_original_nlminb = lme_family.nlminb_port
_current = {"log": None}


def _record_nlminb(objective, start, control=None):
    fit = _original_nlminb(objective, start, control=control)
    if _current["log"] is not None:
        _current["log"].append([fit["iterations"], fit["evaluations"]["function"], fit["evaluations"]["gradient"]])
    return fit


lme_family.nlminb_port = _record_nlminb


def one():
    values = []
    lengths = []
    for name, build in CASES:
        fit = build(orthodont())
        case = numeric_lme(fit)
        values.append([float(v) for v in case])
        lengths.append(len(case))
    return values, lengths


def one_recorded():
    values = []
    lengths = []
    for name, build in CASES:
        _current["log"] = ITERATIONS.setdefault(name, [])
        ITERATIONS[name].clear()
        fit = build(orthodont())
        case = numeric_lme(fit)
        values.append([float(v) for v in case])
        lengths.append(len(case))
        _current["log"] = None
    return values, lengths


value_cases, lengths = one_recorded()
lme_family.nlminb_port = _original_nlminb
iterations = [list(ITERATIONS[name]) for name, _ in CASES]

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

flat = [v for case in value_cases for v in case]
print(
    '{"value":[%s],"lengths":%s,"iterations":%s,"median_ms":%.17g}'
    % (
        ",".join("%.17g" % v for v in flat),
        json.dumps(lengths),
        json.dumps(iterations),
        statistics.median(elapsed),
    )
)
