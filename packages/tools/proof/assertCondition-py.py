import statistics
import time

def one():
    import io
    import contextlib
    from tools.conditions import assert_condition
    try:
        assert_condition(lambda: None, "error", expr_string="1 + 1")
        fail = ""
    except ValueError as exc:
        fail = str(exc)
    ok = assert_condition(lambda: (_ for _ in ()).throw(RuntimeError("boom")), "error", expr_string='stop("boom")')
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert_condition(lambda: (_ for _ in ()).throw(RuntimeError("e")), "error", expr_string='stop("e")', verbose=True)
    return fail + "\n" + ok[0]["message"] + "\n" + buf.getvalue()

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
