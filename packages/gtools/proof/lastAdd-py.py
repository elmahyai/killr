import importlib.util
import io
import json
import statistics
import sys
import time
from contextlib import redirect_stdout

_PATH = "/home/ahmed/killr_projects/killr/packages/gtools/gtools/last_add.py"
_spec = importlib.util.spec_from_file_location("gtools_last_add", _PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
lastAdd = _mod.lastAdd
global_env = _mod.global_env


def one():
    global_env.clear()
    logs = []

    def bye():
        logs.append("bye")
        return 1

    def hello():
        logs.append("hello")
        return 2

    def early():
        logs.append("early")
        return 3

    parts = []
    f0 = lastAdd(bye)
    parts.append("SAME" if f0 is bye else "DIFF")
    parts.append(str(f0()))

    global_env[".Last"] = bye
    f1 = lastAdd(hello)
    parts.append("SAME" if f1 is hello else "WRAP")
    parts.append(str(f1(9)))

    def other():
        logs.append("other")
        return 9

    global_env[".Last"] = other
    parts.append(str(f1()))

    global_env[".Last"] = f1
    f2 = lastAdd(early)
    parts.append(str(f2()))

    global_env[".Last"] = 5
    parts.append("NUM_SAME" if lastAdd(hello) is hello else "NUM_WRAP")
    global_env[".Last"] = None
    parts.append("NULL_SAME" if lastAdd(hello) is hello else "NULL_WRAP")
    global_env[".Last"] = [hello]
    parts.append("LIST_SAME" if lastAdd(hello) is hello else "LIST_WRAP")

    global_env.clear()

    def local_case():
        _Last = lambda: 99
        return lastAdd(hello) is hello and _Last() == 99

    parts.append("LOCAL_IGNORED" if local_case() else "LOCAL_SEEN")

    hit = {"n": 0}

    def bad():
        raise RuntimeError("boom")

    def good():
        hit["n"] += 1
        return 4

    global_env[".Last"] = good
    try:
        lastAdd(bad)()
        err = ""
    except RuntimeError as exc:
        err = str(exc)
    parts.append(err)
    parts.append(str(hit["n"]))

    def message(value):
        try:
            lastAdd(value)
        except ValueError as exc:
            return str(exc)
        return ""

    parts.append(message(1))
    parts.append(message(None))
    parts.append(message("x"))
    parts.append(message([hello]))

    global_env.clear()

    def hello_world():
        sys.stdout.write("\nHello World!\n")

    def bye_world():
        sys.stdout.write("\nGoodbye World!\n")

    global_env[".Last"] = lastAdd(bye_world)
    global_env[".Last"] = lastAdd(hello_world)
    buf = io.StringIO()
    with redirect_stdout(buf):
        ex_val = global_env[".Last"]()
    printed = buf.getvalue()
    parts.append("NULL" if ex_val is None else str(ex_val))
    parts.append(printed)
    parts.append(",".join(logs))
    global_env.clear()
    return "|".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
