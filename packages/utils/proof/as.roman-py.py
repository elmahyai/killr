import statistics
import time

from utils.as_roman import as_roman


def one():
    a = as_roman([0, 1, 4, 3899, None])
    b = as_roman(["I", "IV", "MMMDCCCXCIX", "foo", "MMXVI"])
    return "\n".join(
        [
            str(a).replace(" ", ","),
            str(b).replace(" ", ","),
            str(as_roman(["IV", "V"]) + as_roman(["V", "X"])).replace(" ", ","),
            str(as_roman(["IV", "V"]) * 2).replace(" ", ","),
            str(as_roman(["IV", "V"]) - 1).replace(" ", ","),
            ",".join(
                "TRUE" if value else "FALSE"
                for value in (as_roman(["IV", "V"]) == as_roman(["IV", "X"]))
            ),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
