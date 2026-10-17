"""Workspace, paths, devices, timer, and printing."""

from __future__ import annotations

import os
import platform
import sys
import time

import numpy as np

from pracma._util import PracmaError
from pracma.util_size import isempty
from pracma.util_strings import blanks
from pracma.util_support import whole_number

workspace: dict = {}
_elapsed = {"seconds": None}
_figures: dict = {}


_MISSING = object()


def clear(lst=_MISSING):
    if lst is _MISSING:
        workspace.clear()
        return None
    if isinstance(lst, str):
        names = [lst]
    elif isinstance(lst, (list, tuple)) and all(isinstance(item, str) for item in lst):
        names = list(lst)
    else:
        raise PracmaError("Argument must be empty or a character vector.")
    for name in names:
        workspace.pop(name, None)
    return None


def who():
    return sorted(workspace)


def whos():
    names = who()
    if isempty(names):
        return None
    width = max(len(name) for name in names)
    for name in names:
        item = workspace[name]
        kind = type(item).__name__
        if isinstance(item, np.ndarray) and item.ndim == 2:
            shape = "x".join(str(part) for part in item.shape)
        else:
            try:
                shape = str(len(item))
            except TypeError:
                shape = "1"
        size = sys.getsizeof(item)
        if size < 1024:
            shown = f"{size} Byte"
        elif size < 1024 * 1024:
            shown = f"{round(size / 1024, 1)} KB"
        else:
            shown = f"{round(size / 1024 / 1024, 1)} MB"
        print(f"{name}{blanks(width - len(name) + 2)}{kind}, {shape}, {shown}")
    print()
    return names


def what(dname=None):
    if dname is None:
        dname = os.getcwd()
    if not os.path.exists(dname):
        print(f"Argument '{dname}' is not a known directory.")
    elif os.path.isdir(dname):
        names = sorted(os.listdir(dname))
        if isempty(names):
            print(f"No files in Directory {dname}.")
            print()
        else:
            print(f"Files in Directory {dname}:")
            print()
            for name in names:
                path = os.path.join(dname, name)
                if not os.path.isdir(path):
                    print(name)
    else:
        print(f"Argument '{dname}' is not a directory.")
    return None


def cd(dname=None):
    if dname is None:
        return os.getcwd()
    os.chdir(dname)
    return os.getcwd()


def pwd():
    return os.getcwd()


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def figure(figno=None, title=""):
    if figno is not None:
        if isinstance(figno, (bool, np.bool_)) or not _numeric_one(figno) or not whole_number(figno):
            raise PracmaError("The figure handle must be a whole number.")
        figno = int(float(figno))
        if figno in (1, -1):
            raise PracmaError("Device 1 is the null device; cannot be opened or closed.")
        if figno == 0:
            raise PracmaError("Requested figure handle 0 is in use by another object.")
    plt = _pyplot()
    if figno is None:
        fig = plt.figure()
        _figures[fig.number] = fig
        return None
    if abs(figno) in _figures:
        if figno > 0:
            plt.figure(figno)
        else:
            plt.close(-figno)
            _figures.pop(-figno, None)
        return None
    print(f"Device {figno} is not an open device. List of devices:")
    if not _figures:
        return None
    return np.array(sorted(_figures), dtype=float)


