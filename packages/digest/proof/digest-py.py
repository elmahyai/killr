import statistics
import time

from digest import character, data_frame, digest, integer_matrix

obj = [
    character(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    data_frame(
        a=character(list("abcde")),
        b=integer_matrix(list(range(1, 11)), ncol=2),
    ),
]


def one():
    return digest(obj)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
