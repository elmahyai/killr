import statistics
import time

def one():
    import contextlib
    import io
    import tempfile
    from pathlib import Path
    from tools.rdiff import rdiff
    directory = Path(tempfile.mkdtemp(prefix="rdiff"))
    a = directory / "a.txt"
    b = directory / "b.txt"
    c = directory / "c.txt"
    d = directory / "d.txt"
    e = directory / "e.txt"
    f = directory / "f.txt"
    a.write_text("alpha\nbeta  \ngamma\n")
    b.write_text("alpha\nbeta\ngamma\n")
    c.write_text("alpha\nBETA\ngamma\n")
    d.write_text("only\n")
    e.write_text("see <environment: 0xabc> and <hashtable 1>\n\u2018q\u2019\n")
    f.write_text("see <environment: 0> and <hashtable output>\n'q'\n")
    same = rdiff(a, b)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        diff_status = rdiff(a, c)
    diff_lines = buf.getvalue().splitlines()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        len_status = rdiff(a, d)
    len_msg = buf.getvalue().strip()
    ptr = rdiff(e, f)
    return (
        f"SAME {same}\n"
        f"DIFF\n" + "\n".join(diff_lines) + f"\n{diff_status}\n"
        f"LEN {len_msg} {len_status}\n"
        f"PTR {ptr}\n"
    )

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
