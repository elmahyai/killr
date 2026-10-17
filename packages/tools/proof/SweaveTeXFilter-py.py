import statistics
import time

def one():
    import tempfile
    from pathlib import Path
    from tools.sweave import sweave_tex_filter
    path = Path(tempfile.mkdtemp()) / "demo.Rnw"
    path.write_text("Some text\n<<>>=\ncode line\n@\nmore text\n")
    return "|".join(sweave_tex_filter(path)) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
