"""Helpers for the interactive CODA menu driver."""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from coda.as_mcmc import Mcmc, as_mcmc, is_mcmc
from coda.as_mcmc_list import McmcList, as_mcmc_list, is_mcmc_list
from coda.coda_options import coda_options
from coda.nchain import nchain
from coda.niter import niter
from coda.nvar import nvar
from coda.varnames import varnames
from coda.chanames import chanames


def menu(choices, title=None):
    """Read a numbered menu choice from stdin (``utils::menu``)."""
    if title:
        sys.stdout.write(f"{title}\n")
    for index, label in enumerate(choices, start=1):
        sys.stdout.write(f"{index}: {label}\n")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if line == "":
        return 0
    line = line.strip()
    if line == "":
        return 0
    try:
        pick = int(line)
    except ValueError:
        return 0
    if pick < 0 or pick > len(choices):
        return 0
    return pick


def read_yesno(string, default=True):
    """Ask a yes/no question on stdin."""
    word = " (Y/n)?\n:" if default else " (y/N)?\n:"
    sys.stdout.write(f"\n{string}{word}")
    sys.stdout.flush()
    ans = sys.stdin.readline()
    if ans.endswith("\n"):
        ans = ans[:-1]
    lower = ans.lower()
    if default:
        return lower not in ("no", "n")
    return lower in ("yes", "y")


def change_tfoption(string, option):
    """Toggle a logical coda option after confirmation."""
    current = coda_options(option)
    if not isinstance(current, (bool, np.bool_)):
        raise ValueError("Invalid option: must take logical values")
    new_value = read_yesno(string, bool(current))
    if new_value != current:
        coda_options(**{option: new_value})
    return None


def gelman_transform(x):
    """Log or logit transform for Gelman diagnostic (``gelman.transform``)."""
    obj = as_mcmc_list(x) if is_mcmc(x) else x
    if not is_mcmc_list(obj):
        return obj
    out_chains = []
    n_var = nvar(obj)
    n_ch = nchain(obj)
    for chain in obj.chains:
        matrix = np.asarray(_chain_matrix(chain), dtype=np.float64)
        out_chains.append(matrix.copy())
    if n_var == 1:
        z = np.column_stack([out_chains[j][:, 0] for j in range(n_ch)])
        if np.min(z) > 0:
            y = np.log(z / (1 - z)) if np.max(z) < 1 else np.log(z)
            for j in range(n_ch):
                out_chains[j][:, 0] = y[:, j]
    else:
        for i in range(n_var):
            z = np.column_stack([out_chains[j][:, i] for j in range(n_ch)])
            if np.min(z) > 0:
                y = np.log(z / (1 - z)) if np.max(z) < 1 else np.log(z)
                for j in range(n_ch):
                    out_chains[j][:, i] = y[:, j]
    rebuilt = []
    for chain, matrix in zip(obj.chains, out_chains):
        rebuilt.append(
            Mcmc(
                data=matrix if matrix.shape[1] > 1 else matrix[:, 0],
                start=chain.start,
                end=chain.end,
                thin=chain.thin,
            )
        )
        if getattr(chain, "colnames", None):
            rebuilt[-1].colnames = list(chain.colnames)
    result = McmcList(chains=rebuilt)
    if getattr(obj, "chain_names", None):
        result.chain_names = list(obj.chain_names)
    return result


def mcmc_start(x):
    chain = x.chains[0] if is_mcmc_list(x) else as_mcmc(x)
    return float(chain.start)


def mcmc_end(x):
    chain = x.chains[0] if is_mcmc_list(x) else as_mcmc(x)
    return float(chain.end)


def mcmc_thin(x):
    chain = x.chains[0] if is_mcmc_list(x) else as_mcmc(x)
    return float(chain.thin)


def mcmc_time(x):
    start = mcmc_start(x)
    end = mcmc_end(x)
    thin = int(mcmc_thin(x))
    return np.arange(start, end + thin / 2.0, thin, dtype=np.float64)


def _chain_matrix(chain: Mcmc) -> np.ndarray:
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def set_chain_names(obj: McmcList, names):
    obj.chain_names = [str(name) for name in names]


def set_varnames(obj: McmcList, names):
    for chain in obj.chains:
        chain.colnames = [str(name) for name in names]


def resolve_object(name: str, namespace: dict[str, Any] | None):
    if namespace is None:
        namespace = {}
    if name not in namespace:
        return None
    return namespace[name]
