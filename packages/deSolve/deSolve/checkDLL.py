"""Resolve compiled-model symbols the way deSolve ``checkDLL`` does."""

from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

# Names registered in src/R_init_deSolve.c. R_useDynamicSymbols is FALSE,
# so is.loaded does not see the rest of the shared object. aquaphyforc is
# registered at aquaphy's address.
_DESOLVE_REGISTERED = {
    "unlock_solver": "unlock_solver",
    "initccl4": "initccl4",
    "initparms": "initparms",
    "initforcs": "initforcs",
    "eventfun": "eventfun",
    "derivsccl4": "derivsccl4",
    "chemres": "chemres",
    "scocpar": "scocpar",
    "scocforc": "scocforc",
    "scocder": "scocder",
    "iniaqua": "iniaqua",
    "initaqforc": "initaqforc",
    "aquaphy": "aquaphy",
    "aquaphyforc": "aquaphy",
    "call_daspk": "call_daspk",
    "call_DLL": "call_DLL",
    "call_euler": "call_euler",
    "call_iteration": "call_iteration",
    "call_lsoda": "call_lsoda",
    "call_radau": "call_radau",
    "call_rk4": "call_rk4",
    "call_rkAuto": "call_rkAuto",
    "call_rkFixed": "call_rkFixed",
    "call_rkImplicit": "call_rkImplicit",
    "call_zvode": "call_zvode",
    "getLagDeriv": "getLagDeriv",
    "getLagValue": "getLagValue",
    "getTimestep": "getTimestep",
}

_LOADED: dict[str, "_Library"] = {}
_FLT_EPSILON = np.finfo(np.float32).eps


class NA:
    """R logical NA. Distinct from NULL, which is Python ``None``."""

    def __repr__(self) -> str:
        return "NA"

    def __str__(self) -> str:
        return "NA"


NA_VALUE = NA()


class CFunc:
    """Inline-style compiled function. ``body[1]`` is the native pointer."""

    def __init__(self, pointer: Any):
        self.body = (None, pointer)


class NativeSymbol:
    """Address returned by ``getNativeSymbolInfo(...)$address``."""

    def __init__(self, address: int, name: str, dll: str):
        self.address = int(address)
        self.name = name
        self.dll = dll

    def __repr__(self) -> str:
        return f"<pointer: 0x{self.address:x}>"


class NameVector:
    """Atomic vector, with optional names and an R storage mode."""

    def __init__(self, values: list[Any], names: list[str] | None, mode: str):
        self.values = values
        self.names = names
        self.mode = mode

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __repr__(self) -> str:
        return repr(self.values)


class DeSolveSymbols:
    """List of class ``deSolve.symbols``."""

    r_class = ("deSolve.symbols", "list")

    def __init__(
        self,
        ModelInit: Any,
        Func: NativeSymbol,
        JacFunc: Any,
        Nglobal: Any,
        Nmtot: dict[str, Any],
    ):
        self.ModelInit = ModelInit
        self.Func = Func
        self.JacFunc = JacFunc
        self.Nglobal = Nglobal
        self.Nmtot = Nmtot

    def __getitem__(self, key: str):
        return getattr(self, key)

    def __repr__(self) -> str:
        return (
            f"DeSolveSymbols(ModelInit={self.ModelInit!r}, Func={self.Func!r}, "
            f"JacFunc={self.JacFunc!r}, Nglobal={self.Nglobal!r}, Nmtot={self.Nmtot!r})"
        )


class _Library:
    def __init__(self, name: str, path: Path, cdll: ctypes.CDLL, registered: dict[str, str] | None):
        self.name = name
        self.path = path
        self.cdll = cdll
        self.registered = registered


def _version_key(path: Path) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in path.name.split("."))
    except ValueError:
        return (0,)


def _add_root(roots: list[Path], seen: set[str], path: Path) -> None:
    path = path.expanduser()
    if not path.is_dir():
        return
    key = str(path.resolve())
    if key in seen:
        return
    seen.add(key)
    roots.append(path)


