import statistics
import sys
import time

from crayon import options as crayon_options

crayon_options(**{"crayon.enabled": True})
from diffobj.diff import diffCsv

def one():
    import tempfile
    from pathlib import Path
    folder = Path(tempfile.mkdtemp())
    target = folder / "t.csv"
    current = folder / "c.csv"
    target.write_text("a,b\n1,x\n2,y\n")
    current.write_text("a,b\n1,x\n2,z\n")
    diff = diffCsv(str(target), str(current), format="raw", pager="off", tar_banner="t", cur_banner="c")
    return "\n".join(diff.lines)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
text = value if isinstance(value, str) else "\n".join(value)
sys.stdout.write("VALUE\n")
sys.stdout.write(text)
sys.stdout.write("\n<<<END>>>\n")
sys.stdout.write(f"MS {statistics.median(elapsed):.17g}\n")
