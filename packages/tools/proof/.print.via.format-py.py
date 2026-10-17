import statistics
import time

def one():
    import contextlib, io
    from tools.options import print_via_format
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_via_format(["a", "b"])
    return buf.getvalue()

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
