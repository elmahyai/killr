"""Read OpenBUGS CODA output into an MCMC list.

Translated from coda 0.19-4.1 ``read.openbugs`` in ``R/output.R``.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from coda.mcmc_list import mcmc_list
from coda.read_coda import read_coda


def read_openbugs(stem="", start=None, end=None, thin=None, quiet=False):
    """Read OpenBUGS ``CODAindex.txt`` and ``CODAchain*.txt`` files under ``stem``."""
    prefix = str(stem)
    index_file = Path(f"{prefix}CODAindex.txt")
    if not index_file.is_file():
        raise ValueError("No index file found")

    index_date = index_file.stat().st_ctime
    nchain = 0
    while True:
        output_file = Path(f"{prefix}CODAchain{nchain + 1}.txt")
        if output_file.is_file():
            nchain += 1
            output_date = output_file.stat().st_ctime
            delta_minutes = abs(index_date - output_date) / 60.0
            if delta_minutes > 1.0:
                warnings.warn(
                    f'Files "{index_file}" and "{output_file}" were created at different times\n',
                    RuntimeWarning,
                    stacklevel=2,
                )
        else:
            break

    if nchain == 0:
        raise ValueError("No output files found")

    chains = []
    for i in range(1, nchain + 1):
        output_file = Path(f"{prefix}CODAchain{i}.txt")
        chains.append(
            read_coda(output_file, index_file, start=start, end=end, thin=thin, quiet=quiet)
        )
    return mcmc_list(*chains)
