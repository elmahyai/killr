"""Choose several numbered options from a printed menu.

Translated from coda 0.19-4.1 ``multi.menu`` in ``R/util.R``.
A comma-separated reply may mix single numbers and ``start:end`` ranges.
"""

from __future__ import annotations

import sys

_MISSING = object()


def multi_menu(choices, title=_MISSING, header=_MISSING, allow_zero=True):
    """Print ``choices`` and return the selected option numbers.

    ``0`` means no selection when ``allow_zero`` is true. An out-of-range
    or non-numeric reply is rejected and the prompt is repeated.
    """
    labels = [str(choice) for choice in choices]
    n_choices = len(labels)
    if title is not _MISSING:
        sys.stdout.write(f"{title} \n\n")
    rows = [(str(index), label) for index, label in enumerate(labels, start=1)]
    if header is not _MISSING:
        header_values = [str(item) for item in header]
        if len(header_values) != 2:
            raise ValueError("header is wrong length")
        rows = [(header_values[0], header_values[1]), *rows]
    for line in _format_rows(rows):
        sys.stdout.write(line + "\n")

    while True:
        sys.stdout.write("\nEnter relevant number(s), separated by commas\n")
        sys.stdout.write("Ranges such as 3:7 may be specified)\n")
        if allow_zero:
            sys.stdout.write("(Enter 0 for none)\n")
        sys.stdout.flush()
        tokens = _scan_line()
        if not tokens:
            continue
        out = []
        err = False
        for token in tokens:
            if not _token_ok(token):
                sys.stdout.write("Error: you have specified a non-numeric value!\n")
                err = True
                break
            out.extend(_expand(token))
            lower = 0 if allow_zero else 1
            if (
                min(out) < lower
                or max(out) > n_choices
                or (any(item == 0 for item in out) and len(out) > 1)
            ):
                sys.stdout.write("Error: you have specified variable number(s) out of range!\n")
                err = True
                break
        if not err:
            return out


def _format_rows(rows):
    left = [item[0] for item in rows]
    right = [item[1] for item in rows]
    left_width = max(len(item) for item in left)
    right_width = max(len(item) for item in right)
    return [
        f"{a.ljust(left_width)} {b.ljust(right_width)}"
        for a, b in zip(left, right)
    ]


def _scan_line():
    line = sys.stdin.readline()
    if line == "":
        return []
    if line.endswith("\n"):
        line = line[:-1]
    if line == "":
        return []
    return [part.strip() for part in line.split(",")]


def _token_ok(token):
    if token == "":
        return False
    characters = list(token)
    colons = [char == ":" for char in characters]
    if colons[0] or colons[-1] or sum(colons) > 1:
        return False
    for char, is_colon in zip(characters, colons):
        if is_colon:
            continue
        if not char.isdigit():
            return False
    return True


def _expand(token):
    if ":" in token:
        left, right = token.split(":", 1)
        start = int(left)
        end = int(right)
        if start <= end:
            return list(range(start, end + 1))
        return list(range(start, end - 1, -1))
    return [int(token)]
