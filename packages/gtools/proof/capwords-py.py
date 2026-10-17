import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.capwords import capwords


def one():
    return [
        capwords("a function to capitalize words in a title"),
        capwords("a function to capitalize words in a title", AP=False),
        capwords("testing the iProduct for defects"),
        capwords("testing the iProduct for defects", strict=True),
        capwords("testing the iProduct for defects", onlyfirst=True),
        capwords("testing the iProduct for defects", preserveMixed=True),
        capwords("title_using_underscores_as_separators", sep="_"),
        capwords(""),
        capwords("AND"),
        capwords("a  b"),
        capwords("word With MixedCase Inside"),
        capwords("word With MixedCase Inside", preserveMixed=True),
        capwords("to be Or not To Be", AP=False),
        capwords("to be Or not To Be"),
        capwords("single"),
        capwords("iPhone starts mixed", preserveMixed=True),
        capwords("iPhone starts mixed", preserveMixed=False),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
