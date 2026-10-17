import statistics
import time

from rlang import Env
from rlang.is_formula import Lang, is_formula


def _formula(rhs, lhs=None, env=None):
    env = Env() if env is None else env
    if lhs is None:
        return Lang("~", rhs, env=env, classes=("formula",))
    return Lang("~", lhs, rhs, env=env, classes=("formula",))


def one():
    quoted = Lang("~", "foo")
    return ",".join(
        "TRUE" if item else "FALSE"
        for item in (
            is_formula(_formula(10)),
            is_formula(10),
            is_formula(quoted),
            is_formula(quoted, scoped=True),
            is_formula(_formula("foo"), lhs=False),
            is_formula(Lang("~", "foo", "bar"), lhs=True),
            is_formula(Lang("~", "foo", "bar"), lhs=False),
        )
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
