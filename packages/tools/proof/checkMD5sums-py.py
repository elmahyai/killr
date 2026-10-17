import statistics
import time

def one():
    import contextlib, hashlib, io, os, tempfile
    from tools.checkmd5 import check_md5sums
    directory = tempfile.mkdtemp()
    target = os.path.join(directory, "a.txt")
    with open(target, "wb") as handle:
        handle.write(b"hello\n")
    digest = hashlib.md5(b"hello\n").hexdigest()
    with open(os.path.join(directory, "MD5"), "w", encoding="utf-8") as handle:
        handle.write(digest + "  a.txt\nabc  missing.txt\n")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = check_md5sums(directory=directory)
    shown = "NA" if res is None else ("TRUE" if res else "FALSE")
    return shown + " || " + buf.getvalue().strip().replace("\n", "|") + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
