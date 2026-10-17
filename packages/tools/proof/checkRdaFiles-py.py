import statistics
import time

def one():
    from tools.rda import check_rda_files
    rows = check_rda_files([
        "/home/ahmed/killr_projects/killr/packages/tools/proof/tiny.rda",
        "/tmp/no-such-tools-file.rda",
    ])

    def show(row):
        def cell(value):
            if value is None:
                return "NA"
            if value is True:
                return "TRUE"
            if value is False:
                return "FALSE"
            return str(value)
        return " ".join(cell(row[name]) for name in ("size", "ASCII", "compress", "version"))

    return show(rows[0]) + "\n" + show(rows[1]) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