def _library_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    for key in ("R_LIBS_USER", "R_LIBS", "R_LIBS_SITE"):
        raw = os.environ.get(key, "")
        for part in raw.split(os.pathsep):
            if part:
                _add_root(roots, seen, Path(part))
    r_home = Path.home() / "R"
    if r_home.is_dir():
        for arch in sorted(path for path in r_home.iterdir() if path.is_dir()):
            versions = [path for path in arch.iterdir() if path.is_dir()]
            for version in sorted(versions, key=_version_key, reverse=True):
                _add_root(roots, seen, version)
            _add_root(roots, seen, arch)
    for extra in (
        Path("/usr/local/lib/R/site-library"),
        Path("/usr/lib/R/site-library"),
        Path("/usr/local/lib/R/library"),
        Path("/usr/lib/R/library"),
    ):
        _add_root(roots, seen, extra)
    return roots


def _candidate_paths(dllname: str) -> list[Path]:
    found: list[Path] = []
    filename = f"{dllname}.so"
    for root in _library_roots():
        libs = root / dllname / "libs"
        found.append(libs / filename)
        if libs.is_dir():
            for child in sorted(path for path in libs.iterdir() if path.is_dir()):
                found.append(child / filename)
    raw = os.environ.get("LD_LIBRARY_PATH", "")
    for part in raw.split(os.pathsep):
        if part:
            found.append(Path(part) / filename)
    found.append(Path.cwd() / filename)
    found.append(Path(filename))
    return found


def _is_desolve_package(path: Path) -> bool:
    parts = path.parts
    return path.name == "deSolve.so" and "deSolve" in parts and "libs" in parts


def _load_library(dllname: str) -> _Library | None:
    cached = _LOADED.get(dllname)
    if cached is not None:
        return cached
    for candidate in _candidate_paths(dllname):
        if not candidate.is_file():
            continue
        path = candidate.resolve()
        cdll = ctypes.CDLL(str(path))
        registered = _DESOLVE_REGISTERED if _is_desolve_package(path) else None
        loaded = _Library(dllname, path, cdll, registered)
        _LOADED[dllname] = loaded
        return loaded
    return None


def _symbol_address(cdll: ctypes.CDLL, name: str) -> int | None:
    try:
        address = ctypes.cast(getattr(cdll, name), ctypes.c_void_p).value
    except AttributeError:
        return None
    if not address:
        return None
    return int(address)


def _fortran_names(name: str) -> list[str]:
    if "_" in name:
        return [name + "__", name + "_"]
    return [name + "_"]


def _lookup_address(dllname: str, name: str) -> int | None:
    if not isinstance(name, str):
        raise ValueError("invalid 'symbol' argument")
    loaded = _load_library(dllname)
    if loaded is None:
        return None
    if loaded.registered is not None:
        elf_name = loaded.registered.get(name)
        if elf_name is None:
            return None
        return _symbol_address(loaded.cdll, elf_name)
    address = _symbol_address(loaded.cdll, name)
    if address is not None:
        return address
    for mangled in _fortran_names(name):
        address = _symbol_address(loaded.cdll, mangled)
        if address is not None:
            return address
    return None


def _native(dllname: str, name: str) -> NativeSymbol | None:
    address = _lookup_address(dllname, name)
    if address is None:
        return None
    return NativeSymbol(address, name, dllname)


def _is_cfunc(value: Any) -> bool:
    if isinstance(value, CFunc):
        return True
    classes = getattr(value, "r_class", ())
    if isinstance(classes, str):
        classes = (classes,)
    return "CFunc" in tuple(classes) or type(value).__name__ == "CFunc"


def _cfunc_pointer(value: Any) -> Any:
    body = value.body
    pointer = body[1]
    if isinstance(pointer, NativeSymbol):
        return pointer
    if isinstance(pointer, int) and not isinstance(pointer, bool):
        return NativeSymbol(pointer, "", "")
    return pointer


