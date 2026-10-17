import statistics
import time

from rlang import RLangError, env
from rlang.eval_bare import eval_bare
from rlang.is_call import is_call
from rlang.parse_expr import parse_expr


def one():
    ex1 = parse_expr(["1 + 2 *", "3"])
    ex2 = parse_expr("foo(bar)")
    v1 = eval_bare(ex1, env())
    try:
        parse_expr("1; 2")
        err = ""
    except RLangError as exc:
        err = str(exc)
    if isinstance(v1, float) and v1 == int(v1):
        v1_text = str(int(v1))
    else:
        v1_text = str(v1)
    return "|".join(
        [
            v1_text,
            "TRUE" if is_call(ex2, "foo") else "FALSE",
            err,
        ]
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
