import statistics
import sys
import time

from minqa import newuoa


def fr(x):
    return 100 * (x[1] - x[0] ** 2) ** 2 + (1 - x[0]) ** 2


def one():
    return newuoa([1, 2], fr)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
sys.stdout.write("VALUE\n")
sys.stdout.write(f"{value.par[0]:.17g}\n{value.par[1]:.17g}\n{value.fval:.17g}\n")
sys.stdout.write(f"{value.feval}\n{value.ierr}\n{value.msg}\n")
sys.stdout.write("<<<END>>>\n")
sys.stdout.write(f"MS {statistics.median(elapsed):.17g}\n")
