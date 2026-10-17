"""Coordinate configurations for correspondence-analysis results."""

import numpy as np


def cacoord(obj, type="standard", dim=None, rows=None, cols=None, **_):
    if type not in {
        "standard", "principal", "symmetric", "rowprincipal",
        "colprincipal", "symbiplot", "rowgab", "colgab",
        "rowgreen", "colgreen",
    }:
        raise ValueError("invalid coordinate type")
    r = np.asarray(obj["rowcoord"], dtype=float)
    c = np.asarray(obj["colcoord"], dtype=float)
    sv = np.asarray(obj["sv"], dtype=float)
    rm = np.asarray(obj["rowmass"], dtype=float)
    cm = np.asarray(obj["colmass"], dtype=float)
    if dim is not None:
        d = np.asarray(dim).ravel().astype(int)
        if d.size and np.all((d >= 1) & (d <= r.shape[1])):
            d = d - 1
        r, c, sv = r[:, d], c[:, d], sv[d]
    if type == "standard":
        x, y = r, c
    else:
        rpc, cpc = r * sv, c * sv
        if type == "principal":
            x, y = rpc, cpc
        elif type == "symmetric":
            x, y = r * np.sqrt(sv), c * np.sqrt(sv)
        elif type == "rowprincipal":
            x, y = rpc, c
        elif type == "colprincipal":
            x, y = r, cpc
        elif type == "symbiplot":
            x, y = r * np.sqrt(sv), c * np.sqrt(sv)
        elif type == "rowgab":
            x, y = rpc, c * cm[:, None]
        elif type == "colgab":
            x, y = r * rm[:, None], cpc
        elif type == "rowgreen":
            x, y = rpc, c * np.sqrt(cm)[:, None]
        else:
            x, y = r * np.sqrt(rm)[:, None], cpc
    want_rows = rows is None or bool(rows)
    want_cols = cols is None or bool(cols)
    if want_rows and want_cols:
        return {"rows": x, "columns": y}
    return x if want_rows else y
