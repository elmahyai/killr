"""Read CODA output and index files into an MCMC object.

Translated from coda 0.19-4.1 ``read.coda`` in ``R/output.R``.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import numpy as np

from coda.as_mcmc import as_mcmc


def read_coda(
    output_file,
    index_file,
    start=None,
    end=None,
    thin=None,
    quiet=False,
):
    """Read a CODA output file and companion index into an ``Mcmc`` (or a matrix)."""
    index_table = _read_index_table(index_file)
    vnames = index_table["names"]
    begin = index_table["begin"]
    end_idx = index_table["end"]

    temp_iter, temp_val = _scan_output(output_file)

    nvar = len(vnames)
    start_vec = np.zeros(nvar, dtype=np.float64)
    end_vec = np.zeros(nvar, dtype=np.float64)
    thin_vec = np.zeros(nvar, dtype=np.float64)

    for i in range(nvar):
        inset = _inclusive_slice(begin[i], end_idx[i])
        iter_i = temp_iter[inset]
        if iter_i.size == 0:
            thin_i = np.array([], dtype=np.float64)
        else:
            thin_i = np.unique(np.diff(iter_i))
        thin_vec[i] = thin_i[0] if thin_i.size == 1 else np.nan
        start_vec[i] = iter_i[0] if iter_i.size else np.nan
        end_vec[i] = iter_i[-1] if iter_i.size else np.nan

    if (
        np.any(np.isnan(start_vec))
        or not np.all(thin_vec == thin_vec[0])
        or np.any((start_vec - start_vec[0]) % thin_vec[0] != 0)
    ):
        iter_all = np.sort(np.unique(temp_iter))
        if iter_all.size >= 2:
            old_thin = np.unique(np.diff(iter_all))
        else:
            old_thin = np.array([1.0])
        if old_thin.size == 1:
            is_regular = True
        else:
            if np.all(old_thin % np.min(old_thin) == 0):
                old_thin = np.array([np.min(old_thin)])
            else:
                old_thin = np.array([1.0])
            is_regular = False
    else:
        iter_all = np.arange(
            np.min(start_vec),
            np.max(end_vec) + thin_vec[0],
            thin_vec[0],
            dtype=np.float64,
        )
        old_thin = np.array([thin_vec[0]], dtype=np.float64)
        is_regular = True

    if start is None:
        start_val = float(np.min(start_vec))
    elif start < np.min(start_vec):
        warnings.warn("start not changed", RuntimeWarning, stacklevel=2)
        start_val = float(np.min(start_vec))
    elif start > np.max(end_vec):
        raise ValueError("Start after end of data")
    else:
        start_val = float(start)
        iter_all = iter_all[iter_all >= start_val]

    if end is None:
        end_val = float(np.max(end_vec))
    elif end > np.max(end_vec):
        warnings.warn("end not changed", RuntimeWarning, stacklevel=2)
        end_val = float(np.max(end_vec))
    elif end < np.min(start_vec):
        raise ValueError("End before start of data")
    else:
        end_val = float(end)
        iter_all = iter_all[iter_all <= end_val]

    old_thin_val = _first_value(old_thin)
    if thin is None:
        thin_val = old_thin_val
    elif thin % old_thin_val != 0:
        thin_val = old_thin_val
        warnings.warn("thin not changed", RuntimeWarning, stacklevel=2)
    else:
        thin_val = float(thin)
        new_iter = iter_all[(iter_all - start_val) % thin_val == 0]
        if new_iter.size >= 2:
            new_thin = np.unique(np.diff(new_iter))
        else:
            new_thin = np.array([thin_val])
        if new_thin.size != 1 or new_thin[0] != thin_val:
            warnings.warn("thin not changed", RuntimeWarning, stacklevel=2)
            thin_val = old_thin_val
        else:
            iter_all = new_iter
            end_val = float(np.max(iter_all))
            is_regular = True

    niter = int(iter_all.size)
    out = np.full((niter, nvar), np.nan, dtype=np.float64)

    for col, v in enumerate(vnames):
        if not quiet:
            print(f"Abstracting {v} ... ", end="", flush=True)
        inset = _inclusive_slice(begin[col], end_idx[col])
        iter_v = temp_iter[inset]
        if not is_regular:
            use_v = _r_duplicated(np.concatenate([iter_all, iter_v]))[iter_all.size :]
            use = _r_duplicated(np.concatenate([iter_v, iter_all]))[iter_v.size :]
        else:
            use_v = (
                (iter_v - start_val) % thin_val == 0
                & (iter_v >= start_val)
                & (iter_v <= end_val)
            )
            use = None

        if use_v.size > 0 and np.any(use_v):
            values = temp_val[inset][use_v]
            if is_regular:
                rows = ((iter_v[use_v] - start_val) // thin_val).astype(int)
                out[rows, col] = values
            else:
                out[use, col] = values

        if not quiet:
            count = int(np.sum(use_v)) if use_v.size else 0
            print(f"{count} valid values")

    if is_regular:
        result = as_mcmc(out, start=start_val, end=end_val, thin=thin_val)
        result.colnames = list(vnames)
        return result

    warnings.warn("not returning an mcmc object", RuntimeWarning, stacklevel=2)
    return out


def _read_index_table(path):
    lines = Path(path).read_text().splitlines()
    non_empty = [line.strip() for line in lines if line.strip()]
    if not non_empty:
        raise ValueError("empty index file")
    data_lines = non_empty[1:] if len(non_empty) > 1 else non_empty
    names = []
    begin = []
    end = []
    for line in data_lines:
        fields = _split_index_fields(line)
        if len(fields) < 3:
            raise ValueError(f"malformed index line: {line!r}")
        names.append(fields[0])
        begin.append(int(float(fields[1])))
        end.append(int(float(fields[2])))
    return {"names": names, "begin": begin, "end": end}


def _split_index_fields(line):
    fields = []
    for match in re.finditer(r'"([^"]*)"|(\S+)', line):
        if match.group(1) is not None:
            fields.append(match.group(1))
        else:
            fields.append(match.group(2))
    return fields


def _scan_output(path):
    iters = []
    vals = []
    for line in Path(path).read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        iters.append(float(parts[0]))
        vals.append(float(parts[1]))
    return np.asarray(iters, dtype=np.float64), np.asarray(vals, dtype=np.float64)


def _inclusive_slice(begin, end):
    return slice(int(begin) - 1, int(end))


def _first_value(values):
    array = np.atleast_1d(np.asarray(values, dtype=np.float64))
    return float(array[0])


def _r_duplicated(values):
    dup = np.zeros(values.size, dtype=bool)
    seen = set()
    for index, key in enumerate(values):
        if key in seen:
            dup[index] = True
        else:
            seen.add(key)
    return dup
