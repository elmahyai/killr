import math
import statistics
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.plot import plot_zoo
from zoo.series import Zoo


def fmt_one(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    number = float(value)
    if math.isnan(number):
        return "NA"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return format(number, ".16g")


def fmt_vec(value):
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, np.ndarray)):
        return "|".join(fmt_one(item) for item in np.asarray(value).reshape(-1))
    return fmt_one(value)


def emit_series(name, result):
    lines = [f"CASE {name}", f"mode={result['mode']}", f"nser={result['nser']}"]
    if result["mode"] == "multiple":
        lines.append(f"ngraph={result['ngraph']}")
        lines.append(f"nr={result['nr']}")
        for number, panel in enumerate(result["panels"], start=1):
            lines.append(f"PANEL {number}")
            lines.append("ylim=" + fmt_vec(panel["ylim"]))
            for series in panel["series"]:
                lines.extend(
                    [
                        f"series={series['series']}",
                        f"within={series['within']}",
                        "type=" + fmt_vec(series["type"]),
                        "lty=" + fmt_vec(series["lty"]),
                        "lwd=" + fmt_vec(series["lwd"]),
                        "col=" + fmt_vec(series["col"]),
                        "pch=" + fmt_vec(series["pch"]),
                        "x=" + fmt_vec(series["x"]),
                        "y=" + fmt_vec(series["y"]),
                    ]
                )
    else:
        lines.append("ylim=" + fmt_vec(result["ylim"]))
        for series in result["series"]:
            lines.extend(
                [
                    f"series={series['series']}",
                    "type=" + fmt_vec(series["type"]),
                    "lty=" + fmt_vec(series["lty"]),
                    "lwd=" + fmt_vec(series["lwd"]),
                    "col=" + fmt_vec(series["col"]),
                    "pch=" + fmt_vec(series["pch"]),
                    "x=" + fmt_vec(series["x"]),
                    "y=" + fmt_vec(series["y"]),
                ]
            )
    return "\n".join(lines)


def emit_scatter(name, result):
    labels = result["labels"]
    return "\n".join(
        [
            f"CASE {name}",
            "x=" + fmt_vec(result["x"]),
            "y=" + fmt_vec(result["y"]),
            "ptype=" + str(result["ptype"]),
            "lines=" + ("1" if result["lines"] else "0"),
            "linetype=" + ("" if not result["linetype"] else str(result["linetype"])),
            "labels=" + ("" if not labels else "|".join(str(item) for item in labels)),
            "xlim=" + fmt_vec(result["xlim"]),
            "ylim=" + fmt_vec(result["ylim"]),
            "col=" + fmt_vec(result["col"]),
            "pch=" + fmt_vec(result["pch"]),
            "lty=" + fmt_vec(result["lty"]),
            "lwd=" + fmt_vec(result["lwd"]),
        ]
    )


def one():
    data = np.array(
        [
            [1, 2, 0],
            [3, 2, 1],
            [2, 4, np.nan],
            [5, 3, 2],
            [4, 6, 3],
        ],
        dtype=float,
    )
    series = Zoo(data, [1, 2, 3, 4, 5])
    series.colnames = ["A", "B", "C"]
    single = Zoo(np.array([1, np.nan, 3, 4], dtype=float), [10, 20, 30, 40])
    left = Zoo(np.array([1, 2, np.nan, 4], dtype=float), [1, 2, 3, 4])
    right = Zoo(np.array([10, 20, 30, 40], dtype=float), [1, 2, 3, 5])
    parts = [
        emit_series("default-multiple", plot_zoo(series, draw=False)),
        emit_series("screens-one", plot_zoo(series, screens=1, col={"B": 2}, draw=False)),
        emit_series(
            "type-b",
            plot_zoo(
                series,
                type="b",
                pch=[("A", [1, 2, 3, 4, 5]), ("B", 3)],
                col=[("C", 4), ("", 2)],
                draw=False,
            ),
        ),
        emit_series(
            "screens-ylim",
            plot_zoo(
                series,
                screens=[2, 1, 2],
                ylim=[[0, 10], [-1, 1], None],
                lty=[2, 3],
                lwd=[1, 4],
                draw=False,
            ),
        ),
        emit_series(
            "multiple-screens-one",
            plot_zoo(series, plot_type="multiple", screens=1, draw=False),
        ),
        emit_series("screens-range", plot_zoo(series, screens=1, ylim=[0, 1, 5], draw=False)),
        emit_series("reversed", plot_zoo(series, screens=1, ylim=[10, 0], draw=False)),
        emit_series("univariate", plot_zoo(single, type="o", col=2, lwd=3, pch=19, draw=False)),
        emit_series("points", plot_zoo(single, type="p", pch=19, col=4, draw=False)),
        emit_scatter("scatter", plot_zoo(left, right, draw=False)),
        emit_scatter("scatter-labels", plot_zoo(left, right, xy_labels=True, draw=False)),
        emit_scatter(
            "scatter-text",
            plot_zoo(left, right, xy_labels=["a", "b", "c"], xy_lines=False, draw=False),
        ),
        emit_scatter("scatter-b", plot_zoo(left, right, type="b", draw=False)),
    ]
    return "\n\n".join(parts)


value = one()
out = "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/plot.zoo-python.txt"
with open(out, "w", encoding="utf-8") as handle:
    handle.write(value + "\n")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
chart = Zoo(
    np.array(
        [
            [1, 2, 0],
            [3, 2, 1],
            [2, 4, np.nan],
            [5, 3, 2],
            [4, 6, 3],
        ],
        dtype=float,
    ),
    [1, 2, 3, 4, 5],
)
chart.colnames = ["A", "B", "C"]
figure = plot_zoo(
    chart,
    type="b",
    pch=[("A", [1, 2, 3, 4, 5]), ("B", 3)],
    col=[("C", 4), ("", 2)],
    xname="z",
    draw=True,
)
figure["figure"].savefig(
    "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/plot.zoo-python.svg",
    format="svg",
)
plt.close(figure["figure"])
print("%.17g" % statistics.median(elapsed))
