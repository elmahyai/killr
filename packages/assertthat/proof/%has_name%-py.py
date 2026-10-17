import statistics
import time

def show(res):
    if res is True or getattr(res, "value", None) is True:
        return "TRUE\n"
    if isinstance(res, str):
        return res + "\n"
    return res.msg + "\n"

def one():
    from assertthat import see_if
    y = {"a": 1, "b": 2}
    return show(see_if('y %has_name% "c"')) + show(see_if('y %has_name% c("a", "g", "f")'))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
