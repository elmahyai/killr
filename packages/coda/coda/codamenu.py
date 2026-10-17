"""Interactive CODA menu driver (``codamenu`` in coda 0.19-4.1)."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from coda.as_mcmc import as_mcmc, is_mcmc
from coda.as_mcmc_list import as_mcmc_list, is_mcmc_list
from coda.chanames import chanames
from coda.coda_options import coda_options
from coda.codamenu_support import (
    gelman_transform,
    menu,
    mcmc_end,
    mcmc_start,
    mcmc_thin,
    mcmc_time,
    read_yesno,
    resolve_object,
    set_chain_names,
    set_varnames,
)
from coda.effectiveSize import effectiveSize
from coda.mcmc_list import mcmc_list
from coda.nchain import nchain
from coda.nvar import nvar
from coda.read_and_check import read_and_check
from coda.varnames import varnames

_MENU_HANDLERS: dict[str, Any] = {}


def _register(name):
    def decorator(func):
        _MENU_HANDLERS[name] = func
        return func

    return decorator


def codamenu(namespace=None):
    """Run the CODA interactive analysis menu."""
    coda_options(default=True)
    file_menu = ["Read BUGS output files", "Use an mcmc object", "Quit"]
    pick = menu(file_menu, title="CODA startup menu")
    if pick == 0 or pick == 3:
        return None

    coda_dat = None
    if pick == 1:
        from coda.read_coda_interactive import read_coda_interactive

        coda_dat = read_coda_interactive()
        if coda_dat is None:
            return None
    elif pick == 2:
        msg = '\nEnter name of saved object (or type "exit" to quit)'
        while True:
            print(msg)
            outname = read_and_check(what="")
            if outname in ("exit", '"exit"'):
                return None
            coda_dat = resolve_object(outname, namespace)
            if coda_dat is None:
                msg = "Can't find this object"
                continue
            if is_mcmc(coda_dat):
                coda_dat = mcmc_list(coda_dat)
            if not is_mcmc_list(coda_dat):
                msg = "Not an mcmc or mcmc.list object"
                continue
            break
    else:
        raise ValueError("Invalid option")

    if chanames(coda_dat) is None:
        set_chain_names(coda_dat, chanames(coda_dat, allow_null=False))
    first = coda_dat.chains[0]
    matrix = np.asarray(first.data)
    if matrix.ndim >= 2 and varnames(coda_dat) is None:
        set_varnames(coda_dat, varnames(coda_dat, allow_null=False))

    is_linear = [False] * nvar(coda_dat)
    times = mcmc_time(coda_dat)
    for i in range(nchain(coda_dat)):
        chain_mat = np.asarray(coda_dat.chains[i].data, dtype=np.float64)
        if chain_mat.ndim == 1:
            chain_mat = chain_mat.reshape(-1, 1)
        for j in range(nvar(coda_dat)):
            coef = np.polyfit(times, chain_mat[:, j], 1)
            fitted = np.polyval(coef, times)
            resid_sd = float(np.std(chain_mat[:, j] - fitted, ddof=1))
            if np.isclose(resid_sd, 0.0, rtol=0, atol=1e-8):
                is_linear[j] = True

    if any(is_linear):
        print("Dropping the following variables, which are linear")
        print("functions of the iteration number")
        names = varnames(coda_dat, allow_null=False)
        dropped = [names[idx] for idx, flag in enumerate(is_linear) if flag]
        print(" ".join(dropped))
        keep = [names[idx] for idx, flag in enumerate(is_linear) if not flag]
        coda_dat = _subset_mcmc_list(coda_dat, variables=keep)

    print("Checking effective sample size ...", end="", flush=True)
    transformed = gelman_transform(coda_dat)
    ess_rows = [
        np.atleast_1d(effectiveSize(np.asarray(chain.data, dtype=np.float64)))
        for chain in transformed.chains
    ]
    warn_small = any(np.any(row < 200) for row in ess_rows)
    if warn_small:
        print()
        print("*******************************************")
        print("WARNING !!!                              ")
        print("Some variables have an effective sample  ")
        print("size of less than 200 in at least one    ")
        print("chain.                                   ")
        print("This is too small, and may cause errors  ")
        print("in the diagnostic tests                  ")
        print("HINT:                                    ")
        print("Look at plots first to identify variables")
        print("with slow mixing.  (Choose menu Output   ")
        print("Analysis then Plots)                     ")
        print("Re-run your chain with a larger sample   ")
        print("size and thinning interval. If possible, ")
        print("reparameterize your model to improve mixing")
        print("*******************************************")
    else:
        print("OK")

    current_menu = "codamenu.main"
    work_dat = coda_dat
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        while True:
            handler = _MENU_HANDLERS.get(current_menu, codamenu_main)
            try:
                next_menu = handler(work_dat, coda_dat)
            except Exception:
                if current_menu == "codamenu.main":
                    print("A crash has occurred in the main menu\nBailing out\n")
                    return None
                print("\n\n**********************")
                print("An error has occurred")
                print("Returning to main menu")
                print("**********************")
                current_menu = "codamenu.main"
                continue

            if isinstance(next_menu, dict) and "work.dat" in next_menu:
                work_dat = next_menu["work.dat"]
                next_menu = next_menu.get(1) or next_menu.get("next")

            if next_menu == "quit":
                if read_yesno("Are you sure you want to quit", False):
                    break
            elif isinstance(next_menu, str):
                current_menu = next_menu
    return None


def _subset_mcmc_list(obj, variables=None, chains=None):
    from coda.as_mcmc import Mcmc
    from coda.as_mcmc_list import McmcList

    names = varnames(obj, allow_null=False)
    if variables is not None:
        indices = [names.index(v) for v in variables]
    else:
        indices = list(range(len(names)))
    chain_indices = list(range(nchain(obj))) if chains is None else [c - 1 for c in chains]
    new_chains = []
    for ci in chain_indices:
        chain = obj.chains[ci]
        mat = np.asarray(chain.data, dtype=np.float64)
        if mat.ndim == 1:
            mat = mat.reshape(-1, 1)
        sub = mat[:, indices]
        new_chain = Mcmc(
            data=sub if sub.shape[1] > 1 else sub[:, 0],
            start=chain.start,
            end=chain.end,
            thin=chain.thin,
        )
        new_chain.colnames = [names[i] for i in indices]
        new_chains.append(new_chain)
    out = McmcList(chains=new_chains)
    cnames = chanames(obj, allow_null=False)
    if cnames:
        out.chain_names = [cnames[i] for i in chain_indices]
    return out


@_register("codamenu.main")
def codamenu_main(work_dat, coda_dat=None):
    choices = ["Output Analysis", "Diagnostics", "List/Change Options", "Quit"]
    next_menu_list = ["codamenu.anal", "codamenu.diags", "codamenu.options", "quit"]
    pick = menu(choices, title="CODA Main Menu")
    if pick == 0:
        return "quit"
    return next_menu_list[pick - 1]


@_register("codamenu.anal")
def codamenu_anal(work_dat, coda_dat=None):
    return codamenu_main(work_dat, coda_dat)


@_register("codamenu.diags")
def codamenu_diags(work_dat, coda_dat=None):
    return codamenu_main(work_dat, coda_dat)


@_register("codamenu.options")
def codamenu_options(work_dat, coda_dat=None):
    return codamenu_main(work_dat, coda_dat)
