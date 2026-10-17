import statistics
import time

def one():
    import contextlib, io
    from tools.textutil import show_non_ascii
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        res = show_non_ascii(["plain", "café", "ok"])
    return err.getvalue().strip().replace("\n", "|") + " || " + "|".join(res) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
