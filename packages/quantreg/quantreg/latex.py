"""LaTeX reporting helpers from quantreg."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np


def _r_format(value: Any, digits: int | None = None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    if isinstance(value, str):
        return value
    number = float(value)
    if digits is None:
        return f"{number:g}"
    return f"{number:.{int(digits)}g}"


def latex_table(
    x,
    file: str | Path | None = None,
    rowlabel: str | None = None,
    rowlabel_just: str = "l",
    cgroup=None,
    n_cgroup=None,
    rgroup=None,
    n_rgroup=None,
    digits=None,
    dec=None,
    rdec=None,
    cdec=None,
    append: bool = False,
    dcolumn: bool = False,
    cdot: bool = False,
    longtable: bool = False,
    table_env: bool = True,
    lines_page: int = 40,
    caption: str | None = None,
    caption_lot: str | None = None,
    label: str | None = None,
    double_slash: bool = False,
    **kwargs,
) -> str:
    """Return the LaTeX emitted by quantreg's ``latex.table``.

    ``file`` is accepted for R compatibility.  Unlike R's invisible return,
    Python always returns the generated text; when supplied, it is also
    written to ``file + '.tex'``.
    """
    del lines_page
    values = np.asarray(x, dtype=object)
    if values.ndim != 2:
        values = np.atleast_2d(values)
    nr, nc = values.shape
    row_names = kwargs.get("_row_names", list(getattr(x, "index", []))) or [str(i + 1) for i in range(nr)]
    col_names = kwargs.get("_col_names", list(getattr(x, "columns", []))) or [str(i + 1) for i in range(nc)]
    if rowlabel is None:
        rowlabel = str(file) if file is not None else None
    if label is None and file is not None:
        label = str(file)
    if dec is not None:
        decimals = np.broadcast_to(np.asarray(dec), (nr, nc))
    elif rdec is not None:
        decimals = np.broadcast_to(np.asarray(rdec).reshape(-1, 1), (nr, nc))
    elif cdec is not None:
        decimals = np.broadcast_to(np.asarray(cdec).reshape(1, -1), (nr, nc))
    else:
        decimals = None
    cells = []
    for i in range(nr):
        row = []
        for j in range(nc):
            value = values[i, j]
            if decimals is not None and value is not None:
                try:
                    value = round(float(value), int(decimals[i, j]))
                except (TypeError, ValueError):
                    pass
            text = _r_format(value, digits)
            if dcolumn:
                row.append(text)
            else:
                text = text.replace(" ", "~")
                if cdot and text:
                    text = "$" + text.replace(".", r"\cdot") + "$"
                row.append(text)
        cells.append(row)
    slash = r"\\" if double_slash else "\\"
    rjust = "l" if rowlabel_just == "l" else "c"
    sep = "." if dcolumn else "c"
    row_prefix = f"|{rjust}|" if rowlabel is not None else ""
    form = row_prefix + "|" + "|".join([sep] * nc) + "|"
    out = io.StringIO()
    out.write(f"% {kwargs.get('_call', 'latex.table(x = x)')} \n%\n")
    if dcolumn:
        out.write(f"{slash}newcolumn{{.}}{{D{{.}}{{{slash}cdot}}{{-1}}}}\n")
    if not longtable:
        if table_env:
            out.write(f"{slash}begin{{table}}[hptb]\n")
            if caption is not None:
                cap = f"{slash}caption"
                if caption_lot is not None:
                    cap += f"[{caption_lot}]"
                cap += "{" + caption
                if label is not None:
                    cap += f"{slash}label{{{label}}}"
                out.write(cap + "}\n")
        out.write(f"{slash}begin{{center}}\n")
        out.write(f"{slash}begin{{tabular}}{{{form}}} {slash}hline\n")
    else:
        out.write(f"{slash}setlongtables\n{slash}begin{{longtable}}{{{form}}}\n")
        if caption is not None:
            out.write(f"{slash}caption{{{caption}}}{slash}{slash}\n")
        out.write(f"{slash}hline\n")
    if cgroup is not None:
        groups = list(cgroup)
        counts = list(n_cgroup) if n_cgroup is not None else [nc // len(groups)] * len(groups)
        labels = [f"{slash}bf {name}" for name in groups]
        if rowlabel is not None:
            labels = [f"{slash}multicolumn{{1}}{{|{rjust}||}}{{{slash}bf {rowlabel}}}"] + [
                f"{slash}multicolumn{{{count}}}{{c|}}{{{name}}}" for count, name in zip(counts, labels)
            ]
        else:
            labels = [f"{slash}multicolumn{{{count}}}{{c|}}{{{name}}}" for count, name in zip(counts, labels)]
        out.write("&".join(labels) + f"{slash}{slash} {slash}cline{{2-{nc + 1}}}\n")
    headers = ([rowlabel] if rowlabel is not None else []) + col_names
    if rowlabel is None:
        header_cells = [f"{slash}multicolumn{{1}}{{|c|}}{{{headers[0]}}}"]
        header_cells += [f"{slash}multicolumn{{1}}{{c|}}{{{name}}}" for name in headers[1:]]
    else:
        header_cells = [f"{slash}multicolumn{{1}}{{|{rjust}||}}{{{headers[0]}}}"]
        header_cells += [f"{slash}multicolumn{{1}}{{c|}}{{{name}}}" for name in headers[1:]]
    out.write("&".join(header_cells) + f"{slash}{slash} {slash}hline\n")
    for name, row in zip(row_names, cells):
        out.write("&".join(([str(name)] if rowlabel is not None else []) + row))
        out.write(f"{slash}{slash} \n")
    out.write(f"{slash}hline\n")
    if longtable:
        out.write(f"{slash}end{{longtable}}\n")
    else:
        out.write(f"{slash}end{{tabular}}\n")
        if caption is not None:
            out.write(f"{slash}vspace{{3mm}}\n")
        out.write(f"{slash}end{{center}}\n")
        if table_env:
            out.write(f"{slash}end{{table}}\n")
    text = out.getvalue()
    if file is not None:
        target = Path(file)
        if target.suffix != ".tex":
            target = target.with_name(target.name + ".tex")
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8") as stream:
            stream.write(text)
    return text


def latex_summary_rqs(x, transpose: bool = False, caption: str = "caption goes here.",
                      digits: int = 3, file=None, **kwargs) -> str:
    """Render a list of quantile-regression summaries as a LaTeX table."""
    summaries = list(x)
    taus = [_r_format(round(float(piece["tau"]), digits), None) for piece in summaries]
    coefficients = [np.asarray(piece["coefficients"], dtype=float) for piece in summaries]
    p, k = coefficients[0].shape
    table = np.empty((p, len(summaries)), dtype=object)
    max_decimals = max(
        len(f"{float(value):.12f}".rstrip("0").split(".")[-1])
        for coefficient in coefficients for value in coefficient.flat
    )
    for i, coefficient in enumerate(coefficients):
        for j in range(p):
            a = [f"{round(float(v), digits):.{max_decimals}f}" for v in coefficient[j]]
            if k == 3:
                table[j, i] = f"$\\underset{{({a[1]},{a[2]})}}{{{a[0]}}}$"
            elif k == 4:
                table[j, i] = f"$\\underset{{({a[1]})}}{{{a[0]}}}$"
            else:
                table[j, i] = ""
    row_names = list(summaries[0].get("names", [str(i + 1) for i in range(p)]))
    col_names = taus
    if transpose:
        table = table.T
        row_names, col_names = col_names, row_names
    return latex_table(table, file=file, rowlabel="Quantiles" if transpose else "Covariates",
                       caption=caption, _row_names=row_names, _col_names=col_names,
                       _call="latex.table(x = table, file = file, rowlabel = rowlabel, caption = caption)",
                       **kwargs)


def latex_table_rq(x, **_) -> None:
    """Defunct S3 method retained for compatibility."""
    return "table.rq and related methods are defunct -- see rq, which now accepts a vector of taus."


def table_rq(x, **_) -> None:
    raise RuntimeError("table.rq now defunct, rq() now accepts vector tau argument.  See ?rq.")


def latex(x, **kwargs):
    if isinstance(x, (list, tuple)):
        return latex_summary_rqs(x, **kwargs)
    raise TypeError("no latex method for this object")
