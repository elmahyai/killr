import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Formula.formula import Formula, as_r_formula
from Formula.is_formula import FormulaError
from Formula.model_part import RFrame, fingerprint_part, model_part

MF2 = RFrame(
    {
        "y1": [0.69999999999999996, 0.65000000000000002],
        "y2": ["a", "b"],
        "x3": ["b", "a"],
    },
    row_names=[2, 3],
)
MF1 = RFrame(
    {
        "log(y1)": [-0.19845093872383832, -0.35667494393873245, -0.43078291609245423],
        "x1": [0.089999999999999997, 0.26000000000000001, 0.029999999999999999],
        "x2": [0.22, 0.46000000000000002, 0.37],
        "I(x1^2)": [0.0080999999999999996, 0.067600000000000007, 0.00089999999999999998],
    },
    row_names=[1, 2, 3],
)
MF3 = RFrame(
    {
        "y1": [0.69999999999999996, 0.65000000000000002],
        "y2": ["a", "b"],
        "log(y3)": [-1.7719568419318752, -1.2729656758128873],
        "x1": [0.26000000000000001, 0.029999999999999999],
        "I(x2^2)": [0.21160000000000001, 0.13689999999999999],
        "log(x1)": [-1.3470736479666092, -3.5065578973199818],
        "x3": ["b", "a"],
        "x4": ["b", "a"],
        "(weights)": [0.26000000000000001, 0.029999999999999999],
    },
    row_names=[2, 3],
)

DAT = RFrame(
    {
        "y1": [0.81999999999999995, 0.69999999999999996, 0.65000000000000002],
        "y2": [None, "a", "b"],
        "y3": [0.27000000000000002, 0.17000000000000001, 0.28000000000000003],
        "x1": [0.089999999999999997, 0.26000000000000001, 0.029999999999999999],
        "x2": [0.22, 0.46000000000000002, 0.37],
        "x3": ["a", "b", "a"],
        "x4": ["b", "b", "a"],
    },
    row_names=[1, 2, 3],
)

F1 = Formula(as_r_formula("log(y1) ~ x1 + x2 | I(x1^2)"))
F2 = Formula(as_r_formula("y1 + y2 ~ x3"))
F3 = Formula(
    as_r_formula("y1 + y2 | log(y3) ~ x1 + I(x2^2) | 0 + log(x1) | x3 / x4")
)
def line(fn):
    try:
        val = fn()
    except FormulaError as exc:
        return "ERR " + str(exc)
    return fingerprint_part(val)


def one():
    calls = [
        lambda: model_part(F2, data=MF2, lhs=1),
        lambda: model_part(F1, data=MF1, lhs=1, drop=True),
        lambda: model_part(F3, data=MF3, lhs=1),
        lambda: model_part(F3, data=MF3, lhs=2),
        lambda: model_part(F1, data=MF1, rhs=1),
        lambda: model_part(F1, data=MF1, rhs=2),
        lambda: model_part(as_r_formula("y1 + y2 ~ x3"), data=MF2, lhs=1),
        lambda: model_part(F1, data=MF1, lhs=0, rhs=0),
        lambda: model_part(F1, data=DAT, lhs=1),
    ]
    return " || ".join(line(fn) for fn in calls)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
out = Path(__file__).resolve().parent / "model.part-py-out.txt"
out.write_text(
    "VALUE " + value + "\n" + f"MS {statistics.median(elapsed):.17g}\n",
    encoding="utf-8",
)
