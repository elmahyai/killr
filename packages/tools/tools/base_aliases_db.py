"""Rd alias metadata for base packages shipped with R."""

from __future__ import annotations

from tools.rd_help import base_rd_metadata_db


def base_aliases_db(verbose: bool = False, ncpus: int = 1) -> dict[str, dict[str, list[str]]]:
    """Return Rd aliases in base packages as a nested per-package named mapping."""
    return base_rd_metadata_db("alias", verbose=verbose, ncpus=int(ncpus))
