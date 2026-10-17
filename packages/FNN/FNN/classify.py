"""kNN classification, regression, and optimal weighted neighbors."""

import math

import numpy as np

from .search import get_knn, get_knnx, match_arg


def _labels(cl):
    text = [str(item) for item in np.asarray(cl, dtype=object).reshape(-1)]
    levels = sorted(set(text))
    return text, levels


def _vote(row, levels, k):
    counts = [row.count(level) for level in levels]
    winner = int(np.argmax(counts))
    return levels[winner], counts[winner] / k


def _predict(index, cl, k):
    labels, levels = _labels(cl)
    chosen = []
    probs = []
    for row in np.asarray(index, dtype=int):
        names = [labels[i - 1] for i in row]
        label, prob = _vote(names, levels, k)
        chosen.append(label)
        probs.append(prob)
    return np.array(chosen, dtype=object), np.array(probs, dtype=float)


def knn(train, test, cl, k=1, prob=False, algorithm=None):
    algorithm = match_arg(algorithm, ("kd_tree", "cover_tree", "brute"))
    found = get_knnx(train, test, k, algorithm)
    labels, probs = _predict(found["nn.index"], cl, k)
    result = labels
    if prob:
        result = (labels, probs)
    return {"class": labels, "prob": probs if prob else None, "nn.index": found["nn.index"], "nn.dist": found["nn.dist"]}


def knn_cv(train, cl, k=1, prob=False, algorithm=None):
    algorithm = match_arg(algorithm, ("kd_tree", "cover_tree", "brute"))
    found = get_knn(train, k, algorithm)
    labels, probs = _predict(found["nn.index"], cl, k)
    return {"class": labels, "prob": probs if prob else None, "nn.index": found["nn.index"], "nn.dist": found["nn.dist"]}


def knn_reg(train, test=None, y=None, k=3, algorithm=None):
    algorithm = match_arg(algorithm, ("kd_tree", "cover_tree", "brute"))
    response = np.asarray(y, dtype=float).reshape(-1)
    if test is None:
        found = get_knn(train, k, algorithm)
    else:
        found = get_knnx(train, test, k, algorithm)
    pred = response[found["nn.index"] - 1].mean(axis=1)
    if test is None:
        residuals = response - pred
        press = float(np.sum(residuals ** 2))
        center = response - np.mean(response)
        r2 = 1.0 - press / float(np.sum(center ** 2))
    else:
        residuals = None
        press = None
        r2 = None
    return {"k": k, "n": int(pred.size), "pred": pred, "residuals": residuals, "PRESS": press, "R2Pred": r2}


def ownn(train, test, cl, testcl=None, k=None, prob=False, algorithm=None):
    algorithm = match_arg(algorithm, ("kd_tree", "cover_tree", "brute"))
    train_m = np.asarray(train, dtype=float)
    test_m = np.asarray(test, dtype=float)
    if train_m.ndim == 1:
        train_m = train_m.reshape(1, -1)
    if test_m.ndim == 1:
        test_m = test_m.reshape(1, -1)
    n, d = train_m.shape
    if k is None:
        raise ValueError("k is required; the R default draws a random fold")
    labels, _levels = _labels(cl)
    order = get_knnx(train_m, test_m, n, algorithm)["nn.index"]
    nn_class = np.array(labels, dtype=object)[order - 1]

    def one(row, method):
        if method == "knn":
            weight = np.zeros(n)
            weight[:k] = 1.0 / k
        elif method == "ownn":
            kstar = math.floor(((2 * (d + 4) / (d + 2)) ** (d / (d + 4))) * k)
            kstar = max(int(kstar), 1)
            i = np.arange(1, kstar + 1, dtype=float)
            alpha = i ** (1 + 2 / d) - (i - 1) ** (1 + 2 / d)
            head = (1 + d / 2 - d / (2 * kstar ** (2 / d)) * alpha) / kstar
            weight = np.zeros(n)
            weight[:kstar] = head
        else:
            q = (2 ** (d / (d + 4))) * (math.gamma(2 + 2 / d) ** (2 * d / (d + 4))) * (1 / k)
            index = np.arange(n, dtype=float)
            weight = q * (1 - q) ** index / (1 - (1 - q) ** n)
        levels = sorted(set(labels))
        totals = []
        for level in levels:
            totals.append(float(np.sum(weight[row == level])))
        totals = np.array(totals)
        winner = int(np.argmax(totals))
        share = totals / np.sum(totals)
        return levels[winner], float(share[winner])

    out = {}
    for method in ("knn", "ownn", "bnn"):
        picked = [one(row, method) for row in nn_class]
        out[method] = np.array([item[0] for item in picked], dtype=object)
        out[method + "_prob"] = np.array([item[1] for item in picked], dtype=float)
    result = {"k": k, "knn": out["knn"], "ownn": out["ownn"], "bnn": out["bnn"]}
    if prob:
        result["prob"] = out["knn_prob"]
    if testcl is not None:
        truth = np.array([str(item) for item in np.asarray(testcl, dtype=object).reshape(-1)])
        result["accuracy"] = {
            "knn": float(np.mean(truth == out["knn"])),
            "ownn": float(np.mean(truth == out["ownn"])),
            "bnn": float(np.mean(truth == out["bnn"])),
        }
    return result
