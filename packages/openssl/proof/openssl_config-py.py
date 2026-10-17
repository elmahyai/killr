from openssl import openssl_config

def one():
    cfg = openssl_config()
    flags = ["TRUE" if cfg[name] else "FALSE" for name in ("ec", "x25519", "fips")]
    return cfg["version"] + "|" + "|".join(flags)

import statistics
import time
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
else:
    shown = str(value)
print("VALUE " + shown.replace("\n", " / "))
print(f"MS {statistics.median(elapsed):.17g}")
