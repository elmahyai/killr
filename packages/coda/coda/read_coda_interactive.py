"""Read CODA output files interactively."""

from __future__ import annotations

import sys
from pathlib import Path

from coda.mcmc_list import mcmc_list
from coda.read_coda import read_coda


def read_coda_interactive():
    """Prompt for CODA index and output files (``read.coda.interactive``)."""
    while True:
        print("Enter CODA index file name")
        print("(or a blank line to exit)")
        index_file = _read_line()
        if index_file == "":
            return None
        print("Enter CODA output file names, separated by return key")
        print("(leave a blank line when you have finished)")
        output_files = []
        while True:
            line = _read_line()
            if line == "":
                break
            output_files.append(line)
        all_files = [index_file, *output_files]
        missing = [path for path in all_files if not Path(path).exists()]
        if missing:
            print("The following files were not found:")
            print("\n".join(missing))
            print()
            continue
        break
    chains = [read_coda(output_files[i], index_file) for i in range(len(output_files))]
    return mcmc_list(*chains)


def _read_line():
    line = sys.stdin.readline()
    if line == "":
        return ""
    return line.strip()
