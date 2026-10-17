"""Time bkde against R and record whether the results match.

Writes the ``check`` object on the translated ``bkde`` entry in translation.json.
"""

from __future__ import annotations

import json
import shutil
import statistics
import subprocess
import textwrap
import time
from pathlib import Path

import numpy as np

from kernsmooth import bkde, bkfe, dpih, dpik, locpoly

ROOT = Path(__file__).resolve().parent
RECORD = ROOT / "translation.json"
CASE = "10,000 standard normal points, normal kernel, gridsize 401"
REPEATS = 20
TOLERANCE = 1e-8


def main() -> None:
    sample = np.random.default_rng(0).normal(size=10_000)
    bkde(sample)
    translated = []
    for _ in range(REPEATS):
        started = time.perf_counter()
        bkde(sample)
        translated.append((time.perf_counter() - started) * 1000.0)
    translated_ms = statistics.median(translated)

    r_ms = None
    matches = None
    max_abs_diff = None
    reference = _r_check(sample)
    if reference is not None:
        r_ms = reference["r_ms"]
        estimate = bkde(sample)
        max_abs_diff = float(
            max(
                np.max(np.abs(estimate["x"] - reference["x"])),
                np.max(np.abs(estimate["y"] - reference["y"])),
            )
        )
        matches = max_abs_diff <= TOLERANCE

    record = json.loads(RECORD.read_text())
    check = {
        "case": CASE,
        "r_ms": r_ms,
        "translated_ms": translated_ms,
        "speedup": None if r_ms is None else r_ms / translated_ms,
        "matches": matches,
        "max_abs_diff": max_abs_diff,
        "tolerance": TOLERANCE,
    }
    for function in record["functions"]:
        if function["name"] == "bkde":
            function["check"] = check
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(check, indent=2))


def _r_check(sample: np.ndarray):
    if shutil.which("Rscript") is None:
        return None
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        one <- function() KernSmooth::bkde(x)
        invisible(one())
        elapsed <- numeric(20)
        for (i in seq_len(20)) {
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }
        est <- one()
        cat(sprintf("%.17g\\n", median(elapsed) * 1000))
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$x), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$y), sep="")
        """
    )
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        data = root / "x.txt"
        program = root / "bench.R"
        np.savetxt(data, sample, fmt="%.17g")
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(data)],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    timing, grid, density = result.stdout.split("---")
    return {
        "r_ms": float(timing.strip()),
        "x": np.fromstring(grid, sep="\n"),
        "y": np.fromstring(density, sep="\n"),
    }


def record_bkfe() -> None:
    """Time bkfe on the geyser example and record its check."""
    from mass import geyser

    sample = np.asarray(geyser["duration"], dtype=np.float64)
    bkfe(sample, drv=4, bandwidth=0.3)
    translated = []
    for _ in range(REPEATS):
        started = time.perf_counter()
        bkfe(sample, drv=4, bandwidth=0.3)
        translated.append((time.perf_counter() - started) * 1000.0)
    translated_ms = statistics.median(translated)

    r_ms = None
    matches = None
    max_abs_diff = None
    reference = _r_bkfe_check()
    if reference is not None:
        r_ms = reference["r_ms"]
        estimate = bkfe(sample, drv=4, bandwidth=0.3)
        max_abs_diff = abs(estimate - reference["value"])
        matches = max_abs_diff <= TOLERANCE

    record = json.loads(RECORD.read_text())
    check = {
        "case": "geyser duration, drv=4, bandwidth=0.3",
        "r_ms": r_ms,
        "translated_ms": translated_ms,
        "speedup": None if r_ms is None else r_ms / translated_ms,
        "matches": matches,
        "max_abs_diff": max_abs_diff,
        "tolerance": TOLERANCE,
    }
    for function in record["functions"]:
        if function["name"] == "bkfe":
            function["check"] = check
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(check, indent=2))


def _r_bkfe_check():
    if shutil.which("Rscript") is None:
        return None
    script = textwrap.dedent(
        """
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        if (!requireNamespace("MASS", quietly=TRUE)) quit(status=2)
        data(geyser, package="MASS")
        x <- geyser$duration
        one <- function() KernSmooth::bkfe(x, drv=4, bandwidth=0.3)
        invisible(one())
        elapsed <- numeric(20)
        for (i in seq_len(20)) {
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }
        cat(sprintf("%.17g\\n", median(elapsed) * 1000))
        cat("---\\n")
        cat(sprintf("%.17g\\n", one()))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    timing, value = result.stdout.split("---")
    return {"r_ms": float(timing.strip()), "value": float(value.strip())}


def record_dpik() -> None:
    """Time dpik on the geyser example and record its check."""
    from mass import geyser

    sample = np.asarray(geyser["duration"], dtype=np.float64)
    dpik(sample)
    translated = []
    for _ in range(REPEATS):
        started = time.perf_counter()
        dpik(sample)
        translated.append((time.perf_counter() - started) * 1000.0)
    translated_ms = statistics.median(translated)

    r_ms = None
    matches = None
    max_abs_diff = None
    reference = _r_dpik_check()
    if reference is not None:
        r_ms = reference["r_ms"]
        estimate = dpik(sample)
        max_abs_diff = abs(estimate - reference["value"])
        matches = max_abs_diff <= TOLERANCE

    record = json.loads(RECORD.read_text())
    check = {
        "case": "geyser duration, default plug-in bandwidth",
        "r_ms": r_ms,
        "translated_ms": translated_ms,
        "speedup": None if r_ms is None else r_ms / translated_ms,
        "matches": matches,
        "max_abs_diff": max_abs_diff,
        "tolerance": TOLERANCE,
    }
    for function in record["functions"]:
        if function["name"] == "dpik":
            function["check"] = check
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(check, indent=2))


