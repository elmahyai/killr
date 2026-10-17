import statistics
import time

def show(res):
    if res is True or getattr(res, "value", None) is True:
        return "TRUE\n"
    if isinstance(res, str):
        return res + "\n"
    return res.msg + "\n"

def one():
    from assertthat import AssertThatError, assert_that
    def message(expr):
        try:
            assert_that(expr)
        except AssertThatError as error:
            return error.args[0]
        return "NOERROR"
    ok = "TRUE" if assert_that("is.numeric(1)") else "FALSE"
    short = message("5 < 4")
    long = message("isTRUE(10 + sqrt(25) + sum(1:10) + sqrt(25) + sum(11:20) + sqrt(25) + sum(21:30) + sqrt(25) + sum(31:40) + sqrt(25) + sum(41:50))")
    return ok + "\n" + short + "\n" + long + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
