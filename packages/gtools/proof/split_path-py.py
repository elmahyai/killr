import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.split_path import split_path


def vec_json(parts):
    out = []
    for part in parts:
        if part is None:
            out.append(None)
        else:
            out.append(part)
    return out


def one():
    return [
        vec_json(split_path("/home/user/file.txt")),
        vec_json(split_path("/home/user/file.txt", depth_first=False)),
        vec_json(split_path("/home/user/")),
        vec_json(split_path("/home/user/", depth_first=False)),
        vec_json(split_path("file.txt")),
        vec_json(split_path("./file.txt")),
        vec_json(split_path("../file.txt")),
        vec_json(split_path("../file.txt", depth_first=False)),
        vec_json(split_path("/")),
        vec_json(split_path("a/b/c")),
        vec_json(split_path("a/b/c", depth_first=False)),
        vec_json(split_path("a")),
        vec_json(split_path("")),
        vec_json(split_path("/a//b/c")),
        vec_json(split_path("relative/path/here")),
        vec_json(split_path("C:/Users/file")),
        vec_json(split_path(None)),
        vec_json(split_path(".", depth_first=False)),
        vec_json(split_path("..")),
    ]


split_path("/home/user/file.txt")
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
