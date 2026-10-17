"""The rpart fit and the functions that read it."""

from __future__ import annotations

import math
import sys
from copy import deepcopy
from pathlib import Path

_PACKAGES = Path(__file__).resolve().parents[2]
if str(_PACKAGES / "boot") not in sys.path:
    sys.path.insert(0, str(_PACKAGES / "boot"))
from boot.rng import sample_int  # noqa: E402

from rpart.control import rpart_control
from rpart.tree import grow_anova, xpred_anova

_EPS = sys.float_info.epsilon


class Rpart:
    """An anova tree and the tables R stores on the fit."""

    def __init__(self):
        self.frame = []
        self.splits = []
        self.where = []
        self.cptable = []
        self.method = "anova"
        self.control = {}
        self.y = []
        self.x = []
        self.wt = []
        self.var_names = []
        self.variable_importance = []
        self.iscale = 0.0
        self.numresp = 1
        self.na_action = []


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _columns(data):
    if isinstance(data, dict):
        names = list(data.keys())
        columns = {name: list(data[name]) for name in names}
        return names, columns
    raise TypeError("data must be a dict of columns")


def na_rpart(x, response=None):
    """Drop empty rows, or rows with a missing response or no predictors.

    ``x`` is a dict of columns. ``response`` is a column name. With no
    response, a row is dropped only when every column is missing, which is
    what ``na.rpart`` does to a frame that has no terms.
    """
    names, columns = _columns(x)
    n = len(columns[names[0]]) if names else 0
    keep = []
    dropped = []
    for i in range(n):
        if response is None:
            alive = any(not _missing(columns[name][i]) for name in names)
        else:
            predictors = [name for name in names if name != response]
            y_ok = not _missing(columns[response][i])
            x_ok = any(not _missing(columns[name][i]) for name in predictors) if predictors else True
            alive = y_ok and x_ok
        if alive:
            keep.append(i)
        else:
            dropped.append(i + 1)
    kept = {name: [columns[name][i] for i in keep] for name in names}
    return {"data": kept, "na_action": dropped, "rows": [i + 1 for i in keep]}


def _parse_formula(formula, names, y_default):
    text = formula.replace(" ", "")
    if "~" not in text:
        raise ValueError("a formula is required")
    left, right = text.split("~", 1)
    yname = left or y_default
    if right == ".":
        xnames = [name for name in names if name != yname]
    else:
        xnames = [part for part in right.split("+") if part]
    return yname, xnames


def _importance(frame, splits, method):
    interior = [i for i, row in enumerate(frame) if row["var"] != "<leaf>"]
    if not interior:
        return []
    cursor = 0
    primary_at = []
    for i in interior:
        primary_at.append(cursor)
        cursor += frame[i]["ncompete"] + frame[i]["nsurrogate"] + 1
    totals = {}
    order = []
    scaled = []
    for slot, i in enumerate(interior):
        value = splits[primary_at[slot]]["improve"]
        if method == "anova":
            value *= frame[i]["dev"]
        scaled.append(value)
        name = frame[i]["var"]
        if name not in totals:
            order.append(name)
            totals[name] = 0.0
        totals[name] += value
    for slot, i in enumerate(interior):
        count = frame[i]["nsurrogate"]
        if count <= 0:
            continue
        start = primary_at[slot] + frame[i]["ncompete"] + 1
        for spl in splits[start:start + count]:
            name = spl["var"]
            if name not in totals:
                order.append(name)
                totals[name] = 0.0
            totals[name] += scaled[slot] * spl["adj"]
    ranked = sorted(order, key=lambda name: (-totals[name], name))
    return [(name, totals[name]) for name in ranked]


