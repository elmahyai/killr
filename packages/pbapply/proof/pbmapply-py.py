import json
import statistics
import time

from pbapply.pbmapply import pbmapply
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none")
    try:
        return [
            *list(
                pbmapply(
                    lambda x, y: x + y,
                    [1, 2, 3],
                    [4, 5, 6],
                )
            ),
            *list(
                pbmapply(
                    lambda x, y, z: x * y * z,
                    [1, 2, 3, 4],
                    2,
                    MoreArgs={"z": 3},
                )
            ),
            *[
                float(len(s))
                for s in pbmapply(
                    lambda a, b: f"{a} {b}",
                    ["a", "b"],
                    ["1", "2"],
                    SIMPLIFY=False,
                )
            ],
        ]
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": value,
            "median_ms": statistics.median(elapsed),
        }
    )
)