def _has_duplicate(func: Any, initfunc: Any, jacfunc: Any) -> bool:
    items = [item for item in (func, initfunc, jacfunc) if item is not None]
    for index, item in enumerate(items):
        for earlier in items[:index]:
            if isinstance(item, str) and isinstance(earlier, str):
                if item == earlier:
                    return True
            elif item is earlier:
                return True
    return False


def _switch_index(jt: Any) -> int:
    if isinstance(jt, bool) or isinstance(jt, (int, np.integer)):
        return int(jt)
    if isinstance(jt, (float, np.floating)):
        return int(math.trunc(float(jt)))
    raise ValueError("invalid 'JT' argument")


def _as_nout(nout: Any) -> Any:
    if nout is None:
        return None
    if isinstance(nout, bool):
        return int(nout)
    if isinstance(nout, (int, np.integer)):
        return int(nout)
    if isinstance(nout, (float, np.floating)):
        number = float(nout)
        if number.is_integer() and abs(number) < 2**53:
            return int(number)
        return number
    if isinstance(nout, np.ndarray) and nout.shape == ():
        return _as_nout(nout.item())
    raise ValueError("argument is of length zero" if nout is None else "the condition has length > 1")


def _number(value: Any) -> int | float:
    if isinstance(value, bool):
        raise ValueError("invalid 'outnames' argument")
    if isinstance(value, (int, np.integer)):
        return int(value)
    number = float(value)
    if number.is_integer() and abs(number) < 2**53:
        return int(number)
    return number


def _as_character_piece(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if number.is_integer() and abs(number) < 2**53:
            return str(int(number))
        return str(number)
    return str(value)


def _read_outnames(outnames: Any) -> tuple[str, list[Any], list[str] | None] | None:
    if outnames is None:
        return None
    raw_names = getattr(outnames, "names", None)
    if isinstance(outnames, str):
        values: list[Any] = [outnames]
    elif isinstance(outnames, np.ndarray):
        values = outnames.reshape(-1).tolist()
    else:
        values = list(outnames)
    names: list[str] | None = None
    if raw_names is not None:
        names = ["" if name is None else str(name) for name in list(raw_names)]
        if len(names) != len(values):
            raise ValueError("names length does not match outnames")
    numeric = isinstance(outnames, np.ndarray) and np.issubdtype(outnames.dtype, np.number)
    if not numeric and values and all(_is_number(item) for item in values):
        numeric = True
    if numeric:
        return "numeric", [_number(item) for item in values], names
    return "character", [_as_character_piece(item) for item in values], names


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool)


def r_colon(start: float, end: float) -> list[int]:
    """R's ``:`` operator for integer-valued endpoints."""
    width = abs(float(end) - float(start))
    count = int(width + 1.0 + float(_FLT_EPSILON))
    step = 1 if float(start) <= float(end) else -1
    begin = int(float(start))
    return [begin + index * step for index in range(count)]


def _subset(values: list[Any], names: list[str] | None, indices: list[int]) -> tuple[list[Any], list[str] | None]:
    positive = [index for index in indices if index > 0]
    negative = [index for index in indices if index < 0]
    if positive and negative:
        raise ValueError("only 0's may be mixed with negative subscripts")
    if negative:
        dropped = {abs(index) for index in negative}
        kept = [index for index in range(1, len(values) + 1) if index not in dropped]
        return _subset(values, names, kept)
    chosen: list[Any] = []
    chosen_names: list[str] | None = [] if names is not None else None
    for index in indices:
        if index == 0:
            continue
        if index > len(values):
            chosen.append(None)
            if chosen_names is not None:
                chosen_names.append("")
            continue
        chosen.append(values[index - 1])
        if chosen_names is not None and names is not None:
            chosen_names.append(names[index - 1])
    return chosen, chosen_names


