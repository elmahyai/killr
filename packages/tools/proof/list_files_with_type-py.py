import statistics
import time

def one():
    import os, tempfile
    directory = tempfile.mkdtemp()
    def put(name, text):
        path = os.path.join(directory, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    put("a.R", "z\n")
    put("b.r", "y\n")
    put("notes.txt", "n\n")
    put(".hidden.R", "h\n")
    put("1demo.R", "d\n")
    put("unix/os.R", "o\n")
    import os
    from tools.paths import list_files_with_type
    code = "|".join(os.path.basename(path) for path in list_files_with_type(directory, "code"))
    demo = "|".join(os.path.basename(path) for path in list_files_with_type(directory, "demo", full_names=False))
    return code + "\n" + demo + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
