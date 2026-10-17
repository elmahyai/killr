"""Python translation of the string-building part of htmlTable."""

import html as _html
import math
import re
import warnings


_theme = None
_PRESETS = {
    "warning": "background-color: #fff3cd; color: #856404;",
    "info": "background-color: #d1ecf1; color: #0c5460;",
    "success": "background-color: #d4edda; color: #155724;",
    "muted": "background-color: #f8f9fa; color: #6c757d;",
}


def txtInt(x, language="en", html=True, **kwargs):
    def one(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return ""
        if language == "en":
            return format(v, ",")
        if abs(v) >= 10**4:
            return format(v, ",").replace(",", "&nbsp;" if html else " ")
        return format(v, "g")
    if isinstance(x, (list, tuple)):
        return [one(v) for v in x]
    return one(x)


def outputInt(*args, **kwargs):
    warnings.warn("outputInt is deprecated, use txtInt() instead.", stacklevel=2)
    return txtInt(*args, **kwargs)


def txtPval(pvalues, lim_2dec=10**-2, lim_sig=10**-4, html=True, **kwargs):
    lt = "&lt; " if html is True else "< "
    if isinstance(html, str):
        lt = html
    def one(x):
        try:
            x = float(x)
        except (TypeError, ValueError):
            return str(x)
        if x < lim_sig:
            return f"{lt}{lim_sig:g}"
        if x > lim_2dec:
            return f"{x:.{max(0, -math.floor(math.log10(x)) + 1)}g}"
        return f"{x:.1g}"
    return [one(x) for x in pvalues] if isinstance(pvalues, (list, tuple)) else one(pvalues)


def pvalueFormatter(*args, **kwargs):
    warnings.warn("pvalueFormatter is deprecated, use txtPval() instead.", stacklevel=2)
    return txtPval(*args, **kwargs)


def txtMergeLines(*args, html=5):
    vals = []
    for arg in args:
        vals.extend(arg if isinstance(arg, (list, tuple)) else [arg])
    if not vals:
        return ""
    if len(vals) == 1:
        vals = re.split(r"\n[ ]*", str(vals[0]))
    vals = [str(v) for v in vals]
    if len(vals) == 1:
        return vals[0]
    if html is False:
        return r"\vbox{" + "".join(
            (r"\hbox{\strut " if i == 0 else "") + v + (r"}" if i == 0 else r"\hbox{\strut " + v + "}")
            for i, v in enumerate(vals)
        ) + "}"
    br = "<br>\n" if html == 5 else "<br />\n"
    return "".join((v if i == 0 else br + v) for i, v in enumerate(vals))


def splitLines4Table(*args, **kwargs):
    warnings.warn("splitLines4Table is deprecated, use txtMergeLines() instead.", stacklevel=2)
    return txtMergeLines(*args, **kwargs)


def _style(*styles):
    parts = []
    names = {}
    for style in styles:
        if style is None or style == "" or style == "none":
            continue
        if isinstance(style, dict):
            for k, v in style.items():
                if v is not None and v != "":
                    names[k] = str(v)
        elif isinstance(style, (list, tuple)):
            for item in style:
                if isinstance(item, str) and item:
                    parts.extend(re.split(r";\s*", item.strip("; ")))
        else:
            parts.extend(re.split(r";\s*", str(style).strip("; ")))
    parts.extend(f"{k}: {v}" for k, v in names.items())
    out = []
    for part in parts:
        if ":" not in part:
            continue
        key = part.split(":", 1)[0].strip()
        out = [p for p in out if p.split(":", 1)[0].strip() != key]
        out.append(part.strip() + ";")
    return " ".join(out)


def getHtmlTableTheme():
    global _theme
    if _theme is not None:
        return dict(_theme)
    return {
        "align": "c", "align.header": "c", "col.rgroup": "none", "col.columns": "none",
        "padding.rgroup": "&nbsp;&nbsp;", "padding.tspanner": "",
        "spacer.celltype": "single_empty", "spacer.css.cgroup.bottom.border": "none",
        "spacer.css": "", "spacer.content": "&nbsp;", "css.rgroup": "font-weight: 900;",
        "css.rgroup.sep": "", "css.tspanner": "font-weight: 900; text-align: left;",
        "css.tspanner.sep": "border-top: 1px solid #BEBEBE;",
        "css.total": "border-top: 1px solid #BEBEBE; font-weight: 900;",
        "css.cell": "", "css.cgroup": "", "css.header": "font-weight: 900",
        "css.header.border_bottom": "border-bottom: 1px solid grey",
        "css.class": "gmisc_table", "css.table": "margin-top: 1em; margin-bottom: 1em;",
        "pos.rowlabel": "bottom", "pos.caption": "top",
    }


def setHtmlTableTheme(theme=None, **styles):
    global _theme
    base = getHtmlTableTheme() if theme is None else (dict(theme) if isinstance(theme, dict) else getHtmlTableTheme())
    base.update({k: v for k, v in styles.items() if v is not None})
    _theme = base
    return dict(base)


def addHtmlTableStyle(x, **styles):
    out = x
    if isinstance(x, dict):
        out = dict(x)
    style = dict(getattr(x, "_htmlTable_style", {}) or {})
    style.update({k: v for k, v in styles.items() if v is not None})
    if hasattr(out, "__dict__"):
        out._htmlTable_style = style
    return out


def getHtmlTableStyle(x):
    return getattr(x, "_htmlTable_style", None)


def hasHtmlTableStyle(x, style_name):
    style = getHtmlTableStyle(x)
    return bool(style and style.get(style_name) is not None)


def highlightRow(x, condition, style="warning"):
    out = addHtmlTableStyle(x)
    rules = list(getHtmlTableStyle(out).get("row.highlight", []))
    css = _PRESETS.get(str(style).lower(), f"background-color: {style};") if isinstance(style, str) else _style(style)
    rules.append((condition, css))
    getHtmlTableStyle(out)["row.highlight"] = rules
    return out


def _rows(x):
    if isinstance(x, dict):
        keys = list(x)
        return keys, [list(row) for row in zip(*(x[k] for k in keys))]
    if hasattr(x, "to_numpy") and hasattr(x, "columns"):
        return list(x.columns), x.to_numpy().tolist()
    rows = x.tolist() if hasattr(x, "tolist") else x
    if not rows:
        return [], []
    return None, [list(r) if isinstance(r, (list, tuple)) else [r] for r in rows]


def htmlTable(x, header=None, rnames=None, rowlabel=None, caption=None, tfoot=None,
              label=None, rgroup=None, n_rgroup=None, cgroup=None, n_cgroup=None,
              tspanner=None, total=None, ctable=True, compatibility="LibreOffice",
              escape_html=False, **kwargs):
    cols, rows = _rows(x)
    if header is None:
        header = cols
    ncol = len(rows[0]) if rows else len(header or [])
    if escape_html:
        esc = lambda v: _html.escape(str(v), quote=False)
    else:
        esc = lambda v: str(v)
    theme = getHtmlTableTheme()
    cls = theme.get("css.class", "gmisc_table")
    table_id = f" id='{label}'" if label else ""
    out = [f"<table class='{cls}' style='border-collapse: collapse; {theme.get('css.table','')}'{table_id}>"]
    if caption is not None:
        out.append(f"<caption>{esc(caption)}</caption>")
    if header is not None:
        out.append("<thead><tr>")
        if rnames is not False and rnames is not None:
            out.append(f"<th style='{theme.get('css.header','')}'>{esc(rowlabel or '')}</th>")
        out.extend(f"<th style='{theme.get('css.header','')}'>{esc(v)}</th>" for v in header)
        out.append("</tr></thead>")
    out.append("<tbody>")
    for i, row in enumerate(rows):
        out.append("<tr>")
        if rnames is not False and rnames is not None:
            rn = rnames[i] if i < len(rnames) else ""
            out.append(f"<td>{esc(rn)}</td>")
        out.extend(f"<td>{esc(v)}</td>" for v in row)
        out.append("</tr>")
    out.append("</tbody>")
    if tfoot is not None:
        out.append(f"<tfoot><tr><td colspan='{ncol}'>{txtMergeLines(tfoot)}</td></tr></tfoot>")
    out.append("</table>")
    return "\n".join(out)


def concatHtmlTables(tables, headers=None):
    if headers is None:
        headers = [f"<h1>Table no. {i + 1}</h1>" for i in range(len(tables))]
    else:
        headers = (list(headers) * len(tables))[:len(tables)] if isinstance(headers, (list, tuple)) else [headers] * len(tables)
    return "".join(f"{h}{t}" for h, t in zip(headers, tables))


def htmlTableWidget(x, number_of_entries=(10, 25, 100), **kwargs):
    return {"thetable": htmlTable(x, **kwargs), "options": {"number_of_entries": list(number_of_entries)}}


def htmlTableWidgetOutput(outputId, width="100%", height="400px"):
    return {"outputId": outputId, "name": "htmlTableWidget", "width": width, "height": height}


def renderHtmlTableWidget(expr, env=None, quoted=False):
    return expr if quoted else expr()
