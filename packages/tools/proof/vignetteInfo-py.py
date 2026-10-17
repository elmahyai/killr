import statistics
import time

def one():
    import tempfile
    from pathlib import Path
    from tools.vignette import vignette_info
    directory = Path(tempfile.mkdtemp(prefix="vig"))
    (directory / "demo.Rnw").write_text(
        "% \\VignetteIndexEntry{A Title}\n"
        "% \\VignetteDepends{foo, bar}\n"
        "% \\VignetteKeywords{one, two}\n"
        "% \\VignetteEngine{knitr::knitr}\n"
    )
    (directory / "empty.Rnw").write_text("nothing\n")
    a = vignette_info(directory / "demo.Rnw")
    b = vignette_info(directory / "empty.Rnw")
    return (
        f"VIG {a['file']} {a['title']} {','.join(a['depends'])} {','.join(a['keywords'])} {a['engine']}\n"
        f"VIG0 {b['title']} {','.join(b['depends'])} {','.join(b['keywords'])} {b['engine']}\n"
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
