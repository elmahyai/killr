import csv
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
from nlme.plot_lme import plot_lme_values  # noqa: E402

DATA = PACKAGE / "proof" / "data"
OUTPUT = PACKAGE / "docs" / "output"

# The fitted values and Pearson residuals come from R's lme fit (see
# proof/data/make-plot-lme-fixture.R), because lme is not translated yet.
with open(DATA / "plot-lme-orthodont.csv", newline="") as handle:
    rows = list(csv.DictReader(handle))
FITTED = [float(row["fitted"]) for row in rows]
PEARSON = [float(row["pearson"]) for row in rows]
GROUP = [row["group"] for row in rows]
with open(DATA / "plot-lme-orthodont.json") as handle:
    LABELS = json.load(handle)


def one():
    result = plot_lme_values(
        FITTED,
        PEARSON,
        xlab=LABELS["xlab"],
        ylab=LABELS["ylab"],
        groups=GROUP,
        abline=(0.0, 0.0),
    )
    result["fig"].canvas.draw()
    plt.close(result["fig"])
    return result


def one_id():
    result = plot_lme_values(
        FITTED,
        PEARSON,
        xlab=LABELS["xlab"],
        ylab=LABELS["ylab"],
        groups=GROUP,
        id=0.05,
        abline=(0.0, 0.0),
    )
    result["fig"].canvas.draw()
    plt.close(result["fig"])
    return result


default = one()
labelled = one_id()
value = list(default["x"]) + list(default["y"]) + list(default["abline"])
value_id = [float(i) for i in labelled["id_index"]]

for name, call in (("plot.lme-python.svg", None), ("plot.lme-id-python.svg", 0.05)):
    kwargs = {"id": call} if call is not None else {}
    result = plot_lme_values(
        FITTED,
        PEARSON,
        xlab=LABELS["xlab"],
        ylab=LABELS["ylab"],
        groups=GROUP,
        abline=(0.0, 0.0),
        **kwargs,
    )
    result["fig"].set_size_inches(7, 7)
    result["fig"].savefig(OUTPUT / name, format="svg")
    plt.close(result["fig"])

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(
    json.dumps(
        {
            "value": value,
            "value_id": value_id,
            "id_labels": labelled["id_labels"],
            "labels": {"xlab": default["xlab"], "ylab": default["ylab"]},
            "panels": default["panels"],
            "median_ms": statistics.median(elapsed),
        }
    )
)
