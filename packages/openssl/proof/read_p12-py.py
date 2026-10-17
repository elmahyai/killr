import statistics
import time

from openssl.fingerprint import fingerprint
from openssl.read_p12 import read_p12

FIXTURE = "/home/ahmed/killr_projects/killr/packages/openssl/proof/fixtures/example-elliptic-sha1.p12"


def one():
    bundle = read_p12(FIXTURE, password="password")
    return fingerprint(bundle["key"].raw)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
elif value is None:
    shown = "NULL"
else:
    shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