def _r_dpik_check():
    if shutil.which("Rscript") is None:
        return None
    script = textwrap.dedent(
        """
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        if (!requireNamespace("MASS", quietly=TRUE)) quit(status=2)
        data(geyser, package="MASS")
        x <- geyser$duration
        one <- function() KernSmooth::dpik(x)
        invisible(one())
        elapsed <- numeric(20)
        for (i in seq_len(20)) {
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }
        cat(sprintf("%.17g\\n", median(elapsed) * 1000))
        cat("---\\n")
        cat(sprintf("%.17g\\n", one()))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    timing, value = result.stdout.split("---")
    return {"r_ms": float(timing.strip()), "value": float(value.strip())}


def record_dpih() -> None:
    """Time dpih on the geyser example and record its check."""
    from mass import geyser

    sample = np.asarray(geyser["duration"], dtype=np.float64)
    dpih(sample)
    translated = []
    for _ in range(REPEATS):
        started = time.perf_counter()
        dpih(sample)
        translated.append((time.perf_counter() - started) * 1000.0)
    translated_ms = statistics.median(translated)

    r_ms = None
    matches = None
    max_abs_diff = None
    reference = _r_dpih_check()
    if reference is not None:
        r_ms = reference["r_ms"]
        estimate = dpih(sample)
        max_abs_diff = abs(estimate - reference["value"])
        matches = max_abs_diff <= TOLERANCE

    record = json.loads(RECORD.read_text())
    check = {
        "case": "geyser duration, default histogram bin width",
        "r_ms": r_ms,
        "translated_ms": translated_ms,
        "speedup": None if r_ms is None else r_ms / translated_ms,
        "matches": matches,
        "max_abs_diff": max_abs_diff,
        "tolerance": TOLERANCE,
    }
    for function in record["functions"]:
        if function["name"] == "dpih":
            function["check"] = check
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(check, indent=2))


def _r_dpih_check():
    if shutil.which("Rscript") is None:
        return None
    script = textwrap.dedent(
        """
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        if (!requireNamespace("MASS", quietly=TRUE)) quit(status=2)
        data(geyser, package="MASS")
        x <- geyser$duration
        one <- function() KernSmooth::dpih(x)
        invisible(one())
        elapsed <- numeric(20)
        for (i in seq_len(20)) {
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }
        cat(sprintf("%.17g\\n", median(elapsed) * 1000))
        cat("---\\n")
        cat(sprintf("%.17g\\n", one()))
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    timing, value = result.stdout.split("---")
    return {"r_ms": float(timing.strip()), "value": float(value.strip())}


def record_locpoly() -> None:
    """Time the locpoly density example and record its check."""
    from mass import geyser

    sample = np.asarray(geyser["duration"], dtype=np.float64)
    locpoly(sample, bandwidth=0.25)
    translated = []
    for _ in range(REPEATS):
        started = time.perf_counter()
        locpoly(sample, bandwidth=0.25)
        translated.append((time.perf_counter() - started) * 1000.0)
    translated_ms = statistics.median(translated)

    r_ms = None
    matches = None
    max_abs_diff = None
    reference = _r_locpoly_check()
    if reference is not None:
        r_ms = reference["r_ms"]
        estimate = locpoly(sample, bandwidth=0.25)
        max_abs_diff = float(
            max(
                np.max(np.abs(estimate["x"] - reference["x"])),
                np.max(np.abs(estimate["y"] - reference["y"])),
            )
        )
        matches = max_abs_diff <= TOLERANCE

    record = json.loads(RECORD.read_text())
    check = {
        "case": "geyser duration, bandwidth 0.25, density",
        "r_ms": r_ms,
        "translated_ms": translated_ms,
        "speedup": None if r_ms is None else r_ms / translated_ms,
        "matches": matches,
        "max_abs_diff": max_abs_diff,
        "tolerance": TOLERANCE,
    }
    for function in record["functions"]:
        if function["name"] == "locpoly":
            function["check"] = check
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(check, indent=2))


def _r_locpoly_check():
    if shutil.which("Rscript") is None:
        return None
    script = textwrap.dedent(
        """
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        if (!requireNamespace("MASS", quietly=TRUE)) quit(status=2)
        data(geyser, package="MASS")
        x <- geyser$duration
        one <- function() KernSmooth::locpoly(x, bandwidth=0.25)
        invisible(one())
        elapsed <- numeric(20)
        for (i in seq_len(20)) {
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }
        est <- one()
        cat(sprintf("%.17g\\n", median(elapsed) * 1000))
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$x), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$y), sep="")
        """
    )
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    timing, grid, curve = result.stdout.split("---")
    return {
        "r_ms": float(timing.strip()),
        "x": np.fromstring(grid, sep="\n"),
        "y": np.fromstring(curve, sep="\n"),
    }


if __name__ == "__main__":
    main()
    record_bkfe()
    record_dpik()
    record_dpih()
    record_locpoly()
