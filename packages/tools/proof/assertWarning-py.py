import statistics
import time

def one():
    import warnings
    from tools.conditions import assert_warning
    w = assert_warning(lambda: warnings.warn("w"), expr_string='warning("w")')
    try:
        assert_warning(lambda: (_ for _ in ()).throw(RuntimeError("x")), expr_string='stop("x")')
        err = ""
    except ValueError as exc:
        err = str(exc)

    def both():
        warnings.warn("w")
        raise RuntimeError("e")

    try:
        assert_warning(both, expr_string='{warning("w"); stop("e")}')
        both_msg = ""
    except ValueError as exc:
        both_msg = str(exc)
    return w[0]["message"] + "\n" + err + "\n" + both_msg + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
