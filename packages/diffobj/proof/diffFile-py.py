import statistics
import sys
import time

from crayon import options as crayon_options

crayon_options(**{"crayon.enabled": True})
from diffobj.diff import diffFile

def one():
    import tempfile
    from pathlib import Path
    folder = Path(tempfile.mkdtemp())
    target = folder / "t"
    current = folder / "c"
    target.write_text("a\nb\nc\n")
    current.write_text("a\nB\nc\n")
    diff = diffFile(target, current, format="raw", pager="off", tar_banner="t", cur_banner="c")
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
