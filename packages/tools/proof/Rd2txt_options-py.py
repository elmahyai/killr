import statistics
import time

def one():
    from tools.options import rd2txt_options
    o = rd2txt_options()
    flags = " ".join(str(o[name]).upper() if isinstance(o[name], bool) else str(o[name]) for name in ("width", "minIndent", "extraIndent", "sectionIndent", "sectionExtra", "showURLs", "code_quote", "underline_titles"))
    return flags + " " + o["itemBullet"] + o["enumFormat"](3) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
