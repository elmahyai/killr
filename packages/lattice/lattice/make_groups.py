"""Grouped data from multiple vectors, as lattice ``make.groups``."""

from __future__ import annotations

def _is_data_frame(x):
    return isinstance(x, dict) and bool(x) and all(isinstance(v, (list, tuple)) for v in x.values())


def _group_factor(names, lengths):
    labels = list(names)
    codes = []
    for index, count in enumerate(lengths, start=1):
        codes.extend([index] * int(count))
    return codes, labels


def _rbind_frames(frames):
    columns = list(frames[0].keys())
    out = {name: [] for name in columns}
    for frame in frames:
        for name in columns:
            out[name].extend(frame[name])
    return out


def make_groups(**groups):
    """Combine named vectors or compatible data frames with a ``which`` group column."""
    if not groups:
        raise ValueError("must pass at least one group")
    names = list(groups.keys())
    tmp = [groups[name] for name in names]
    lengths = [_nrow(item) for item in tmp]
    which_codes, which_labels = _group_factor(names, lengths)
    if all(_is_data_frame(item) for item in tmp):
        out = _rbind_frames(tmp)
        out["which"] = [_which_label(code, which_labels) for code in which_codes]
        return out
    data = []
    for item in tmp:
        data.extend(_vectorize(item))
    return {
        "data": data,
        "which": [_which_label(code, which_labels) for code in which_codes],
    }


def _which_label(code, labels):
    return labels[code - 1]


def _vectorize(x):
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _nrow(x):
    if _is_data_frame(x):
        first = next(iter(x.values()))
        return len(first)
    return len(_vectorize(x))
