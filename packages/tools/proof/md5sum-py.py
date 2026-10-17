import statistics
import time

def one():
    import os, tempfile
    from tools.checksum import md5sum
    from tools.file_ext import NA
    path = tempfile.mktemp()
    with open(path, "wb") as handle:
        handle.write(b"z\n")
    miss = tempfile.mktemp()
    try:
        md5sum(files=path, bytes=b"abc")
        both = "NOERROR"
    except ValueError as error:
        both = str(error)
    try:
        md5sum(bytes="abc")
        rawerr = "NOERROR"
    except ValueError as error:
        rawerr = str(error)
    digest = next(iter(md5sum(path).values()))
    missing = next(iter(md5sum(miss).values()))
    missing = "NA" if isinstance(missing, NA) else missing
    return md5sum(bytes=b"abc") + "\n" + digest + "\n" + missing + "\n" + both + "\n" + rawerr + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
