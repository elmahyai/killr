"""The R-level randomForest helpers around a fitted forest."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from randomForest.model import RandomForest, random_forest


def _rng_state():
    import boot.rng as rng

    return rng._mt[:], rng._mti


def _restore_rng(state):
    import boot.rng as rng

    rng._mt[:] = state[0]
    rng._mti = state[1]


def treesize(forest, terminal=True):
    """Terminal-node counts, or every node, for each tree."""
    sizes = forest.forest["ndbigtree"]
    if terminal:
        return [(size + 1) / 2 for size in sizes]
    return list(sizes)


def get_tree(forest, k=1, label_var=False):
    """One tree as rows of daughter, variable, split, status, and prediction."""
    tree = k - 1
    size = forest.forest["ndbigtree"][tree]
    rows = []
    for node in range(size):
        if forest.type == "regression":
            left = forest.forest["left_daughter"][node][tree]
            right = forest.forest["right_daughter"][node][tree]
        else:
            left, right = forest.forest["treemap"][node][tree]
        rows.append([
            left,
            right,
            forest.forest["bestvar"][node][tree],
            forest.forest["xbestsplit"][node][tree],
            forest.forest["nodestatus"][node][tree],
            forest.forest["nodepred"][node][tree],
        ])
    if label_var:
        for row in rows:
            variable = row[2]
            row[2] = None if variable == 0 else forest.x_names[variable - 1]
            if forest.type == "classification":
                prediction = row[5]
                row[5] = None if prediction < 1 or prediction > len(forest.classes) else forest.classes[prediction - 1]
    return rows


def var_used(forest, by_tree=False, count=True):
    """How often each predictor is chosen as a split."""
    best = np.asarray(forest.forest["bestvar"], dtype=int)
    p = len(forest.forest["ncat"])
    if count:
        if by_tree:
            columns = []
            for tree in range(best.shape[1]):
                tally = [0] * p
                for value in best[:, tree]:
                    if value > 0:
                        tally[value - 1] += 1
                columns.append(tally)
            return columns
        tally = [0] * p
        for value in best.ravel():
            if value > 0:
                tally[value - 1] += 1
        return tally
    per_tree = []
    for tree in range(best.shape[1]):
        per_tree.append(sorted({int(value) for value in best[:, tree] if value > 0}))
    if by_tree:
        return per_tree
    widths = {len(column) for column in per_tree}
    if len(widths) == 1 and per_tree:
        rows = list(zip(*per_tree))
        seen = []
        for row in rows:
            if row not in seen:
                seen.append(row)
        return sorted(value for row in seen for value in row)
    return sorted({item for column in per_tree for item in column})


def importance(forest, type=None, class_label=None, scale=True):
    """Variable-importance columns, optionally scaled by their tree-to-tree SD."""
    table = np.array(forest.importance, dtype=float)
    if type == 2:
        return table[:, -1:].copy()
    if scale and forest.importance_sd is not None and table.shape[1] > 1:
        sd = np.array(forest.importance_sd, dtype=float)
        if sd.ndim == 1:
            sd = sd.reshape(-1, 1)
        scaled = table.copy()
        width = table.shape[1] - 1
        denom = sd[:, :width]
        denom = np.where(denom < np.finfo(float).eps, 1.0, denom)
        scaled[:, :width] = table[:, :width] / denom
        table = scaled
    if type is None:
        return table
    if type == 1 and class_label is None:
        return table[:, -2:-1].copy()
    if class_label is None:
        return table[:, :1].copy()
    names = list(forest.classes) + ["MeanDecreaseAccuracy", "MeanDecreaseGini"]
    if forest.type == "regression":
        names = ["%IncMSE", "IncNodePurity"]
    column = names.index(class_label)
    return table[:, column:column + 1].copy()


def _predict_rows(forest, matrix):
    data = np.asarray(matrix, dtype=float)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    n, _p = data.shape
    ntree = forest.ntree
    if forest.type == "regression":
        total = np.zeros(n)
        for tree in range(ntree):
            for row in range(n):
                node = 0
                while forest.forest["nodestatus"][node][tree] != -1:
                    variable = forest.forest["bestvar"][node][tree] - 1
                    if data[row, variable] <= forest.forest["xbestsplit"][node][tree]:
                        node = forest.forest["left_daughter"][node][tree] - 1
                    else:
                        node = forest.forest["right_daughter"][node][tree] - 1
                total[row] += forest.forest["nodepred"][node][tree]
        return total / ntree
    nclass = forest.forest["nclass"]
    votes = np.zeros((n, nclass))
    state = _rng_state()
    try:
        for tree in range(ntree):
            for row in range(n):
                node = 0
                while forest.forest["nodestatus"][node][tree] != -1:
                    variable = forest.forest["bestvar"][node][tree] - 1
                    left, right = forest.forest["treemap"][node][tree]
                    if data[row, variable] <= forest.forest["xbestsplit"][node][tree]:
                        node = left - 1
                    else:
                        node = right - 1
                votes[row, forest.forest["nodepred"][node][tree] - 1] += 1.0
        cutoff = forest.forest["cutoff"]
        labels = []
        for row in range(n):
            best = 0.0
            ntie = 1
            chosen = 1
            for j in range(nclass):
                crit = (votes[row, j] / ntree) / cutoff[j]
                if crit > best:
                    best = crit
                    chosen = j + 1
                    ntie = 1
                if crit == best:
                    ntie += 1
                    from boot.rng import unif
                    if unif() < 1.0 / ntie:
                        best = crit
                        chosen = j + 1
            labels.append(forest.classes[chosen - 1])
    finally:
        _restore_rng(state)
    return votes, labels


def predict(forest, newdata=None, type="response", norm_votes=True):
    """Predict from a kept forest. ``type`` is response, prob, or vote."""
    if newdata is None:
        if type == "response" or forest.type == "regression":
            return forest.predicted
        return forest.votes
    if forest.type == "regression":
        return _predict_rows(forest, newdata).tolist()
    votes, labels = _predict_rows(forest, newdata)
    if type in ("prob", "vote"):
        if norm_votes or type == "prob":
            totals = votes.sum(axis=1, keepdims=True)
            votes = votes / totals
        return votes.tolist()
    return labels


def combine(*forests):
    """Average several forests, weighting each by its number of trees."""
    first = forests[0]
    trees = [item.ntree for item in forests]
    total = sum(trees)
    merged = RandomForest(**first.__dict__)
    merged.ntree = total
    if first.forest is not None and all(item.forest is not None for item in forests):
        nrnodes = max(item.forest["nrnodes"] for item in forests)
        def pad_columns(key):
            columns = []
            for item in forests:
                block = item.forest[key]
                for node in range(nrnodes):
                    if len(columns) <= node:
                        columns.append([])
                    if node < len(block):
                        columns[node].extend(block[node])
                    else:
                        columns[node].extend([0] * item.ntree)
            return columns
        forest = dict(first.forest)
        forest["nrnodes"] = nrnodes
        forest["ntree"] = total
        forest["ndbigtree"] = [size for item in forests for size in item.forest["ndbigtree"]]
        for key in ("nodestatus", "bestvar", "xbestsplit", "nodepred"):
            forest[key] = pad_columns(key)
        if first.type == "classification":
            treemap = []
            for node in range(nrnodes):
                row = []
                for item in forests:
                    if node < len(item.forest["treemap"]):
                        row.extend(item.forest["treemap"][node])
                    else:
                        row.extend([[0, 0]] * item.ntree)
                treemap.append(row)
            forest["treemap"] = treemap
        else:
            forest["left_daughter"] = pad_columns("left_daughter")
            forest["right_daughter"] = pad_columns("right_daughter")
        merged.forest = forest
    if first.type == "classification":
        votes = np.zeros_like(np.array(first.votes, dtype=float))
        oob = np.zeros(len(first.oob_times))
        raw = any(np.nanmax(np.array(item.votes, dtype=float)) > 1 for item in forests)
        for item in forests:
            block = np.array(item.votes, dtype=float)
            block = np.where(np.isnan(block), 0.0, block)
            times = np.array(item.oob_times, dtype=float)
            oob += times
            votes += block if raw else block * times[:, None]
        if not raw:
            votes = votes / oob[:, None]
        merged.votes = votes.tolist()
        merged.oob_times = oob.tolist()
        merged.predicted = [first.classes[index] for index in _max_col(votes)]
    else:
        predicted = np.zeros(len(first.predicted))
        for item in forests:
            predicted += np.array(item.predicted, dtype=float) * item.ntree
        merged.predicted = (predicted / total).tolist()
    if all(item.importance is not None for item in forests):
        importance_sum = np.zeros_like(np.array(first.importance, dtype=float))
        for item in forests:
            importance_sum += np.array(item.importance, dtype=float) * item.ntree
        merged.importance = (importance_sum / total).tolist()
        if first.importance_sd is not None:
            sd = np.zeros_like(np.array(first.importance_sd, dtype=float))
            for item in forests:
                block = np.array(item.importance_sd, dtype=float)
                sd += block * block * item.ntree
            merged.importance_sd = np.sqrt(sd / total).tolist()
    if first.type == "classification":
        merged.confusion = None
        merged.err_rate = None
    else:
        merged.mse = None
        merged.rsq = None
    return merged


def grow(forest, how_many, **kwargs):
    """Grow ``how_many`` more trees and append them."""
    extra = random_forest(
        forest._x,
        forest.y,
        ntree=how_many,
        mtry=forest.mtry,
        nodesize=forest._nodesize,
        importance=forest.importance_sd is not None,
        keep_forest=forest.forest is not None,
        **kwargs,
    )
    return combine(forest, extra)


def _max_col(matrix):
    """R max.col with ties.method 'random'. Returns 0-based column indices."""
    from boot.rng import unif

    chosen = []
    for row in np.asarray(matrix, dtype=float):
        which = 0
        ntie = 1
        best = float(row[0])
        for index in range(1, len(row)):
            value = float(row[index])
            if value > best:
                which = index
                ntie = 1
                best = value
            elif value == best:
                ntie += 1
                if ntie * unif() < 1.0:
                    which = index
        chosen.append(which)
    return chosen


def class_center(x, label, prox, n_nbr=None):
    """Median of the neighbors that most often fall with each class."""
    data = np.asarray(x, dtype=float)
    labels = [str(item) for item in label]
    levels = []
    for item in labels:
        if item not in levels:
            levels.append(item)
    counts = [labels.count(item) for item in levels]
    if n_nbr is None:
        n_nbr = min(counts) - 1
    proximity = np.asarray(prox, dtype=float)
    order = np.argsort(-proximity, axis=1, kind="mergesort")
    chosen = order[:, :n_nbr]
    neighbor_labels = np.array(labels)[chosen]
    ncls = np.column_stack([
        np.sum(neighbor_labels == level, axis=1) for level in levels
    ])
    modes = _max_col(ncls.T)
    centers = []
    for level, mode in zip(levels, modes):
        neighbors = chosen[mode]
        keep = [index for index in neighbors if labels[index] == level]
        block = data[keep]
        centers.append(np.median(block, axis=0).tolist())
    return centers


def partial_plot(forest, pred_data, x_var, which_class=None, weights=None, n_pt=None):
    """Partial dependence of the forest prediction on one predictor."""
    data = np.asarray(pred_data, dtype=float)
    if isinstance(x_var, str):
        column = forest.x_names.index(x_var)
    else:
        column = int(x_var) - 1
    xv = data[:, column]
    n = data.shape[0]
    if weights is None:
        weights = np.ones(n)
    else:
        weights = np.asarray(weights, dtype=float)
    unique = np.unique(xv)
    if n_pt is None:
        n_pt = min(len(unique), 51)
    grid = np.linspace(float(xv.min()), float(xv.max()), n_pt)
    focus = 0 if which_class is None else forest.classes.index(str(which_class))
    ys = []
    eps = np.finfo(float).eps
    for point in grid:
        trial = data.copy()
        trial[:, column] = point
        if forest.type == "classification":
            probs = np.array(predict(forest, trial, type="prob"), dtype=float)
            logged = np.log(np.where(probs > 0, probs, eps))
            score = logged[:, focus] - logged.mean(axis=1)
            ys.append(float(np.average(score, weights=weights)))
        else:
            ys.append(float(np.average(predict(forest, trial), weights=weights)))
    return {"x": grid.tolist(), "y": ys}


def tune_rf(x, y, mtry_start=None, ntree_try=50, step_factor=2, improve=0.05, do_best=False, **kwargs):
    """Search mtry outward while the out-of-bag error keeps falling."""
    matrix = np.asarray(x, dtype=float)
    labels = list(y)
    class_fit = isinstance(labels[0], str)
    p = matrix.shape[1]
    if mtry_start is None:
        mtry_start = math.floor(math.sqrt(p)) if class_fit else math.floor(p / 3)
    def error_at(mtry):
        fit = random_forest(matrix, labels, mtry=mtry, ntree=ntree_try, keep_forest=False, **kwargs)
        if class_fit:
            return fit.err_rate[ntree_try - 1][0]
        return fit.mse[ntree_try - 1]
    current = error_at(mtry_start)
    found = {mtry_start: current}
    for direction in ("left", "right"):
        better = 1.1 * improve
        cursor = mtry_start
        reference = current
        while better >= improve:
            previous = cursor
            if direction == "left":
                cursor = max(1, math.ceil(cursor / step_factor))
            else:
                cursor = min(p, math.floor(cursor * step_factor))
            if cursor == previous:
                break
            trial = error_at(cursor)
            found[cursor] = trial
            better = 1 - trial / reference
            if better > improve:
                reference = trial
    keys = sorted(found)
    return [[key, found[key]] for key in keys]


def rfcv(train_x, train_y, cv_fold=5, scale="log", step=0.5, mtry=None, recursive=False, **kwargs):
    """Cross-validated error as predictors are dropped by importance."""
    from boot.rng import sample_int

    matrix = np.asarray(train_x, dtype=float)
    labels = list(train_y)
    class_fit = isinstance(labels[0], str)
    n, p = matrix.shape
    if scale == "log":
        k = math.floor(math.log(p) / math.log(1 / step))
        n_var = [int(round(p * step ** i)) for i in range(k)]
        deduped = []
        for value in n_var:
            if not deduped or value != deduped[-1]:
                deduped.append(value)
        n_var = deduped
        if 1 not in n_var:
            n_var.append(1)
    else:
        n_var = list(range(p, 0, -int(step) if step >= 1 else -1))
    if class_fit:
        groups = [str(item) for item in labels]
    else:
        ranks = np.argsort(np.argsort(np.asarray(labels, dtype=float), kind="mergesort"), kind="mergesort")
        groups = [str((int(index) % 5) + 1) for index in ranks]
    levels = sorted(set(groups))
    fold = [0] * n
    for level in levels:
        members = [index for index, item in enumerate(groups) if item == level]
        draw = sample_int(len(members))
        pool = [((i % cv_fold) + 1) for i in range(len(members))]
        for member, slot in zip(members, draw):
            fold[member] = pool[slot - 1]
    if mtry is None:
        def mtry(width):
            return max(1, math.floor(math.sqrt(width)))
    predicted = [labels[:] for _ in n_var]
    for fold_id in range(1, cv_fold + 1):
        train = [index for index, item in enumerate(fold) if item != fold_id]
        test = [index for index, item in enumerate(fold) if item == fold_id]
        y_train = [labels[index] for index in train]
        y_test = [labels[index] for index in test]
        fit = random_forest(
            matrix[train], y_train, xtest=matrix[test], ytest=y_test,
            mtry=mtry(p), importance=True, **kwargs,
        )
        # Test predictions are not stored unless xtest is honoured; predict instead.
        held = predict(fit, matrix[test])
        for offset, index in enumerate(test):
            predicted[0][index] = held[offset]
        scores = np.array(importance(fit, type=1), dtype=float).ravel()
        order = list(np.argsort(-scores, kind="mergesort"))
        for j in range(1, len(n_var)):
            keep = order[:n_var[j]]
            sub = random_forest(
                matrix[np.ix_(train, keep)], y_train,
                mtry=mtry(n_var[j]), importance=recursive, **kwargs,
            )
            held = predict(sub, matrix[np.ix_(test, keep)])
            for offset, index in enumerate(test):
                predicted[j][index] = held[offset]
            if recursive:
                scores = np.array(importance(sub, type=1), dtype=float).ravel()
                order = list(np.argsort(-scores, kind="mergesort"))
    if class_fit:
        error = [float(np.mean([a != b for a, b in zip(labels, column)])) for column in predicted]
    else:
        error = [float(np.mean((np.array(labels, dtype=float) - np.array(column, dtype=float)) ** 2)) for column in predicted]
    return {"n_var": n_var, "error_cv": error, "predicted": predicted}


def rf_impute(x, y, iter=5, ntree=300, **kwargs):
    """Fill missing predictors from proximity-weighted neighbors."""
    from randomForest.votes import na_roughfix

    data = np.array(x, dtype=float)
    labels = list(y)
    filled = np.array(na_roughfix(data), dtype=float)
    missing_columns = [j for j in range(data.shape[1]) if np.isnan(data[:, j]).any()]
    for _ in range(iter):
        fit = random_forest(filled, labels, ntree=ntree, proximity=True, **kwargs)
        prox = np.array(fit.proximity, dtype=float)
        for j in missing_columns:
            miss = np.isnan(data[:, j])
            observed = ~miss
            sumprox = prox[np.ix_(observed, miss)].sum(axis=0)
            numer = prox[np.ix_(miss, observed)] @ filled[observed, j]
            filled[miss, j] = numer / (1e-8 + sumprox)
    if labels and isinstance(labels[0], str):
        return filled
    return np.column_stack([np.asarray(labels, dtype=float), filled])


def mdsplot(forest, k=2):
    """Classical scaling of one minus the proximity matrix."""
    proximity = np.asarray(forest.proximity, dtype=float)
    distance = 1.0 - proximity
    squared = distance ** 2
    row_mean = squared.mean(axis=1, keepdims=True)
    col_mean = squared.mean(axis=0, keepdims=True)
    centred = squared - row_mean - col_mean + squared.mean()
    gram = np.asfortranarray(-centred / 2.0)
    # Same symmetric eigensolver R's eigen() calls, so the axis signs agree.
    from scipy.linalg import lapack

    values, vectors, _m, _isuppz, info = lapack.dsyevr(gram, compute_v=1, range=b"A")
    if info != 0:
        raise RuntimeError("eigen decomposition failed")
    order = np.argsort(values)[::-1]
    values = np.asarray(values, dtype=float)[order]
    vectors = np.asarray(vectors, dtype=float)[:, order]
    keep = values[:k]
    positive = keep > 0
    used = keep[positive]
    vectors = vectors[:, :k][:, positive]
    points = vectors * np.sqrt(used)
    return {"points": points.tolist(), "eig": values.tolist()}


def var_imp_plot(forest, sort=True, n_var=None, type=None, class_label=None, scale=True):
    """The importance matrix a dot chart is drawn from. R returns that matrix."""
    del sort, n_var
    table = importance(forest, type=type, class_label=class_label, scale=scale)
    if table.shape[1] > 2:
        table = table[:, -2:]
    return table.tolist()


def rf_news():
    """Text of the installed randomForest NEWS file."""
    path = Path.home() / "R" / "library" / "randomForest" / "NEWS"
    return path.read_text()
