import json
import statistics
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
from nlme.lme_family import lme  # noqa: E402
from nlme.plot_lme import plot_lme  # noqa: E402

OUTPUT = PACKAGE / "docs" / "output"

# Orthodont as nlme ships it: distance ~ age grouped by Subject, with the units
# that R's plot.lme puts on the axes.
DISTANCE = [
    26, 25, 29, 31, 21.5, 22.5, 23, 26.5, 23, 22.5, 24, 27.5, 25.5, 27.5, 26.5, 27,
    20, 23.5, 22.5, 26, 24.5, 25.5, 27, 28.5, 22, 22, 24.5, 26.5, 24, 21.5, 24.5, 25.5,
    23, 20.5, 31, 26, 27.5, 28, 31, 31.5, 23, 23, 23.5, 25, 21.5, 23.5, 24, 28, 17,
    24.5, 26, 29.5, 22.5, 25.5, 25.5, 26, 23, 24.5, 26, 30, 22, 21.5, 23.5, 25, 21, 20,
    21.5, 23, 21, 21.5, 24, 25.5, 20.5, 24, 24.5, 26, 23.5, 24.5, 25, 26.5, 21.5, 23,
    22.5, 23.5, 20, 21, 21, 22.5, 21.5, 22.5, 23, 25, 23, 23, 23.5, 24, 20, 21, 22,
    21.5, 16.5, 19, 19, 19.5, 24.5, 25, 28, 28,
]
SUBJECTS = [f"M{i:02d}" for i in range(1, 17)] + [f"F{i:02d}" for i in range(1, 12)]
LEVELS = (
    "M16", "M05", "M02", "M11", "M07", "M08", "M03", "M12", "M13", "M14", "M09",
    "M15", "M06", "M04", "M01", "M10", "F10", "F09", "F06", "F01", "F05", "F07",
    "F02", "F08", "F03", "F04", "F11",
)


class Orthodont:
    classes = ("groupedData", "data.frame")
    formula = "distance ~ age | Subject"
    attributes = {"units": {"x": "(yr)", "y": "(mm)"}, "labels": {"x": "Age"}}

    def __init__(self):
        self.columns = {
            "distance": DISTANCE,
            "age": [8, 10, 12, 14] * 27,
            "Subject": [name for name in SUBJECTS for _ in range(4)],
        }
        self.group_levels = LEVELS


def one():
    fit = lme("distance ~ age", data=Orthodont(), control={"apVar": False})
    result = plot_lme(fit)
    result["fig"].canvas.draw()
    plt.close(result["fig"])
    return result


def one_id():
    fit = lme("distance ~ age", data=Orthodont(), control={"apVar": False})
    result = plot_lme(fit, id=0.05)
    result["fig"].canvas.draw()
    plt.close(result["fig"])
    return result


default = one()
labelled = one_id()
value = list(default["x"]) + list(default["y"]) + list(default["abline"])
value_id = [float(i) for i in labelled["id_index"]]

for name, ident in (("plot.lme-python.svg", None), ("plot.lme-id-python.svg", 0.05)):
    fit = lme("distance ~ age", data=Orthodont(), control={"apVar": False})
    kwargs = {"id": ident} if ident is not None else {}
    result = plot_lme(fit, **kwargs)
    result["fig"].set_size_inches(7, 7)
    result["fig"].savefig(OUTPUT / name, format="svg")
    plt.close(result["fig"])

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

fit = lme("distance ~ age", data=Orthodont(), control={"apVar": False})
print(
    json.dumps(
        {
            "value": value,
            "value_id": value_id,
            "id_labels": labelled["id_labels"],
            "labels": {"xlab": default["xlab"], "ylab": default["ylab"]},
            "panels": default["panels"],
            "fitted": [float(v) for v in fit.fitted[:, -1]],
            "pearson": [float(v) for v in fit.residuals[:, -1] / fit.sigma],
            "group": [str(v) for v in fit.groups[fit.coefficients_random_names[-1]]],
            "median_ms": statistics.median(elapsed),
        }
    )
)
