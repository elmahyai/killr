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
    parts = []
    x = 1
    parts.append(show(see_if("is.character(x)")))
    parts.append(show(see_if("length(x) == 3")))
    parts.append(show(see_if('is.scalar("a")')))
    parts.append(show(see_if("is.string(1:3)")))
    parts.append(show(see_if("is.dir(17)")))
    parts.append(show(see_if('is.dir("asdf")')))
    parts.append(show(see_if("5 < 3", msg="Five is not smaller than three")))
    parts.append(show(see_if("noNA(c(TRUE, NA))")))
    x = 2
    parts.append(show(see_if("are_equal(x, 1.9)")))
    parts.append(show(see_if("are_equal(x, 1.999, tol = 0.01)")))
    parts.append(show(see_if("any(c(FALSE, FALSE))")))
    parts.append(show(see_if("5 != 5")))
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
