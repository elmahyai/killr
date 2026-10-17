import statistics
import time

from rlang import env
from rlang.as_label import Call
from rlang.as_string import Symbol
from rlang.eval_bare import eval_bare


def one():
    expr = Call(Symbol("+"), Symbol("a"), Call(Symbol("*"), Symbol("b"), Symbol("c")))
    return eval_bare(expr, env(a=1.5, b=2, c=3))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
elif value is None:
    shown = "NULL"
else:
    shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