def _assemble(grown, var_names, control):
    fit = Rpart()
    fit.control = dict(control)
    fit.method = "anova"
    fit.y = grown["y"]
    fit.x = grown["x"]
    fit.wt = grown["wt"]
    fit.var_names = list(var_names)
    fit.iscale = grown["iscale"]
    fit.where = list(grown["where"])
    fit.cptable = [list(row) for row in grown["cptable"]]
    splits = []
    for spl in grown["splits"]:
        splits.append({
            "var": var_names[spl["var"]],
            "count": spl["count"],
            "ncat": spl["ncat"],
            "improve": spl["improve"],
            "index": spl["index"],
            "adj": spl["adj"],
        })
    fit.splits = splits
    frame = []
    for node in grown["nodes"]:
        terminal = node["nprimary"] == 0
        if terminal:
            var = "<leaf>"
            ncompete = 0
            nsurrogate = 0
        else:
            var = splits[node["split_index"] - 1]["var"]
            ncompete = max(0, node["nprimary"] - 1)
            nsurrogate = node["nsurrogate"]
        frame.append({
            "id": node["id"],
            "var": var,
            "n": node["n"],
            "wt": node["wt"],
            "dev": node["risk"],
            "yval": node["yval"],
            "complexity": node["complexity"],
            "ncompete": ncompete,
            "nsurrogate": nsurrogate,
        })
    fit.frame = frame
    fit.variable_importance = _importance(frame, splits, "anova")
    return fit


def rpart(formula, data, weights=None, method=None, control=None, cost=None, na_action=True, **kwargs):
    """Grow an anova tree. ``data`` is a dict of columns and ``formula`` is ``y ~ .``."""
    names, columns = _columns(data)
    yname, xnames = _parse_formula(formula, names, names[0])
    if method not in (None, "anova"):
        raise ValueError("only the anova method is implemented")
    if na_action:
        kept = na_rpart(columns, response=yname)
        columns = kept["data"]
        dropped = kept["na_action"]
    else:
        dropped = []
    y = [float(value) for value in columns[yname]]
    x = [[columns[name][i] for name in xnames] for i in range(len(y))]
    for row in x:
        for j, value in enumerate(row):
            row[j] = float("nan") if _missing(value) else float(value)
    if weights is None:
        wt = None
    else:
        if na_action and dropped:
            keep_rows = [i for i in range(len(weights)) if (i + 1) not in set(dropped)]
            wt = [float(weights[i]) for i in keep_rows]
        else:
            wt = [float(value) for value in weights]
    if control is None:
        controls = rpart_control(**kwargs)
    elif isinstance(control, dict):
        controls = rpart_control(**control)
    else:
        controls = control
    if cost is not None and len(cost) != len(xnames):
        raise ValueError("Cost vector is the wrong length")
    grown = grow_anova(y, x, wt=wt, control=controls, cost=cost)
    fit = _assemble(grown, xnames, controls)
    fit.na_action = dropped
    return fit


def meanvar(tree):
    """Leaf mean and mean deviance. R draws them and returns the three vectors."""
    if tree.method != "anova":
        raise ValueError("Plot not useful for classification or poisson trees")
    leaves = [row for row in tree.frame if row["var"] == "<leaf>"]
    return {
        "x": [row["yval"] for row in leaves],
        "y": [row["dev"] / row["n"] for row in leaves],
        "label": [str(row["id"]) for row in leaves],
    }


def printcp(x):
    """The complexity table ``printcp`` returns."""
    return [list(row) for row in x.cptable]


def _geometric_cp(cp0):
    previous = [float("inf")] + list(cp0[:-1])
    return [math.sqrt(value * prior) for value, prior in zip(cp0, previous)]


def plotcp(x, minline=True, upper="size"):
    """The series ``plotcp`` draws. R returns NULL after the plot."""
    table = x.cptable
    if not table or len(table[0]) < 5:
        raise ValueError("cptable does not contain cross-validation results")
    xerror = [row[3] for row in table]
    xstd = [row[4] for row in table]
    nsplit = [row[1] for row in table]
    geometric = _geometric_cp([row[0] for row in table])
    low = min(err - std for err, std in zip(xerror, xstd)) - 0.1
    high = max(err + std for err, std in zip(xerror, xstd)) + 0.1
    best = min(range(len(xerror)), key=lambda i: (xerror[i], i))
    return {
        "nsplit": nsplit,
        "xerror": xerror,
        "xstd": xstd,
        "cp": geometric,
        "ylim": [low, high],
        "hline": (xerror[best] + xstd[best]) if minline else None,
        "upper": upper,
    }


