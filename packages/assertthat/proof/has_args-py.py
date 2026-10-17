import statistics
import time
from assertthat import has_args
from assertthat.base import mean, rnorm

def one():
    return [has_args(mean, "x"), has_args(mean, "x", exact=True), has_args(mean, "y"), has_args(rnorm, "n"), has_args(rnorm, ["n", "mean"]), has_args(rnorm, ["mean", "sd", "n"]), has_args(rnorm, "n", exact=True), has_args(rnorm, ["n", "mean"], exact=True), has_args(rnorm, ["mean", "sd", "n"], exact=True)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
