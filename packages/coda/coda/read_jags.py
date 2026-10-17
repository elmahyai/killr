"""Read JAGS CODA output into an MCMC object.

Translated from coda 0.19-4.1 ``read.jags`` in ``R/output.R``.
"""

from __future__ import annotations

from pathlib import Path

from coda.read_coda import read_coda


def read_jags(
    file: str | Path = "jags.out",
    start=None,
    end=None,
    thin=None,
    quiet: bool = False,
):
    """Read a JAGS ``*.out`` file and companion ``*.ind`` index via ``read_coda``."""
    path = str(file)
    nc = len(path)
    if nc > 3 and path[nc - 4 :] == ".out":
        root = path[: nc - 4]
    else:
        root = path
    index_file = f"{root}.ind"
    return read_coda(path, index_file, start=start, end=end, thin=thin, quiet=quiet)
