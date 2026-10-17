import statistics
import time

from digest.vdigest import getVDigest

letters = list("abcdefghijklmnopqrstuvwxyz")
sha1 = getVDigest(algo="sha1")


def one():
    return sha1(letters)


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append(time.perf_counter() - t0)
print("%.17g" % (statistics.median(elapsed) * 1000))
print("\n".join(value))
