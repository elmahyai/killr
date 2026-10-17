import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nlme.nlslist import nlsList  # noqa: E402
from nlme.nlslistformula import coef as nls_coef  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "data"


class GroupedFrame:
    """Column dict plus the group level order, as ``groupedData`` supplies it."""

    def __init__(self, columns, group_levels):
        self.columns = columns
        self.group_levels = group_levels


def load_frame():
    with open(DATA_DIR / "nlsList-loblolly.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    columns = {
        "Seed": [row["Seed"] for row in rows],
        "age": [float(row["age"]) for row in rows],
        "height": [float(row["height"]) for row in rows],
    }
    levels = (DATA_DIR / "nlsList-levels.txt").read_text(encoding="utf-8").split()
    return GroupedFrame(columns, tuple(levels))


def names_fp(names):
    names = list(names)
    out = [float(len(names))]
    for text in names:
        codes = [ord(ch) for ch in text]
        out.append(float(len(text)))
        out.append(float(sum(code * (index + 1) for index, code in enumerate(codes))))
    return out


FORMULA = "height ~ SSasympOff(age, Asym, lrc, c0) | Seed"
START = {"Asym": 100.0, "lrc": -1.5, "c0": 0.0}
FRAME = load_frame()


def fit_matrix():
    fit = nlsList(FORMULA, FRAME, start=START)
    return nls_coef(fit)


def one():
    cf = fit_matrix()
    values = np.asarray(cf.values, dtype=np.float64)
    out = list(values.ravel(order="F"))
    out.extend(names_fp(cf.rownames))
    out.extend(names_fp(cf.colnames))
    return np.asarray(out, dtype=np.float64)


def example():
    cf = fit_matrix()
    lines = [
        f"groups: {len(cf.rownames)}",
        f"coefficients: {' '.join(cf.colnames)}",
    ]
    for index, name in enumerate(cf.rownames):
        row = " ".join(f"{float(value):.10g}" for value in cf.values[index])
        lines.append(f"{name}: {row}")
    return lines


out_dir = ROOT / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "nlsList-python.txt").write_text("\n".join(example()) + "\n", encoding="utf-8")

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
