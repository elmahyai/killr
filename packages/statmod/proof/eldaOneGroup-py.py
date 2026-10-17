import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.elda_one_group import elda_one_group


def collect(out):
    if "p" not in out:
        return np.concatenate(
            [
                np.asarray(out["CI.frequency"], dtype=float).reshape(-1),
                np.array(
                    [
                        out["deviance"],
                        out["dloglik.logdose"],
                        out["FisherInfo.logdose"],
                        out["dloglik.dose"],
                        out["FisherInfo.dose"],
                    ],
                    dtype=float,
                ),
            ]
        )
    return np.concatenate(
        [
            np.asarray(out["p"], dtype=float).reshape(-1),
            np.array([out["lambda"], out["alpha"]], dtype=float),
            np.asarray(out["CI.alpha"], dtype=float).reshape(-1),
            np.asarray(out["CI.frequency"], dtype=float).reshape(-1),
            np.array(
                [
                    out["deviance"],
                    float(out["iter"]),
                    out["z.scoretest"],
                    out["z.scoretest.dose"],
                    out["dloglik.logdose"],
                    out["FisherInfo.logdose"],
                    out["dloglik.dose"],
                    out["FisherInfo.dose"],
                ],
                dtype=float,
            ),
        ]
    )


def one():
    dose = np.array([50, 100, 200, 400, 800], dtype=float)
    responses = np.array([2, 6, 9, 15, 21], dtype=float)
    tested = np.array([24, 24, 24, 24, 24], dtype=float)
    return np.concatenate(
        [
            collect(elda_one_group(responses, dose, tested)),
            collect(
                elda_one_group(
                    np.array([0, 0, 0, 0], dtype=float),
                    np.array([50, 100, 200, 400], dtype=float),
                    np.array([10, 10, 10, 10], dtype=float),
                )
            ),
            collect(
                elda_one_group(
                    np.array([10, 10, 10, 10], dtype=float),
                    np.array([50, 100, 200, 400], dtype=float),
                    np.array([10, 10, 10, 10], dtype=float),
                )
            ),
            collect(elda_one_group(responses, dose, tested, observed=True)),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
