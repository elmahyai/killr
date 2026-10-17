"""Orthodont fixtures for ``augPred`` proofs (loads ``lme`` coefficients from R once)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.fit_objects import LmeCall, LmeCoefficients, LmeDims, LmeFit, LmListFit
from nlme.lmlistformula import LmList, lmList_formula

_R_EXPORT = """
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(nlme))
data(Orthodont, package = "nlme")
fm1 <- lmList(Orthodont)
fm2 <- lme(fm1)
random <- fm2$coefficients$random[[1]]
out <- list(
  fixef=fixef(fm2),
  random=list(
    rn=rownames(random),
    cn=colnames(random),
    v=as.vector(random)
  ),
  Q=fm2$dims$Q,
  groups=fm2$groups[[1]],
  group_levels=levels(getGroups(fm2, level=1)),
  fitted=as.vector(fitted(fm2)),
  resid=as.vector(resid(fm2)),
  lm_fitted=as.vector(fitted(fm1)),
  lm_resid=as.vector(resid(fm1))
)
cat(toJSON(out, auto_unbox=FALSE, digits=17))
"""


@dataclass(slots=True)
class OrthodontFixtures:
    data: Any
    fm1: LmListFit
    fm2: LmeFit


def orthodont_fixtures() -> OrthodontFixtures:
    ortho, frame = _orthodont_grouped()
    payload = json.loads(
        subprocess.run(["Rscript", "-e", _R_EXPORT], check=True, capture_output=True, text=True).stdout
    )
    base = lmList_formula("distance ~ age | Subject", data=frame)
    fm1 = _as_lm_list_fit(base, ortho, frame, payload)
    fm2 = _as_lme_fit(ortho, frame, payload)
    return OrthodontFixtures(data=ortho, fm1=fm1, fm2=fm2)


def _orthodont_grouped():
    from nlme.astable import GroupedData

    response = (
        26, 25, 29, 31, 21.5, 22.5, 23, 26.5, 23, 22.5, 24, 27.5, 25.5, 27.5, 26.5,
        27, 20, 23.5, 22.5, 26, 24.5, 25.5, 27, 28.5, 22, 22, 24.5, 26.5, 24, 21.5,
        24.5, 25.5, 23, 20.5, 31, 26, 27.5, 28, 31, 31.5, 23, 23, 23.5, 25, 21.5,
        23.5, 24, 28, 17, 24.5, 26, 29.5, 22.5, 25.5, 25.5, 26, 23, 24.5, 26, 30,
        22, 21.5, 23.5, 25, 21, 20, 21.5, 23, 21, 21.5, 24, 25.5, 20.5, 24, 24.5,
        26, 23.5, 24.5, 25, 26.5, 21.5, 23, 22.5, 23.5, 20, 21, 21, 22.5, 21.5,
        22.5, 23, 25, 23, 23, 23.5, 24, 20, 21, 22, 21.5, 16.5, 19, 19, 19.5, 24.5,
        25, 28, 28,
    )
    covariate = (8, 10, 12, 14) * 27
    groups = (
        "M01", "M01", "M01", "M01", "M02", "M02", "M02", "M02", "M03", "M03", "M03",
        "M03", "M04", "M04", "M04", "M04", "M05", "M05", "M05", "M05", "M06", "M06",
        "M06", "M06", "M07", "M07", "M07", "M07", "M08", "M08", "M08", "M08", "M09",
        "M09", "M09", "M09", "M10", "M10", "M10", "M10", "M11", "M11", "M11", "M11",
        "M12", "M12", "M12", "M12", "M13", "M13", "M13", "M13", "M14", "M14", "M14",
        "M14", "M15", "M15", "M15", "M15", "M16", "M16", "M16", "M16", "F01", "F01",
        "F01", "F01", "F02", "F02", "F02", "F02", "F03", "F03", "F03", "F03", "F04",
        "F04", "F04", "F04", "F05", "F05", "F05", "F05", "F06", "F06", "F06", "F06",
        "F07", "F07", "F07", "F07", "F08", "F08", "F08", "F08", "F09", "F09", "F09",
        "F09", "F10", "F10", "F10", "F10", "F11", "F11", "F11", "F11",
    )
    group_levels = (
        "M16", "M05", "M02", "M11", "M07", "M08", "M03", "M12", "M13", "M14", "M09",
        "M15", "M06", "M04", "M01", "M10", "F10", "F09", "F06", "F01", "F05", "F07",
        "F02", "F08", "F03", "F04", "F11",
    )
    frame = {
        "distance": list(response),
        "age": list(covariate),
        "Subject": list(groups),
    }

    @dataclass(slots=True)
    class _Grouped:
        columns: dict[str, list]
        formula: str = "distance ~ age | Subject"
        labels: dict[str, str] | None = None
        units: dict[str, str] | None = None
        classes: tuple[str, ...] = ("groupedData", "data.frame")
        group_levels: tuple[str, ...] = ()

    ortho = _Grouped(
        columns=frame,
        labels={
            "x": "Age",
            "y": "Distance from pituitary to pterygomaxillary fissure",
        },
        units={"x": "(yr)", "y": "(mm)"},
        group_levels=group_levels,
    )
    return ortho, frame


def _frame_dict(ortho) -> dict[str, list[Any]]:
    return {key: list(np.asarray(values).ravel()) for key, values in ortho.columns.items()}


def _as_lm_list_fit(base: LmList, ortho, frame: dict[str, list[Any]], payload: dict) -> LmListFit:
    @dataclass(slots=True)
    class _Call:
        data: Any
        formula: str = "distance ~ age | Subject"

    return LmListFit(
        entries=base.entries,
        level=base.level,
        pool=base.pool,
        groups_form=base.groups_form,
        group_names=base.group_names,
        labels=base.labels,
        units=base.units,
        call=_Call(data=ortho),
        fitted_values=np.asarray(payload["lm_fitted"], dtype=np.float64),
        resid_values=np.asarray(payload["lm_resid"], dtype=np.float64),
        groups_vector=list(frame["Subject"]),
    )


def _as_lme_fit(ortho, frame: dict[str, list[Any]], payload: dict) -> LmeFit:
    rn = payload["random"]["rn"]
    cn = payload["random"]["cn"]
    nrow = len(rn)
    ncol = len(cn)
    random = np.array(payload["random"]["v"], dtype=np.float64).reshape(nrow, ncol, order="F")
    return LmeFit(
        call=LmeCall(data=ortho),
        dims=LmeDims(Q=int(payload["Q"][0] if isinstance(payload["Q"], list) else payload["Q"])),
        groups={"Subject": list(payload["groups"])},
        group_colnames=("Subject",),
        group_level_labels=tuple(str(item) for item in payload["group_levels"]),
        coefficients=LmeCoefficients(
            fixed=np.asarray(payload["fixef"], dtype=np.float64),
            fixed_names=("(Intercept)", "age"),
            random={"Subject": random},
            random_rownames={"Subject": tuple(str(item) for item in rn)},
            random_colnames={"Subject": tuple(str(item) for item in cn)},
        ),
        formula="distance ~ age",
        fitted_values=np.asarray(payload["fitted"], dtype=np.float64),
        resid_values=np.asarray(payload["resid"], dtype=np.float64),
        labels=ortho.labels,
        units=ortho.units,
    )
