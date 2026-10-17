import statistics
import time

def one():
    from tools.file_ext import NA_character_
    from tools.paths import file_path_sans_ext
    def show(value):
        return "|".join("NA" if item.__class__.__name__ == "NA" else item for item in value)
    x = ["file.zip", "file.tar.gz", ".hidden", "file.", "file.c++", "a.é", "a..txt", "foo/bar.txt.bak", NA_character_]
    return show(file_path_sans_ext(x)) + "\n" + show(file_path_sans_ext(x, True)) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
