import json
import statistics
import tempfile
import time
from withr import (libpaths, local_environment, local_namespace, local_package,
                   local_libpaths, local_temp_libpaths, lookup, search,
                   with_environment, with_namespace, with_package,
                   with_libpaths, with_temp_libpaths)

def one(name):
    before = search()
    if name in {"local_environment", "with_environment"}:
        if name == "local_environment":
            with local_environment({"value": 42}, name="withr-proof-env"):
                inside = lookup("value")
        else:
            inside = with_environment({"value": 42}, lambda: lookup("value"), name="withr-proof-env")
        return [float(inside), float("withr-proof-env" not in search())]
    if name in {"local_package", "with_package"}:
        if name == "local_package":
            with local_package("compiler"):
                inside = "package:compiler" in search()
        else:
            inside = with_package("compiler", lambda: "package:compiler" in search())
        return [float(inside), float(search() == before)]
    if name in {"local_namespace", "with_namespace"}:
        ns = "<environment: namespace:stats>"
        if name == "local_namespace":
            with local_namespace("stats"):
                inside = ns in search()
        else:
            inside = with_namespace("stats", lambda: ns in search())
        return [float(inside), float(search() == before)]
    before = libpaths()
    path = tempfile.mkdtemp(prefix="withr-proof-lib-")
    if name in {"local_libpaths", "with_libpaths"}:
        if name == "local_libpaths":
            with local_libpaths(path):
                inside = libpaths()[0]
        else:
            inside = with_libpaths(path, lambda: libpaths()[0])
        return [float(inside == path), float(libpaths() == before)]
    if name in {"local_temp_libpaths", "with_temp_libpaths"}:
        if name == "local_temp_libpaths":
            with local_temp_libpaths():
                inside = libpaths()[1:] == before
        else:
            inside = with_temp_libpaths(lambda: libpaths()[1:] == before)
        return [float(inside), float(libpaths() == before)]
    raise ValueError(name)

def run(name):
    value = one(name)
    elapsed = []
    for _ in range(20):
        t0 = time.perf_counter()
        one(name)
        elapsed.append((time.perf_counter() - t0) * 1000)
    print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
