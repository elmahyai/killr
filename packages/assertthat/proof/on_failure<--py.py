import statistics
import time

def show(res):
    if res is True or getattr(res, "value", None) is True:
        return "TRUE\n"
    if isinstance(res, str):
        return res + "\n"
    return res.msg + "\n"

def one():
    from assertthat import assert_that, is_number, see_if, set_on_failure
    from assertthat.expr import render
    def is_odd(x):
        assert_that(is_number(x))
        return x % 2 == 1
    before = show(see_if("is_odd(2)", env={"is_odd": is_odd}))
    def fail(call, env):
        return render(call["x"]) + " is even"
    set_on_failure(is_odd, fail)
    after = show(see_if("is_odd(2)", env={"is_odd": is_odd}))
    return before + after

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