def rsq_rpart(x):
    """Apparent and cross-validated R-squared, the two series ``rsq.rpart`` draws."""
    table = printcp(x)
    if len(table[0]) < 5:
        raise ValueError("cptable does not contain cross-validation results")
    rel = [row[2] for row in table]
    xerror = [row[3] for row in table]
    xstd = [row[4] for row in table]
    return {
        "apparent": [1.0 - value for value in rel],
        "x_relative": [1.0 - value for value in xerror],
        "xerror": xerror,
        "xstd": xstd,
        "nsplit": [row[1] for row in table],
    }


def _descendants(nodes, include=True):
    n = len(nodes)
    desc = [[False] * n for _ in range(n)]
    if n == 1:
        return [[True]]
    if include:
        for i in range(n):
            desc[i][i] = True
    first = {}
    for i, node in enumerate(nodes):
        if node not in first:
            first[node] = i + 1
    parents = [first.get(node // 2, 0) for node in nodes]
    levels = [node.bit_length() - 1 for node in nodes]
    for col in range(1, n):
        desc[0][col] = True
    if max(levels) < 2:
        return desc
    for level in range(max(levels), 1, -1):
        for j in range(n):
            if levels[j] != level:
                continue
            parent = parents[j]
            if parent > 0:
                desc[parent - 1][j] = True
                parents[j] = parents[parent - 1]
            levels[j] = level - 1
    return desc


def _node_match(nodes, nodelist):
    found = []
    for node in nodes:
        try:
            found.append(nodelist.index(node) + 1)
        except ValueError:
            continue
    return found


def _labels(tree, digits=4):
    frame = tree.frame
    n = len(frame)
    if n == 1:
        return ["root"]
    whichrow = [row["var"] != "<leaf>" for row in frame]
    index = []
    cursor = 1
    for row, interior in zip(frame, whichrow):
        index.append(cursor)
        cursor += row["ncompete"] + row["nsurrogate"] + (1 if interior else 0)
    irow = [index[i] for i, interior in enumerate(whichrow) if interior]
    ncat = [tree.splits[row - 1]["ncat"] for row in irow]
    lsplit = [""] * len(irow)
    rsplit = [""] * len(irow)
    spec = "." + str(int(digits)) + "g"
    for j, cat in enumerate(ncat):
        if cat >= 2:
            continue
        cut = format(tree.splits[irow[j] - 1]["index"], spec)
        if cat < 0:
            lsplit[j] = "< " + cut
            rsplit[j] = ">=" + cut
        else:
            lsplit[j] = ">=" + cut
            rsplit[j] = "< " + cut
    node = [row["id"] for row in frame]
    interior_ids = [node[i] for i, interior in enumerate(whichrow) if interior]
    parent = []
    for ident in node:
        parent_id = ident // 2
        parent.append(interior_ids.index(parent_id) + 1 if parent_id in interior_ids else 0)
    vnames = [frame[i]["var"] for i, interior in enumerate(whichrow) if interior]
    labels = [""] * n
    for i, ident in enumerate(node):
        if i == 0:
            labels[i] = "root"
            continue
        slot = parent[i] - 1
        piece = rsplit[slot] if ident % 2 else lsplit[slot]
        labels[i] = vnames[slot] + piece
    return labels


def path_rpart(tree, nodes, pretty=0, print_it=False):
    """Labels along the path from the root to each node."""
    del pretty, print_it
    labels = _labels(tree)
    node = [row["id"] for row in tree.frame]
    matched = _node_match(list(nodes), node)
    if not matched:
        return {}
    which = _descendants(node)
    path = {}
    for index in matched:
        column = index - 1
        path[str(node[column])] = [labels[row] for row in range(len(node)) if which[row][column]]
    return path


def snip_rpart(x, toss):
    """Drop the named nodes and everything below them. Node ids, not row numbers."""
    tree = deepcopy(x)
    frame = tree.frame
    ident = [row["id"] for row in frame]
    n = len(ident)
    wanted = []
    for node in dict.fromkeys(toss):
        if node in ident:
            wanted.append(node)
    id2 = ident[:]
    while any(value > 1 for value in id2):
        id2 = [value // 2 for value in id2]
        extra = [ident[i] for i, value in enumerate(id2) if value in wanted]
        for i, value in enumerate(id2):
            if value in wanted:
                id2[i] = 0
        wanted.extend(extra)
    keep_rows = [i + 1 for i, value in enumerate(ident) if value not in wanted]
    parent_tossed = []
    for node in wanted:
        if (node // 2) not in wanted:
            parent_tossed.append(node)
    newleaf = [ident.index(node) + 1 for node in parent_tossed]
    owners = []
    for row_number, row in enumerate(frame, start=1):
        width = row["ncompete"] + row["nsurrogate"] + (0 if row["var"] == "<leaf>" else 1)
        owners.extend([row_number] * width)
    kept_splits = [spl for spl, owner in zip(tree.splits, owners) if owner in keep_rows]
    tree.splits = kept_splits
    for row_number in newleaf:
        frame[row_number - 1]["ncompete"] = 0
        frame[row_number - 1]["nsurrogate"] = 0
        frame[row_number - 1]["var"] = "<leaf>"
    order = sorted(keep_rows + newleaf)
    tree.frame = [frame[i - 1] for i in order]
    id3 = [ident[i - 1] for i in order]
    old_leaf = [ident[row - 1] for row in x.where]
    located = []
    for value in old_leaf:
        while value not in id3 and value > 0:
            value //= 2
        located.append(id3.index(value) + 1)
    tree.where = located
    return tree


def prune_rpart(tree, cp):
    """Snip every interior node whose complexity is at most ``cp``, then cut the table."""
    ident = [row["id"] for row in tree.frame]
    toss = [
        ident[i]
        for i, row in enumerate(tree.frame)
        if row["complexity"] <= cp and row["var"] != "<leaf>"
    ]
    if not toss:
        return deepcopy(tree)
    new = snip_rpart(tree, toss)
    lifted = [max(row[0], cp) for row in tree.cptable]
    seen = []
    for value in lifted:
        if value not in seen:
            seen.append(value)
    keep = [lifted.index(value) for value in seen]
    table = [list(tree.cptable[i]) for i in keep]
    table[-1][0] = cp
    new.cptable = table
    new.variable_importance = _importance(new.frame, new.splits, new.method)
    return new


def prune(tree, cp):
    return prune_rpart(tree, cp)


def xpred_rpart(fit, xval=10, cp=None, return_all=False):
    """Cross-validated predictions. ``return_all`` is unused for anova."""
    del return_all
    nobs = len(fit.y)
    if cp is None:
        column = [row[0] for row in fit.cptable]
        tail = column[:-1]
        cp = [math.sqrt(value * prior) for value, prior in zip(column, [10.0] + tail)]
        cp[0] = (1.0 + fit.cptable[0][0]) / 2.0
    if isinstance(xval, int):
        pool = [((i % xval) + 1) for i in range(nobs)]
        draw = sample_int(nobs)
        groups = [pool[slot - 1] for slot in draw]
        n_xval = xval
    else:
        groups = [int(value) for value in xval]
        n_xval = len(set(groups))
    return xpred_anova(
        fit.y,
        fit.x,
        fit.wt,
        fit.control,
        cp,
        fit.frame[0]["dev"],
        groups,
        n_xval,
        iscale=fit.iscale,
    )


def post(tree, title=None, filename="", digits=None, pretty=True, use_n=True, horizontal=True):
    """R's ``post.rpart`` only draws and returns NULL."""
    del tree, title, filename, digits, pretty, use_n, horizontal
    return None


def _cut_lowest(value, breaks):
    for k in range(1, len(breaks)):
        left_ok = value >= breaks[0] if k == 1 else value > breaks[k - 1]
        if left_ok and value <= breaks[k]:
            return k
    return len(breaks) - 1


def _approx(x, y, xout):
    out = []
    for value in xout:
        if value <= x[0]:
            out.append(y[0])
            continue
        if value >= x[-1]:
            out.append(y[-1])
            continue
        for i in range(1, len(x)):
            if value <= x[i]:
                span = x[i] - x[i - 1]
                weight = 0.0 if span == 0 else (value - x[i - 1]) / span
                out.append(y[i - 1] + weight * (y[i] - y[i - 1]))
                break
    return out


def _quantile_type7(values, probs):
    ordered = sorted(values)
    n = len(ordered)
    out = []
    for prob in probs:
        if prob <= 0:
            out.append(ordered[0])
            continue
        if prob >= 1:
            out.append(ordered[-1])
            continue
        rank = (n - 1) * prob + 1.0
        j = int(math.floor(rank))
        gamma = rank - j
        out.append((1.0 - gamma) * ordered[j - 1] + gamma * ordered[j])
    return out


def _keep_times(dtimes):
    n = len(dtimes)
    delta = _EPS * (dtimes[(3 * n) // 4] - dtimes[n // 4])
    keep = [1]
    last = dtimes[0]
    for value in dtimes[1:]:
        if value - last <= delta:
            keep.append(0)
        else:
            keep.append(1)
            last = value
    return [value for value, flag in zip(dtimes, keep) if flag]


def _rates(y, itable):
    ny = len(y[0])
    time = [row[ny - 2] for row in y]
    status = [row[ny - 1] for row in y]
    ilength = [itable[i + 1] - itable[i] for i in range(len(itable) - 1)]
    ngrp = len(ilength)
    index = [_cut_lowest(value, itable) for value in time]
    itime = [time[i] - itable[index[i] - 1] for i in range(len(time))]
    counts = [0] * ngrp
    time_in = [0.0] * ngrp
    deaths = [0.0] * ngrp
    for i, bin_id in enumerate(index):
        counts[bin_id - 1] += 1
        time_in[bin_id - 1] += itime[i]
        deaths[bin_id - 1] += status[i]
    temp = [0] * ngrp
    running = 0
    for i in range(ngrp - 1, -1, -1):
        running += counts[i]
        temp[i] = running
    pyears = []
    for i in range(ngrp):
        later = temp[i + 1] if i + 1 < ngrp else 0
        pyears.append(ilength[i] * later + time_in[i])
    if ny == 3:
        start = [row[0] for row in y]
        index2 = [_cut_lowest(value, itable) for value in start]
        itime2 = [start[i] - itable[index2[i] - 1] for i in range(len(start))]
        counts2 = [0] * ngrp
        time2 = [0.0] * ngrp
        for i, bin_id in enumerate(index2):
            counts2[bin_id - 1] += 1
            time2[bin_id - 1] += itime2[i]
        temp2 = [0] * ngrp
        running = 0
        for i in range(ngrp - 1, -1, -1):
            running += counts2[i]
            temp2[i] = running
        # c(0, temp[-ngrp]) is 0 followed by every entry but the last.
        for i in range(ngrp):
            factor = 0.0 if i == 0 else temp2[i - 1]
            pyears[i] -= ilength[i] * factor + time2[i]
    return [deaths[i] / pyears[i] for i in range(ngrp)]


def rpart_exp(y, offset=None, parms=None, wt=None):
    """Rescale survival times so the cumulative hazard is the new time."""
    del wt
    rows = [list(row) for row in y]
    ny = len(rows[0])
    status = [row[ny - 1] for row in rows]
    time = [row[ny - 2] for row in rows]
    if any(row[0] <= 0 for row in rows):
        raise ValueError("Observation time must be > 0")
    if all(value == 0 for value in status):
        raise ValueError("No deaths in data set")
    dtimes = sorted({time[i] for i, flag in enumerate(status) if flag == 1})
    dtimes = _keep_times(dtimes)
    if len(dtimes) > 1000:
        dtimes = _quantile_type7(dtimes, [i / 1000 for i in range(1001)])
    itable = [0.0] + dtimes[:-1] + [max(time)]
    rate = _rates(rows, itable)
    cumhaz = [0.0]
    for i, value in enumerate(rate):
        cumhaz.append(cumhaz[-1] + value * (itable[i + 1] - itable[i]))
    newy = _approx(itable, cumhaz, time)
    if ny == 3:
        started = _approx(itable, cumhaz, [row[0] for row in rows])
        newy = [newy[i] - started[i] for i in range(len(newy))]
    if offset is not None and len(offset) == len(rows):
        newy = [newy[i] * math.exp(offset[i]) for i in range(len(newy))]
    if parms is None:
        shrink, method = 1.0, 1.0
    else:
        method = float(parms.get("method", 1))
        shrink = float(parms.get("shrink", 2 - method))
    second = [row[1] for row in rows]
    return {
        "y": [[newy[i], second[i]] for i in range(len(rows))],
        "parms": [shrink, method],
        "numresp": 2,
        "numy": 2,
    }
