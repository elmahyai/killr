import statistics
import time

def one():
    import tempfile
    from tools.checksum import sha256sum
    path = tempfile.mktemp()
    with open(path, "wb") as handle:
        handle.write(b"z\n")
    digest = next(iter(sha256sum(path).values()))
    return sha256sum(bytes=b"abc") + "\n" + digest + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
