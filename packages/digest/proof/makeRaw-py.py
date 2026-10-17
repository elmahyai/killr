import statistics
import time

from digest.makeraw import makeRaw


def one():
    return makeRaw("1234567890ABCDE")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join(str(byte) for byte in value))
print("%.17g" % statistics.median(elapsed))
