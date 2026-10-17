import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Formula.as_formula import as_Formula
from Formula.formula import Formula, as_r_formula, fingerprint
from Formula.is_formula import FormulaError

f1 = as_r_formula("y ~ x1 + x2")
f2 = as_r_formula("~ z1 + z2 + z3")
f3 = as_r_formula("y ~ x1 | x2")
f4 = as_r_formula("y1 | y2 ~ x")
f5 = as_r_formula("~ z")
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
        lambda: as_Formula(F1),
        lambda: as_Formula(f1),
        lambda: as_Formula(f1, f2),
        lambda: as_Formula("y ~ x"),
        lambda: as_Formula(f3),
        lambda: as_Formula(f4, f5),
        lambda: as_Formula(1),
        lambda: as_Formula(f1, f1),
        lambda: as_Formula(f1, foo=1),
        lambda: as_Formula(),
        lambda: as_Formula(1, 2),
    ]
    parts = [line(fn) for fn in calls]
    ident = "TRUE" if as_Formula(F1) is F1 else "FALSE"
    parts.append("ID " + ident)
    return " || ".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
out = Path(__file__).resolve().parent / "as.Formula-py-out.txt"
out.write_text(
    "VALUE " + value + "\n" + f"MS {statistics.median(elapsed):.17g}\n",
    encoding="utf-8",
)
