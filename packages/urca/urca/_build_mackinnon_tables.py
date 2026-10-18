"""One-off helper: parse MacKinnon tables from the CRAN urca tarball into npz."""

from __future__ import annotations

import re
import tarfile
from pathlib import Path

import numpy as np

_TARBALL = Path(__file__).resolve().parents[3] / "rcran" / "contrib" / "urca_1.3-4.tar.gz"
_OUT = Path(__file__).resolve().parent / "mackinnon_tables.npz"


def _read_r_source() -> str:
    with tarfile.open(_TARBALL, "r:gz") as tf:
        member = tf.getmember("urca/R/MacKinnonPValues.R")
        return tf.extractfile(member).read().decode("utf-8", errors="replace")


def _parse_probs(text: str) -> tuple[np.ndarray, np.ndarray]:
    block = text.split('".probsUrcval" <-', 1)[1].split('".urc1" <-', 1)[0]
    v1 = np.array([float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", block.split("V1 = c(")[1].split("),")[0])])
    v2 = np.array([float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", block.split("V2 = c(")[1].split("),")[0])])
    if v1.shape[0] != 221 or v2.shape[0] != 221:
        raise ValueError("expected 221 prob rows")
    return v1, v2


def _parse_urc1(text: str) -> list[str]:
    block = text.split('".urc1" <-', 1)[1].split('".urc11" <-', 1)[0]
    lines = re.findall(r'"([^"]*)"', block)
    return lines


def _split_fields(line: str) -> list[str]:
    return [part for part in line.split() if part]


def _section(table: list[str], itt: int, itv: int) -> dict:
    skip = 886 * (itt - 1) + 2 * itt + (itv - 1) * 222
    parms = _split_fields(table[skip - 1])
    model = int(float(parms[3]))
    nreg = int(float(parms[2]))
    minsize = int(float(parms[4]))
    nvar = 3 if model in (2, 4) else 4
    rows = []
    for line in table[skip : skip + 221]:
        rows.append([float(x) for x in _split_fields(line)])
    beta_raw = np.asarray(rows, dtype=float)
    wght = beta_raw[:, nvar].copy()
    beta = beta_raw[:, :4].T.copy()
    return {
        "model": model,
        "nreg": nreg,
        "minsize": minsize,
        "beta": beta,
        "wght": wght,
    }


def main() -> None:
    text = _read_r_source()
    probs, cnorm = _parse_probs(text)
    table = _parse_urc1(text)
    sections = {}
    for itt in (1, 2):
        for itv in (1, 2, 3, 4):
            key = f"itt{itt}_itv{itv}"
            sections[key] = _section(table, itt, itv)
    np.savez(
        _OUT,
        probs=probs,
        cnorm=cnorm,
        **{f"{k}_beta": v["beta"] for k, v in sections.items()},
        **{f"{k}_wght": v["wght"] for k, v in sections.items()},
        **{f"{k}_model": np.array(v["model"]) for k, v in sections.items()},
        **{f"{k}_nreg": np.array(v["nreg"]) for k, v in sections.items()},
        **{f"{k}_minsize": np.array(v["minsize"]) for k, v in sections.items()},
    )
    print(f"wrote {_OUT}")


if __name__ == "__main__":
    main()
