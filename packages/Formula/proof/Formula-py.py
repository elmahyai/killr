import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Formula.formula import Formula, as_r_formula, fingerprint
from Formula.is_formula import FormulaError

f1 = as_r_formula("y ~ x1 + x2 | z1 + z2 + z3")
f2 = as_r_formula("y1 | y2 + y3 ~ x1 + I(x2^2) | 0 + log(x1) | x3 / x4")
f3 = as_r_formula("~ x + y")
f4 = as_r_formula("y1 | y2 ~ x")
f5 = as_r_formula("y ~ a | b | c")
f6 = as_r_formula("y1 + y2 | y3 ~ x")
f7 = as_r_formula("y ~ x")

F1 = Formula(f1)


def line(fn):
    try:
        val = fn()
    except FormulaError as exc:
        return "ERR " + str(exc)
    if hasattr(val, "classes"):
        return fingerprint(val)
    return "OTHER|" + str(val)


def one():
    calls = [
        lambda: Formula(f1),
        lambda: Formula(f2),
        lambda: Formula(f3),
        lambda: Formula(f4),
        lambda: Formula(f5),
        lambda: Formula(f6),
        lambda: Formula(f7),
        lambda: Formula(F1),
        lambda: Formula(1),
        lambda: Formula("y ~ x"),
    ]
    parts = [line(fn) for fn in calls]
    ident = "TRUE" if Formula(F1) is F1 else "FALSE"
    parts.append("ID " + ident)
    return " || ".join(parts)


def identical(a, b):
    return a is b


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
