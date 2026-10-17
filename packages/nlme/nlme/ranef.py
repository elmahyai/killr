"""Random effects of mixed-effects fits (nlme ``ranef`` and ``random.effects``).

``ranef`` is an S3 generic in R.  Its two methods, ``ranef.lme`` and
``ranef.lmList``, are the bodies here, dispatched on the ``classes`` of the
fit stand-in (``LmeFit`` or ``LmListFit``).  ``random.effects`` is the same
generic under its other name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from nlme.lmlistformula import LmList, coef as lm_list_coef


@dataclass(slots=True)
class RanefFrame:
    """One ``data.frame`` of effects: rows are groups, columns are effects or augmentations."""

    rownames: tuple[str, ...]
    colnames: tuple[str, ...]
    columns: list[np.ndarray]
    effect_names: tuple[str, ...] | None = None

    def as_matrix(self) -> np.ndarray:
        """Numeric matrix with the columns in order, like R's ``as.matrix``."""
        if not self.columns:
            return np.empty((len(self.rownames), 0), dtype=np.float64)
        return np.column_stack([np.asarray(col, dtype=np.float64) for col in self.columns])


@dataclass(slots=True)
class RanefEffects:
    """``ranef.lme`` / ``ranef.lmList`` result with R's attributes."""

    frames: list[RanefFrame]
    label: str
    level: int
    standardized: bool
    grp_names: tuple[str, ...]
    single: bool
    classes: tuple[str, ...] = ("ranef.lme",)
    extra: dict[str, Any] = field(default_factory=dict)

    def as_matrix(self) -> np.ndarray:
        """The single data frame as a numeric matrix (``as.matrix`` on a one-level result)."""
        if len(self.frames) != 1:
            raise ValueError("as_matrix needs a single level")
        return self.frames[0].as_matrix()


def ranef(
    object: Any,
    aug_frame: bool = False,
    level: int | Sequence[int] | None = None,
    data: Any = None,
    which: Sequence[int | str] | None = None,
    fun: Any = None,
    standard: bool = False,
    omit_grouping_factor: bool = True,
    subset: Any = None,
    sigma: float | None = None,
    re_struct_diag: Mapping[str, Sequence[float]] | None = None,
) -> RanefEffects:
    """Extract random effects from a fitted ``lme`` or ``lmList`` object.

    ``sigma`` and ``re_struct_diag`` stand in for ``object$sigma`` and
    ``diag(as.matrix(object$modelStruct$reStruct[[i]]))``; they are needed only
    when ``standard`` is true because the ``lme`` stand-in does not store them.
    """
    classes = tuple(getattr(object, "classes", ()))
    if "lme" in classes:
        return _ranef_lme(
            object,
            aug_frame=aug_frame,
            level=level,
            data=data,
            which=which,
            fun=fun,
            standard=standard,
            omit_grouping_factor=omit_grouping_factor,
            subset=subset,
            sigma=sigma,
            re_struct_diag=re_struct_diag,
        )
    if "lmList" in classes or isinstance(object, LmList):
        return _ranef_lm_list(object, aug_frame=aug_frame, standard=standard)
    raise TypeError(f"no applicable method for 'ranef' applied to an object of class {classes!r}")


def random_effects(object: Any, **kwargs) -> RanefEffects:
    """R's ``random.effects``: the same generic as ``ranef``."""
    return ranef(object, **kwargs)


def group_names(names: Sequence[str], q: int) -> list[str]:
    """Port of the ``grpNames`` construction in ``ranef.lme`` for ``Q`` levels."""
    names = list(names)
    if q <= 1:
        return names
    reversed_names = list(reversed(names))
    rows = []
    for row in range(q):
        parts = [reversed_names[col] for col in range(q) if col >= row]
        rows.append(" %in% ".join(parts))
    return list(reversed(rows))


def _ranef_lme(
    object: Any,
    *,
    aug_frame: bool,
    level,
    data,
    which,
    fun,
    standard: bool,
    omit_grouping_factor: bool,
    subset,
    sigma,
    re_struct_diag,
) -> RanefEffects:
    q = int(object.dims.Q)
    effect_names = list(object.coefficients.random.keys())
    grp_names = group_names(effect_names, q)
    levels = _resolve_levels(level, q)
    names = [effect_names[index - 1] for index in levels]

    frames: list[RanefFrame] = []
    for name in names:
        mat = np.asarray(object.coefficients.random[name], dtype=np.float64)
        if standard:
            if sigma is None or re_struct_diag is None:
                raise ValueError("standard=TRUE needs sigma and the reStruct diagonal")
            scale = float(sigma) * np.sqrt(np.asarray(re_struct_diag[name], dtype=np.float64))
            mat = mat / scale[None, :]
        rownames = tuple(str(item) for item in object.coefficients.random_rownames[name])
        colnames = tuple(str(item) for item in object.coefficients.random_colnames[name])
        frames.append(
            RanefFrame(rownames, colnames, [mat[:, col].copy() for col in range(mat.shape[1])])
        )

    if aug_frame:
        if len(levels) > 1:
            raise ValueError("augmentation of random effects only available for single level")
        if subset is not None:
            raise NotImplementedError("subset in ranef augmentation is not translated")
        frame = frames[0]
        frame.effect_names = frame.colnames
        frame_data = _data_columns(data if data is not None else object.call.data)
        frame_data = _select_which(frame_data, which)
        frame_data = {key: val for key, val in frame_data.items() if key not in frame.colnames}
        groups = list(object.groups.values())[levels[0] - 1]
        summary = gsummary(frame_data, groups, fun=fun)
        if omit_grouping_factor:
            summary = {key: val for key, val in summary.items() if key not in effect_names}
        if summary:
            index = {name: pos for pos, name in enumerate(summary["__rows__"])}
            for key, column in summary.items():
                if key == "__rows__":
                    continue
                values = [column[index[row]] for row in frame.rownames]
                frame.columns.append(_as_column(values))
                frame.colnames = frame.colnames + (key,)

    label = "Standardized random effects" if standard else "Random effects"
    return RanefEffects(
        frames=frames,
        label=label,
        level=max(levels),
        standardized=standard,
        grp_names=tuple(grp_names[index - 1] for index in levels),
        single=len(levels) == 1,
        classes=("ranef.lme",),
    )


