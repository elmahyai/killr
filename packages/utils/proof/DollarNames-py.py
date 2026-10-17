import statistics
import time

from utils.dollar_names import DollarNames, REnvironment


def one():
    env = REnvironment(foo=1, bar=2, _hidden={".hidden": 3})
    return ",".join(sorted(DollarNames(env, "")))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
