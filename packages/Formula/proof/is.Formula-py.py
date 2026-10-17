import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Formula.is_formula import FormulaError, RClassed, is_Formula

CHILD = ("ChildF", "Formula", "numeric", "vector")
FORMULA_EXT = ("Formula", "numeric", "vector")
OTHER = ("Other", "numeric", "vector")

fml = RClassed(classes=("Formula", "formula"))
plain = RClassed(classes=("formula",))
s3_formula = RClassed(classes=("Formula",))
s3_lower = RClassed(classes=("formula",))
s3_second = RClassed(classes=("foo", "Formula"))
s3_first = RClassed(classes=("Formula", "formula"))
s3_child = RClassed(classes=("ChildF",), extends=CHILD)
s4_child = RClassed(classes=("ChildF",), s4=True, extends=CHILD)
s4_formula = RClassed(classes=("Formula",), s4=True, extends=FORMULA_EXT)
s4_other = RClassed(classes=("Other",), s4=True, extends=OTHER)
s4_primary = RClassed(classes=("Formula",), s4=True)
s4_second = RClassed(classes=("foo", "Formula"), s4=True)
na_s3 = RClassed(classes=(None, "Formula"))
na_s4 = RClassed(classes=(None, "Formula"), s4=True)
only_na = RClassed(classes=(None,))
form_na = RClassed(classes=("Formula", None))
form_na_s4 = RClassed(classes=("Formula", None), s4=True)
env_f = RClassed(classes=("Formula",))
bare = RClassed(classes=("call",))
spaced = RClassed(classes=("Formula ",))
empty_cl = RClassed(classes=("",))
fn_f = RClassed(classes=("Formula",))
prepended = RClassed(classes=("bar", "Formula", "formula"))
matrix_v = RClassed(classes=("matrix", "array"))
factor_v = RClassed(classes=("factor",))
asis = RClassed(classes=("AsIs",))
frame = RClassed(classes=("data.frame",))
na_logical = RClassed(classes=("logical",))
nan_v = RClassed(classes=("numeric",))


def line(fn):
    try:
        val = fn()
    except FormulaError as exc:
        return "ERR " + str(exc)
    if val is True:
        return "TRUE"
    if val is False:
        return "FALSE"
    return "OTHER"


def one():
    calls = [
        lambda: is_Formula(fml),
        lambda: is_Formula(plain),
        lambda: is_Formula(None),
        lambda: is_Formula(1),
        lambda: is_Formula(1),
        lambda: is_Formula(True),
        lambda: is_Formula("Formula"),
        lambda: is_Formula([]),
        lambda: is_Formula([]),
        lambda: is_Formula(s3_formula),
        lambda: is_Formula(s3_lower),
        lambda: is_Formula(s3_second),
        lambda: is_Formula(s3_first),
        lambda: is_Formula(s3_child),
        lambda: is_Formula(s4_child),
        lambda: is_Formula(s4_formula),
        lambda: is_Formula(s4_other),
        lambda: is_Formula(s4_primary),
        lambda: is_Formula(s4_second),
        lambda: is_Formula(na_s3),
        lambda: is_Formula(na_s4),
        lambda: is_Formula(only_na),
        lambda: is_Formula(form_na),
        lambda: is_Formula(form_na_s4),
        lambda: is_Formula(env_f),
        lambda: is_Formula(bare),
        lambda: is_Formula(spaced),
        lambda: is_Formula(empty_cl),
        lambda: is_Formula(fn_f),
        lambda: is_Formula(prepended),
        lambda: is_Formula(matrix_v),
        lambda: is_Formula(factor_v),
        lambda: is_Formula(asis),
        lambda: is_Formula(frame),
        lambda: is_Formula(na_logical),
        lambda: is_Formula(nan_v),
        lambda: is_Formula(object=None),
        lambda: is_Formula(ob=s3_formula),
        lambda: is_Formula(o=1),
        lambda: is_Formula(),
        lambda: is_Formula(1, 2),
        lambda: is_Formula(1, 2, 3),
        lambda: is_Formula(1, foo=2),
        lambda: is_Formula(1, foo=2, bar=3),
        lambda: is_Formula(object=s3_formula, o=1, ob=2),
        lambda: is_Formula(o=1, ob=2),
        lambda: is_Formula(1, o=2),
        lambda: is_Formula(Object=1),
        lambda: is_Formula(2, object=s3_formula),
    ]
    return " | ".join(line(fn) for fn in calls)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