def _numeric_one(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return False
    array = np.asarray(value)
    return array.size == 1 and np.issubdtype(array.dtype, np.number)


def tic(gcFirst=False):
    if gcFirst is True:
        import gc

        gc.collect()
    _elapsed["seconds"] = time.perf_counter()
    return None


def toc(echo=True):
    diff = time.perf_counter() - _elapsed["seconds"]
    if echo:
        print(f"elapsed time is {diff:f} seconds")
    return diff


def fprintf(fmt, *args, file="", append=False):
    text = fmt % args if args else fmt
    if file in ("", None):
        sys.stdout.write(text)
    else:
        mode = "a" if append else "w"
        with open(file, mode, encoding="utf-8") as handle:
            handle.write(text)
    return len(text)


def beep():
    sys.stdout.write("\a")
    return None


def disp(*args):
    print(*args)
    return None


def ver():
    print("------------------------------------------------------------------------")
    print(f"Version:    Python {platform.python_version()}")
    print("License:    Gnu General Public License, GPL-3")
    print(f"Platform:   {platform.platform()}")
    print(f"Op.System:  {platform.system()} ({platform.machine()})")
    print(f"Locale:     {'.'.join(filter(None, __import__('locale').getlocale()))}")
    print("------------------------------------------------------------------------")
    return None


def matlab():
    print(
        "\n".join(
            [
                "",
                "The following functions are emulations of corresponding Matlab functions",
                "and bear the same signature as their Matlab cousins as far as possible:",
                "",
                "  accumarray, acosd, acot, acotd, acoth, acsc, acscd, acsch, and, angle, ans,",
                "      arrayfun, asec, asecd, asech, asind, atand, atan2d,",
                "  beep, bernoulli, blank, blkdiag, bsxfun,",
                "  cart2pol, cart2sph, cd, ceil, circshift, clear, compan, cond, conv,",
                "      cosd, cot, cotd, coth, cross, csc, cscd, csch, cumtrapz,",
                "  dblquad, deblank, deconv, deg2rad, detrend, deval, disp, dot,",
                "  eig, eigint, ellipj, ellipke, eps, erf, erfc, erfcinv, erfcx, erfi, erfinv,",
                "      errorbar, expint, expm, eye, ezcontour, ezmesh, ezplot, ezpolar, ezsurf,",
                "  fact, fftshift, figure, findpeaks, findstr, flipdim, fliplr, flipud,",
                "      fminbnd, fminsearch, fplot, fprintf, fsolve, fzero,",
                "  gammainc, gcd, geomean, gmres, gradient,",
                "  hadamard, hankel, harmmean, hilb, histc, humps, hypot,",
                "  idivide, ifft, ifftshift, inpolygon, integral, integral2, integral3,",
                "      interp1, interp2, inv, isempty, isprime,",
                "  kron,",
                "  legendre, linprog, linspace, loglog, logm, logseq, logspace, lsqcurvefit,",
                "      lsqlin, lsqnonlin, lsqnonneg, lu,",
                "  magic, meshgrid, mkpp, mldivide, mod, mrdivide,",
                "  nchoosek, ndims, nextpow2, nnz, normest, nthroot, null, num2str, numel,",
                "  ode23, ode23s, ones, or, orth,",
                "  pascal, pchip, pdist, pdist2, peaks, perms, piecewise, pinv, plotyy,",
                "      pol2cart,polar, polyfit, polyint, polylog, polyval, pow2, ppval,",
                "      primes, psi, pwd,",
                "  quad, quad2d, quadgk, quadl, quadprog, quadv, quiver,",
                "  rad2deg, randi, randn, randsample, rat, rats, regexp, regexpi, regexpreg,",
                "      rem, repmat, roots, rosser, rot90, rref, runge,",
                "  sec, secd, sech, semilogx, semilogy, sinc, sind, size, sortrows, sph2cart,",
                "      sqrtm, squareform, std, str2num, strcat, strcmp, strcmpi,",
                "	  strfind, strfindi, strjust, subspace,",
                "  tand, tic, toc, trapz, tril, trimmean, triplequad, triu,",
                "  vander, vectorfield, ver,",
                "  what, who, whos, wilkinson,",
                "  zeros, zeta.",
                "",
                "The following Matlab function names have been capitalized in 'pracma' to",
                "avoid shadowing functions from R base or one of its recommended packages:",
                "",
                "  Diag, factors, finds, Fix, Imag, Lcm, Mode, Norm, nullspace (null),",
                "  Poly, Rank, Real, Reshape, strRep, strTrim, Toeplitz, Trace, uniq (unique).",
                "",
                "To use 'ans' instead of 'ans()' (i.e., as is common practice in Matlab)",
                "type (and similar for other Matlab commands):",
                "",
                "  makeActiveBinding('ans', function() .Last.value, .GlobalEnv)",
                "  makeActiveBinding('who', who, .GlobalEnv)",
                "",
                "etc. after loading the 'pracma' package.",
                "",
            ]
        )
    )
    return None
