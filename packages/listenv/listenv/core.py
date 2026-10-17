"""Python representation of R's listenv containers and helpers."""
from __future__ import annotations

import ast
import math
import re
from collections.abc import Mapping, MutableMapping


class ListEnv(MutableMapping):
    """A dict-like holder with listenv's positional and dimensional metadata."""

    def __init__(self, *values, names=None):
        self._values = list(values)
        self._names = list(names) if names is not None else [None] * len(values)
        if len(self._names) != len(self._values):
            raise ValueError("names and values must have the same length")
        self._dim = None
        self._dimnames = None
        self._vars = [f".listenv_var_{i + 1}" for i in range(len(values))]
        self._var_count = len(values)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._names)

    def __getitem__(self, key):
        if isinstance(key, int):
            if key < 0:
                key += len(self._values)
            return self._values[key]
        if isinstance(key, slice):
            return ListEnv(*self._values[key], names=self._names[key])
        try:
            return self._values[self._names.index(key)]
        except ValueError:
            raise KeyError(key) from None

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if key < 0:
                key += len(self._values)
            if key >= len(self._values):
                self._values.extend([None] * (key + 1 - len(self._values)))
                self._names.extend([None] * (key + 1 - len(self._names)))
                self._vars.extend([None] * (key + 1 - len(self._vars)))
            self._values[key] = value
            return
        try:
            i = self._names.index(key)
        except ValueError:
            self._names.append(key)
            self._values.append(value)
            self._vars.append(key)
        else:
            self._values[i] = value

    def __delitem__(self, key):
        i = key if isinstance(key, int) else self._names.index(key)
        del self._values[i]
        del self._names[i]
        self._dim = self._dimnames = None

    def keys(self):
        return list(self._names)

    @property
    def names(self):
        return list(self._names)

    @names.setter
    def names(self, value):
        if value is not None and len(value) != len(self):
            raise ValueError("names length does not match")
        self._names = [None] * len(self) if value is None else list(value)

    @property
    def dim(self):
        return None if self._dim is None else tuple(self._dim)

    @dim.setter
    def dim(self, value):
        if value is None:
            self._dim = self._dimnames = None
            self._names = [None] * len(self)
            return
        dims = tuple(int(v) for v in value)
        if math.prod(dims) != len(self):
            if len(self) != 0:
                raise ValueError("dimension product does not match length")
            self._values.extend([None] * math.prod(dims))
            self._names.extend([None] * math.prod(dims))
            self._vars.extend([None] * math.prod(dims))
        self._dim = dims
        self._dimnames = None
        self._names = [None] * len(self)

    @property
    def dimnames(self):
        return self._dimnames

    @dimnames.setter
    def dimnames(self, value):
        if self._dim is None and value is not None:
            raise ValueError("dimnames applied to non-array")
        if value is not None and any(
            dn is not None and len(dn) != self._dim[i]
            for i, dn in enumerate(value)
        ):
            raise ValueError("dimnames length does not match dimension")
        self._dimnames = None if value is None else [None if x is None else list(x) for x in value]

    def as_list(self):
        return list(self._values)


def listenv(*args, **kwargs):
    names = [None] * len(args) + list(kwargs) if kwargs else [None] * len(args)
    values = list(args) + list(kwargs.values())
    return ListEnv(*values, names=names if kwargs else None)


def as_listenv(x, *args, **kwargs):
    if isinstance(x, ListEnv):
        return x
    if isinstance(x, Mapping):
        return ListEnv(*x.values(), names=list(x.keys()))
    return ListEnv(*list(x))


def mapping(x: ListEnv, *args, **kwargs):
    return {name: var for name, var in zip(x.names, x._vars) if name is not None}


def map_(x: ListEnv, *args, **kwargs):
    return mapping(x, *args, **kwargs)


def get_variable(x: ListEnv, name, mustExist=False, create=None, **kwargs):
    if create is None:
        create = not mustExist
    if isinstance(name, (list, tuple)):
        if x.dim is None or len(name) != len(x.dim):
            raise ValueError("subscript must be scalar or match dimensions")
        idx = 0
        stride = 1
        for i, d in zip(name, x.dim):
            if not 1 <= int(i) <= d:
                raise IndexError("index out of range")
            idx += (int(i) - 1) * stride
            stride *= d
        name = idx + 1
    if isinstance(name, str):
        if name in x.names:
            return f".listenv_var_{x.names.index(name) + 1}"
        if mustExist:
            raise KeyError(name)
        if create:
            x._names.append(name)
            x._values.append(None)
            x._vars.append(name)
        return name
    i = int(name) - 1
    if i < 0:
        raise IndexError(name)
    if i >= len(x):
        if mustExist:
            raise IndexError(name)
        extra = i + 1 - len(x)
        x._values.extend([None] * extra)
        x._names.extend([None] * extra)
        x._vars.extend([None] * extra)
    if x._vars[i] is None:
        x._var_count += 1
        x._vars[i] = f".listenv_var_{x._var_count}"
    return x._vars[i]


def dim_na(x, value):
    if value is None:
        x.dim = None
        return x
    vals = list(value)
    missing = [i for i, v in enumerate(vals) if v is None]
    if len(missing) > 1:
        raise ValueError("value may only have one missing dimension")
    if missing:
        known = math.prod(int(v) for v in vals if v is not None)
        vals[missing[0]] = len(x) // known
    x.dim = vals
    return x


def undim(x, *args, **kwargs):
    if isinstance(x, ListEnv):
        x._dim = x._dimnames = None
        return x
    return x


def parse_env_subset(expr, envir=None, substitute=True, is_variable=True):
    """Parse common environment target spellings into R-like metadata."""
    code = expr if isinstance(expr, str) else repr(expr)
    res = {"envir": envir, "name": "", "op": None, "subset": None,
           "idx": None, "exists": None, "code": code}
    if not isinstance(expr, str):
        if isinstance(expr, (int, float)):
            res["subset"] = [expr]
        else:
            res["name"] = str(expr)
        return res
    m = re.fullmatch(r"([A-Za-z_.][\w.]*)\$(\w+)", expr)
    if m:
        res.update(name=m.group(2), op="$", subset=[m.group(2)])
        return res
    m = re.fullmatch(r"([A-Za-z_.][\w.]*)\[\[(.+)\]\]", expr)
    if m:
        val = _literal(m.group(2))
        res.update(op="[[", subset=[val], name=str(val) if isinstance(val, str) else "")
        return res
    m = re.fullmatch(r"([A-Za-z_.][\w.]*)\[(.+)\]", expr)
    if m:
        val = _literal(m.group(2))
        res.update(op="[", subset=[val], name=str(val) if isinstance(val, str) else "")
        return res
    if re.fullmatch(r"[A-Za-z_.][\w.]*", expr):
        res["name"] = expr
        return res
    raise ValueError(f"Invalid syntax: {code}")


def _literal(text):
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError):
        try:
            return int(text)
        except ValueError:
            return text


__all__ = ["ListEnv", "listenv", "as_listenv", "get_variable", "mapping",
           "map_", "parse_env_subset", "dim_na", "undim"]
