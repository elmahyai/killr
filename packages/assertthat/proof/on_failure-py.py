import statistics
import time

def show(res):
    if res is True or getattr(res, "value", None) is True:
        return "TRUE\n"
    if isinstance(res, str):
        return res + "\n"
    return res.msg + "\n"

def one():
    from assertthat import on_failure, see_if
    from assertthat.expr import render
    def is_red(x):
        return x == "red"
    def fail(call, env):
        return render(call["x"]) + " is not red"
    on_failure(is_red, fail)
    return show(see_if('is_red("blue")', env={"is_red": is_red}))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
