import statistics
import time

from digest.hmac import hmac


def one():
    return hmac("Jefe", "what do ya want for nothing?", "md5")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
