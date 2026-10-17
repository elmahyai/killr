import statistics
import time

from openssl.bcrypt_pbkdf import bcrypt_pbkdf


def one():
    key = bcrypt_pbkdf("test-password", bytes(range(1, 17)), 16, 32)
    return ",".join(str(b) for b in key)


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
