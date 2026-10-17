import statistics
import time

def show(res):
    if res is True or getattr(res, "value", None) is True:
        return "TRUE\n"
    if isinstance(res, str):
        return res + "\n"
    return res.msg + "\n"

def one():
    from assertthat import validate_that
    x = 1
    parts = [
        show(validate_that("is.numeric(x)")),
        show(validate_that("is.character(x)")),
        show(validate_that("length(x) == 3")),
        show(validate_that('is.dir("asdf")')),
        show(validate_that("FALSE", msg="Custom message")),
        show(validate_that('5 == "i"')),
        show(validate_that("any(c(FALSE, FALSE))")),
    ]
    x = [False, True]
    parts.append(show(validate_that("all(x)")))
    return "".join(parts)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
