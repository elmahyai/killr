import statistics
import time

def one():
    from tools.file_ext import NA_character_
    from tools.textutil import to_title_case
    x = ["the quick brown fox", "a tale of two cities", "HTML and LaTeX", NA_character_, "john's book", "foo-bar: baz", '"hello" world']
    parts = ["NA" if item.__class__.__name__ == "NA" else item for item in to_title_case(x)]
    return "|".join(parts) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