def _ranef_lm_list(object: Any, *, aug_frame: bool, standard: bool) -> RanefEffects:
    if aug_frame:
        raise NotImplementedError("augFrame for ranef.lmList needs coef.lmList augmentation, not translated")
    named = lm_list_coef(object, aug_frame=False)
    if named is None:
        raise ValueError("no coefficients available for ranef.lmList")
    values = np.asarray(named.values, dtype=np.float64)
    centred = values - np.nanmean(values, axis=0, keepdims=True)
    if standard:
        std_eff = np.array(
            [np.std(col[~np.isnan(col)], ddof=1) for col in centred.T], dtype=np.float64
        )
        centred = centred / std_eff[None, :]
    frame = RanefFrame(
        tuple(str(item) for item in named.rownames),
        tuple(str(item) for item in named.colnames),
        [centred[:, col].copy() for col in range(centred.shape[1])],
    )
    return RanefEffects(
        frames=[frame],
        label="Standardized random effects" if standard else "Random effects",
        level=1,
        standardized=standard,
        grp_names=frame.rownames,
        single=True,
        classes=("ranef.lmList",),
    )


def gsummary(
    columns: Mapping[str, Sequence[Any]],
    groups: Sequence[Any],
    fun: Any = None,
) -> dict[str, Any]:
    """Port of nlme's ``gsummary`` for one grouping vector.

    Varying numeric columns are summarised with ``fun`` (default mean), varying
    other columns with the mode, and invariant columns keep their first value.
    Rows are sorted by group label, as R does.
    """
    group_list = [str(item) for item in groups]
    unique = sorted(set(group_list))
    first_index: dict[str, int] = {}
    for pos, label in enumerate(group_list):
        first_index.setdefault(label, pos)
    summary: dict[str, Any] = {"__rows__": unique}
    for key, column in columns.items():
        col = list(column)
        numeric = all(_is_number(item) for item in col)
        varying = any(
            str(col[pos]) != str(col[first_index[label]])
            for pos, label in enumerate(group_list)
        )
        if not varying:
            summary[key] = [col[first_index[label]] for label in unique]
            continue
        out = []
        for label in unique:
            members = [col[pos] for pos, g in enumerate(group_list) if g == label]
            if numeric:
                out.append(_summarise(members, fun))
            else:
                out.append(_mode(members))
        summary[key] = out
    return summary


def _summarise(members: Sequence[Any], fun) -> float:
    arr = np.asarray(members, dtype=np.float64)
    if fun is None:
        return float(np.mean(arr))
    return float(fun(arr))


def _mode(members: Sequence[Any]) -> str:
    counts: dict[str, int] = {}
    for item in members:
        counts[str(item)] = counts.get(str(item), 0) + 1
    best = max(counts.values())
    return next(key for key in sorted(counts) if counts[key] == best)


def _is_number(item: Any) -> bool:
    return isinstance(item, (int, float, np.integer, np.floating)) and not isinstance(item, bool)


def _as_column(values: Sequence[Any]) -> np.ndarray:
    if all(_is_number(item) for item in values):
        return np.asarray(values, dtype=np.float64)
    return np.asarray(values, dtype=object)


def _resolve_levels(level, q: int) -> list[int]:
    if level is None:
        return list(range(1, q + 1))
    if isinstance(level, (int, np.integer)):
        return [int(level)]
    return [int(item) for item in level]


def _data_columns(data: Any) -> dict[str, list[Any]]:
    if hasattr(data, "columns"):
        data = data.columns
    return {str(key): list(np.asarray(val, dtype=object).ravel()) for key, val in dict(data).items()}


def _select_which(columns: dict[str, list[Any]], which) -> dict[str, list[Any]]:
    if which is None:
        return columns
    keys = list(columns.keys())
    chosen = []
    for item in which:
        chosen.append(keys[int(item) - 1] if isinstance(item, (int, np.integer)) else str(item))
    return {key: columns[key] for key in chosen}
