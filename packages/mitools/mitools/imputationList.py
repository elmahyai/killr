"""Multiple-imputation data containers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass
class ImputationList:
    """A collection of equally shaped imputed datasets."""

    imputations: list[Any]
    call: Any = None
    updates: list[dict[str, Any]] | None = field(default=None, repr=False)

    def __len__(self) -> int:
        return len(self.imputations)

    def __iter__(self):
        return iter(self.imputations)

    def __getitem__(self, index):
        return self.imputations[index]


def imputationList(datasets: Iterable[Any], *args, **kwargs) -> ImputationList:
    """Construct an :class:`ImputationList` from imputed datasets.

    Database-backed R objects are intentionally not emulated; Python callers
    should pass the already loaded datasets.
    """
    if isinstance(datasets, (str, bytes)):
        raise NotImplementedError("database-backed imputation lists are not supported")
    return ImputationList(list(datasets))


def update(object: ImputationList, **updates: Callable[[Any], Any]) -> ImputationList:
    """Evaluate named update functions on every imputed dataset."""
    out = deepcopy(object)
    for dataset in out.imputations:
        for name, expression in updates.items():
            value = expression(dataset) if callable(expression) else expression
            if isinstance(dataset, dict):
                dataset[name] = value
            else:
                dataset[name] = value
    return out


def rbind(*objects: ImputationList) -> ImputationList:
    """Row-bind corresponding datasets."""
    if len(objects) == 1:
        return objects[0]
    if not all(isinstance(x, ImputationList) for x in objects):
        raise TypeError("arguments must all be imputationLists")
    if len({len(x) for x in objects}) != 1:
        raise ValueError("differing numbers of imputations")
    import numpy as np
    combined = []
    for i in range(len(objects[0])):
        combined.append(np.concatenate([np.asarray(x[i]) for x in objects], axis=0))
    return ImputationList(combined)


def cbind(*objects: ImputationList) -> ImputationList:
    """Column-bind corresponding datasets."""
    if len(objects) == 1:
        return objects[0]
    if not all(isinstance(x, ImputationList) for x in objects):
        raise TypeError("arguments must all be imputationLists")
    if len({len(x) for x in objects}) != 1:
        raise ValueError("differing numbers of imputations")
    import numpy as np
    return ImputationList([
        np.concatenate([np.asarray(x[i]) for x in objects], axis=1)
        for i in range(len(objects[0]))
    ])
