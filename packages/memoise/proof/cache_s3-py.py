
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ready = Path(tempfile.mktemp(prefix="s3ready"))
subprocess.Popen(
    [sys.executable, "-m", "memoise._s3mock", str(ready)],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
for _ in range(100):
    if ready.exists() and ready.stat().st_size:
        break
    time.sleep(0.05)
info = json.loads(ready.read_text())
os.environ["AWS_S3_ENDPOINT"] = f"127.0.0.1:{info['port']}"
os.environ["SSL_CERT_FILE"] = info["cert"]
os.environ["CURL_CA_BUNDLE"] = info["cert"]

from memoise import cache_s3

def one():
    name = f"bkt{os.urandom(4).hex()}"
    store = cache_s3(name)
    store.set("abc", 4)
    got = store.get("abc")
    has = store.has_key("abc")
    nkeys = len(store.keys())
    store.drop_key("abc")
    has2 = store.has_key("abc")
    return [got, int(has), nkeys, int(has2)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