def _output_names(outnames: Any, nout: Any) -> dict[str, Any]:
    nmtot: dict[str, Any] = {}
    parsed = _read_outnames(outnames)
    if parsed is None:
        return nmtot
    mode, values, names = parsed
    if nout is None:
        raise ValueError("argument is of length zero")
    if isinstance(nout, (list, tuple)) or (isinstance(nout, np.ndarray) and nout.shape != ()):
        raise ValueError("the condition has length > 1")
    n_out = _as_nout(nout)
    if not isinstance(n_out, (int, float)):
        raise ValueError("argument is of length zero")
    if len(values) == n_out:
        colnames = values
        col_names = names
    elif len(values) > n_out:
        colnames, col_names = _subset(values, names, r_colon(1, n_out))
    else:
        extra = r_colon(len(values) + 1, n_out)
        if mode == "character":
            colnames = values + [_as_character_piece(item) for item in extra]
        else:
            colnames = values + extra
            if any(isinstance(item, float) and not float(item).is_integer() for item in colnames):
                colnames = [float(item) for item in colnames]
        if names is None:
            col_names = None
        else:
            col_names = names + [""] * len(extra)
    nmtot["colnames"] = NameVector(colnames, col_names, mode if not colnames or isinstance(colnames[0], str) else "numeric")
    if mode == "character" or (colnames and isinstance(colnames[0], str)):
        nmtot["colnames"].mode = "character"
    unique: list[Any] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    if len(values) > len(unique):
        counts = [sum(item == value for item in values) for value in unique]
        count_names = [""] + [_as_character_piece(value) for value in unique]
        nmtot["lengthvar"] = NameVector([None, *counts], count_names, "integer")
    return nmtot


def checkDLL(func, jacfunc, dllname, initfunc, verbose, nout, outnames, JT=1):
    """Resolve DLL entry points and the names of extra output variables.

    ``verbose`` is accepted and unused, matching the R argument that is
    reserved for later extensions. ``JT`` selects the Jacobian error text
    when ``jacfunc`` is not a name.
    """
    del verbose
    if not isinstance(dllname, str):
        raise ValueError("invalid 'symbol' argument")
    if _has_duplicate(func, initfunc, jacfunc):
        raise ValueError("func, initfunc, or jacfunc cannot be the same")

    model_init: Any = NA_VALUE
    if initfunc is not None:
        if _is_cfunc(initfunc):
            model_init = _cfunc_pointer(initfunc)
        else:
            if not isinstance(initfunc, str):
                raise ValueError("invalid 'symbol' argument")
            found = _native(dllname, initfunc)
            if found is not None:
                model_init = found
            elif initfunc != dllname:
                raise ValueError(f"'initfunc' not loaded  {initfunc}")

    if _is_cfunc(func):
        resolved_func = _cfunc_pointer(func)
        if not isinstance(resolved_func, NativeSymbol):
            raise ValueError("invalid 'symbol' argument")
    else:
        if not isinstance(func, str):
            raise ValueError("invalid 'symbol' argument")
        resolved_func = _native(dllname, func)
        if resolved_func is None:
            raise ValueError(f"dyn function 'func' not loaded {func}")

    if jacfunc is None:
        jac_resolved = None
    else:
        if not isinstance(jacfunc, str):
            index = _switch_index(JT)
            if index == 1:
                raise ValueError("If 'func' is dynloaded, so must 'jacfunc' be")
            if index == 2:
                raise ValueError("If 'func' is dynloaded, so must 'jacvec' be")
        if _is_cfunc(jacfunc):
            jac_resolved = _cfunc_pointer(jacfunc)
        elif isinstance(jacfunc, str):
            jac_resolved = _native(dllname, jacfunc)
            if jac_resolved is None:
                raise ValueError(f"cannot integrate: jac function not loaded  {jacfunc}")
        else:
            raise ValueError("invalid 'symbol' argument")

    nglobal = _as_nout(nout) if not isinstance(nout, (list, tuple)) else nout
    if isinstance(nout, np.ndarray) and nout.shape != ():
        nglobal = nout
    return DeSolveSymbols(
        ModelInit=model_init,
        Func=resolved_func,
        JacFunc=jac_resolved,
        Nglobal=nglobal if nout is not None else None,
        Nmtot=_output_names(outnames, nout),
    )
