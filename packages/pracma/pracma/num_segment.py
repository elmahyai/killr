"""Segment intersection and distance."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_cross import cross
from pracma.num_helpers import is_r_numeric, r_length


def _segment(values, name):
    if not is_r_numeric(values):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or array.shape[0] != 2:
        raise PracmaError(f"nrow({name}) == 2 is not TRUE")
    if array.shape[1] != 2:
        raise PracmaError(f"ncol({name}) == 2 is not TRUE")
    return array


def segm_intersect(s1, s2):
    first = _segment(s1, "s1")
    second = _segment(s2, "s2")

    def bounds(segment):
        return np.array([
            [np.min(segment[:, 0]), np.min(segment[:, 1])],
            [np.max(segment[:, 0]), np.max(segment[:, 1])],
        ])

    bb1 = bounds(first)
    bb2 = bounds(second)
    upper = np.vstack([bb1[1], bb2[1]])
    lower = np.vstack([bb2[0], bb1[0]])
    if not np.all(upper >= lower):
        return False
    p1, p2 = first[0], first[1]
    p3, p4 = second[0], second[1]
    sgn1 = np.sign(cross(np.concatenate([p3 - p1, [0]]), np.concatenate([p2 - p1, [0]]))[2]) * np.sign(
        cross(np.concatenate([p4 - p1, [0]]), np.concatenate([p2 - p1, [0]]))[2]
    )
    sgn2 = np.sign(cross(np.concatenate([p1 - p3, [0]]), np.concatenate([p4 - p3, [0]]))[2]) * np.sign(
        cross(np.concatenate([p2 - p3, [0]]), np.concatenate([p4 - p3, [0]]))[2]
    )
    return bool(sgn1 <= 0 and sgn2 <= 0)


def _pair(values, name):
    if not is_r_numeric(values):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    array = np.asarray(values, dtype=float).reshape(-1)
    if array.size != 2:
        raise PracmaError(f"length({name}) == 2 is not TRUE")
    return array


def _euclid(p1, p2):
    return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))


def segm_distance(p1, p2, p3, p4=None):
    a = _pair(p1, "p1")
    b = _pair(p2, "p2")
    c = _pair(p3, "p3")
    if p4 is None or (not isinstance(p4, np.ndarray) and r_length(p4) == 0 and not is_r_numeric(p4)):
        if _euclid(a, b) == 0:
            return {"d": _euclid(a, c), "p": a}
        direction = b - a
        design = np.array([[-direction[1], -direction[0]], [direction[0], -direction[1]]], dtype=float)
        coefficient = np.linalg.solve(design, (a - c).reshape(2, 1))[1, 0]
        if 0 <= coefficient <= 1:
            point = a + coefficient * direction
        elif coefficient < 0:
            point = a
        else:
            point = b
        return {"d": _euclid(point, c), "p": point, "q": c}
    if is_r_numeric(p4) and np.asarray(p4).size == 2:
        d = _pair(p4, "p4")
        if segm_intersect(np.vstack([a, b]), np.vstack([c, d])) and cross(
            np.concatenate([b - a, [0]]), np.concatenate([d - c, [0]])
        )[2] != 0:
            design = np.column_stack([b - a, d - c])
            coefficient = np.linalg.solve(design, c - a)
            return {
                "d": 0.0,
                "p": a + coefficient[0] * (b - a),
                "q": c - coefficient[1] * (d - c),
            }
        points = [c, d, a, b]
        pieces = [
            segm_distance(a, b, c),
            segm_distance(a, b, d),
            segm_distance(c, d, a),
            segm_distance(c, d, b),
        ]
        index = int(np.argmin([piece["d"] for piece in pieces]))
        return {"d": pieces[index]["d"], "p": pieces[index]["p"], "q": points[index]}
    raise PracmaError("Argument 'p4' must be NULL or a vector of length 2.")
