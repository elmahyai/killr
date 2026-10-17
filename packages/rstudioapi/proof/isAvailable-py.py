import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rstudioapi.is_available import isAvailable


def line(name, fn):
    try:
        value = fn()
    except Exception as exc:
        text = "ERR " + str(exc)
    else:
        if value is True:
            text = "TRUE"
        elif value is False:
            text = "FALSE"
        else:
            text = "OTHER " + repr(value)
    return name + "=" + text


def _restore(name, previous):
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


def one():
    saved = {
        name: os.environ.get(name)
        for name in (
            "RSTUDIO_WORKBENCH_JOB",
            "RSTUDIOAPI_IPC_REQUESTS_FILE",
            "RSTUDIOAPI_IPC_RESPONSE_FILE",
            "RSTUDIOAPI_IPC_SHARED_SECRET",
            "RSTUDIO",
        )
    }
    try:
        for name in saved:
            os.environ.pop(name, None)
        parts = [
            line("default", isAvailable),
            line("version", lambda: isAvailable(version_needed="2024.04.2")),
            line("child", lambda: isAvailable(child_ok=True)),
            line(
                "both",
                lambda: isAvailable(version_needed="0.99.0", child_ok=False),
            ),
            line("null", lambda: isAvailable(child_ok=None)),
            line("string", lambda: isAvailable(child_ok="TRUE")),
            line("len2", lambda: isAvailable(child_ok=(True, False))),
            line("zero", lambda: isAvailable(child_ok=0)),
            line("one", lambda: isAvailable(child_ok=1)),
            line("nan", lambda: isAvailable(child_ok=float("nan"))),
            line("empty", lambda: isAvailable(child_ok=())),
            line("zeroi", lambda: isAvailable(child_ok=0j)),
            line("onei", lambda: isAvailable(child_ok=1j)),
        ]
        os.environ["RSTUDIO"] = "1"
        parts.append(line("rstudio-env", isAvailable))
        parts.append(line("rstudio-env-child", lambda: isAvailable(child_ok=True)))
        os.environ.pop("RSTUDIO", None)
        os.environ["RSTUDIO_WORKBENCH_JOB"] = "1"
        parts.extend(
            [
                line("wb-default", isAvailable),
                line("wb-child", lambda: isAvailable(child_ok=True)),
                line(
                    "wb-version",
                    lambda: isAvailable(version_needed="99.0", child_ok=True),
                ),
                line("wb-na", lambda: isAvailable(child_ok=float("nan"))),
                line("wb-zeroi", lambda: isAvailable(child_ok=0j)),
                line("wb-onei", lambda: isAvailable(child_ok=1j)),
            ]
        )
        os.environ.pop("RSTUDIO_WORKBENCH_JOB", None)
        os.environ["RSTUDIOAPI_IPC_REQUESTS_FILE"] = ""
        parts.append(line("ipc-child", lambda: isAvailable(child_ok=True)))
        parts.append(line("ipc-false", lambda: isAvailable(child_ok=False)))
        return "\n".join(parts)
    finally:
        for name, previous in saved.items():
            _restore(name, previous)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
