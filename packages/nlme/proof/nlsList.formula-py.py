import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.nlslistformula import coef, nlsList_formula


@dataclass(slots=True)
class Co2Frame:
    columns: dict[str, list]
    group_levels: tuple[str, ...]


def co2() -> Co2Frame:
    return Co2Frame(
        columns={
            "uptake": [
                16, 30.4, 34.8, 37.2, 35.3, 39.2, 39.7, 13.6, 27.3, 37.1, 41.8, 40.6, 41.4, 44.3,
                16.2, 32.4, 40.3, 42.1, 42.9, 43.9, 45.5, 14.2, 24.1, 30.3, 34.6, 32.5, 35.4, 38.7,
                9.3, 27.3, 35, 38.8, 38.6, 37.5, 42.4, 15.1, 21, 38.1, 34, 38.9, 39.6, 41.4, 10.6,
                19.2, 26.2, 30, 30.9, 32.4, 35.5, 12, 22, 30.6, 31.8, 32.4, 31.1, 31.5, 11.3, 19.4,
                25.8, 27.9, 28.5, 28.1, 27.8, 10.5, 14.9, 18.1, 18.9, 19.5, 22.2, 21.9, 7.7, 11.4,
                12.3, 13, 12.5, 13.7, 14.4, 10.6, 18, 17.9, 17.9, 17.9, 18.9, 19.9,
            ],
            "conc": [95, 175, 250, 350, 500, 675, 1000] * 12,
            "Plant": (
                ["Qn1"] * 7
                + ["Qn2"] * 7
                + ["Qn3"] * 7
                + ["Qc1"] * 7
                + ["Qc2"] * 7
                + ["Qc3"] * 7
                + ["Mn1"] * 7
                + ["Mn2"] * 7
                + ["Mn3"] * 7
                + ["Mc1"] * 7
                + ["Mc2"] * 7
                + ["Mc3"] * 7
            ),
        },
        group_levels=(
            "Qn1", "Qn2", "Qn3", "Qc1", "Qc3", "Qc2", "Mn3", "Mn2", "Mn1", "Mc2", "Mc3", "Mc1"
        ),
    )


def one():
    data = co2()
    fm1 = nlsList_formula(
        "uptake ~ SSasympOff(conc, Asym, lrc, c0) | Plant",
        data=data,
        start={"Asym": 30, "lrc": -4.5, "c0": 52},
    )
    table = coef(fm1)
    return np.ravel(table.values, order="F")


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
