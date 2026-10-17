import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.lme_family import nlme_formula, numeric_nlme


@dataclass
class Frame:
    columns: dict


def height_data():
    age = [2, 4, 6, 8, 10] * 4
    group = [name for name in "ABCD" for _ in range(5)]
    shift = [value for value in (-4, 1, 3, -2) for _ in range(5)]
    noise = [
        0.2, -0.1, 0.4, -0.3, 0.1, 0.0, 0.3, -0.2, 0.1, -0.4,
        -0.2, 0.2, 0.0, -0.1, 0.3, 0.1, -0.3, 0.2, 0.0, -0.2,
    ]
    height = [
        (100 + bi) + (15 - (100 + bi)) * math.exp(-math.exp(-3.2) * a) + e
        for a, bi, e in zip(age, shift, noise)
    ]
    return Frame(columns={"height": height, "age": age, "group": group})


def one():
    fit = nlme_formula(
        "height ~ SSasymp(age, Asym, R0, lrc)",
        height_data(),
        fixed="Asym + R0 + lrc ~ 1",
        random="Asym ~ 1",
        groups="~ group",
        start={"Asym": 100.0, "R0": 15.0, "lrc": -3.2},
    )
    return numeric_nlme(fit)


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
