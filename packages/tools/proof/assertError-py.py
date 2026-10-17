import statistics
import time

def one():
    from tools.conditions import assert_error
    try:
        assert_error(lambda: None, expr_string="1 + 1")
        fail = ""
    except ValueError as exc:
        fail = str(exc)
    ok = assert_error(lambda: (_ for _ in ()).throw(RuntimeError("boom")), expr_string='stop("boom")')
    return fail + "\n" + ok[0]["message"] + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
