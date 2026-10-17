"""Edited training sets from class.

condense, multiedit, and reduce.nn call knn and R's sample. The draws
use boot's generator.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_knn = importlib.import_module("class.knn")
_rows = _knn._rows
knn = _knn.knn
knn1 = _knn.knn1


def _rng():
    try:
        from boot import rng as module
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot import rng as module
    return module


def _sample(values, size=None, replace=False):
    if size is None:
        size = len(values)
    picks = _rng().sample_int(len(values), size, replace)
    return [values[index - 1] for index in picks]


def multiedit(x, cl, k=1, V=3, I=5, trace=False):
    """Indexes, 1-based, kept after the editing passes."""
    rows = _rows(x)
    labels = list(cl)
    index = list(range(len(labels)))
    n1 = len(labels)
    passed = 0
    last = 0
    while True:
        if n1 < 5 * V:
            break
        passed += 1
        block = _rng().sample_int(V, len(labels), replace=True)
        keep = [False] * len(labels)
        for group in range(1, V + 1):
            train = [i for i, item in enumerate(block) if item == group]
            test_group = 1 + group % V
            test = [i for i, item in enumerate(block) if item == test_group]
            if not test:
                continue
            guessed = knn(
                [rows[i] for i in train],
                [rows[i] for i in test],
                [labels[i] for i in train],
                k=k,
            )
            for at, label in zip(test, guessed):
                keep[at] = str(label) == str(labels[at])
        rows = [row for row, flag in zip(rows, keep) if flag]
        labels = [label for label, flag in zip(labels, keep) if flag]
        index = [item for item, flag in zip(index, keep) if flag]
        n2 = len(labels)
        if n2 < n1:
            last = passed
        if last <= passed - I:
            break
        n1 = n2
    return [item + 1 for item in index]


def condense(train, cl, store=None, trace=False):
    """1-based indexes of the condensed set."""
    rows = _rows(train)
    labels = list(cl)
    n = len(labels)
    if store is None:
        store = _rng().sample_int(n, 1)[0] - 1
    else:
        store = int(store) - 1
    bag = [True] * n
    bag[store] = False
    while True:
        if sum(bag) == 0:
            break
        held = [i for i, flag in enumerate(bag) if not flag]
        waiting = [i for i, flag in enumerate(bag) if flag]
        guessed = knn1([rows[i] for i in held], [rows[i] for i in waiting], [labels[i] for i in held])
        added = [index for index, label in zip(waiting, guessed) if str(label) != str(labels[index])]
        if not added:
            break
        if len(added) > 1:
            added = _sample(added, 1)
        bag[added[0]] = False
    return [index + 1 for index, flag in enumerate(bag) if not flag]


def reduce_nn(train, ind, cl):
    """1-based indexes still needed after dropping redundant stored rows."""
    rows = _rows(train)
    labels = list(cl)
    n = len(labels)
    kept = [int(item) - 1 for item in ind]
    rest = [index for index in range(n) if index not in set(kept)]
    for item in _sample(kept):
        held = [index for index in range(n) if index not in set(rest) and index != item]
        query = rest + [item]
        guessed = knn1([rows[index] for index in held], [rows[index] for index in query], [labels[index] for index in held])
        if [str(label) for label in guessed] == [str(labels[index]) for index in query]:
            rest.append(item)
    return [index + 1 for index in range(n) if index not in set(rest)]
