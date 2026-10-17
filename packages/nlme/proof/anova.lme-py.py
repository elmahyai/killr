import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nlme.lme_family as lme_family
from nlme.lme_family import anova_lme, lme, numeric_anova

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


def one():
    return numeric_anova(anova_lme(lme("distance ~ age", data=orthodont(), control={"apVar": False})))


ITERATIONS = []
_original_fit = lme_family._optimize_variance_fit


def _record_fit(start, con, block, control, reml):
    par, info = _original_fit(start, con, block, control, reml)
    ITERATIONS.append([info["iterations"], info["evaluations"]["function"], info["evaluations"]["gradient"]])
    return par, info


lme_family._optimize_variance_fit = _record_fit
value = one()
lme_family._optimize_variance_fit = _original_fit
iterations = ITERATIONS
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"iterations":%s,"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), json.dumps(iterations), statistics.median(elapsed))
)
