"""Nearest-neighbor search for FNN 1.1.4.1.

Euclidean search uses ANN's k-element queue. A later point replaces an
earlier one only when its squared distance is strictly smaller, so an equal
distance keeps the point already stored. The default kd-tree visits the
closer child first, and that visit order is the index order. ``get.knn``
asks for ``k + 1`` neighbors and drops the first, which is the point itself
when self-match is allowed.

``CR`` is the correlation distance ``1 - x'y`` from the class package, with
that package's tie window. Self-matches are skipped.
"""

import math

import numpy as np

_EUCLIDEAN = ("kd_tree", "cover_tree", "brute")
_CHOICES = ("kd_tree", "cover_tree", "CR", "brute")
_MAX_TIES = 1000
_SENTINEL = 0.99 * np.finfo(float).max


def match_arg(value, choices):
    if value is None:
        return choices[0]
    text = str(value)
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) != 1:
        raise ValueError(f"algorithm {value!r} does not match one of {choices}")
    return hits[0]


def _as_matrix(data, name):
    array = np.asarray(data, dtype=float)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a matrix")
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError("Data non-numeric")
    if np.isnan(array).any():
        raise ValueError("Data include NAs")
    return np.ascontiguousarray(array, dtype=float)


class _MinK:
    """ANN's insertion-sorted queue of k squared distances."""

    def __init__(self, k):
        self.k = int(k)
        self.n = 0
        self.key = np.full(self.k + 1, np.inf)
        self.info = np.full(self.k + 1, -1, dtype=int)

    def insert(self, key, info):
        i = self.n
        while i > 0 and self.key[i - 1] > key:
            self.key[i] = self.key[i - 1]
            self.info[i] = self.info[i - 1]
            i -= 1
        self.key[i] = key
        self.info[i] = info
        if self.n < self.k:
            self.n += 1


def _sq_dist(point, query):
    diff = point - query
    return float(np.dot(diff, diff))


_FNN_ERR = 0.001


def _enclose(data, pidx):
    lo = data[pidx[0]].copy()
    hi = lo.copy()
    for i in pidx[1:]:
        point = data[i]
        lo = np.minimum(lo, point)
        hi = np.maximum(hi, point)
    return lo, hi


def _spread(data, pidx, dim):
    coords = data[pidx, dim]
    return float(coords.max() - coords.min())


def _plane_split(data, pidx, dim, cut):
    """Partition like ANN ``annPlaneSplit``. Returns br1, br2."""
    n = len(pidx)
    l = 0
    r = n - 1
    while True:
        while l < n and data[pidx[l], dim] < cut:
            l += 1
        while r >= 0 and data[pidx[r], dim] >= cut:
            r -= 1
        if l > r:
            break
        pidx[l], pidx[r] = pidx[r], pidx[l]
        l += 1
        r -= 1
    br1 = l
    r = n - 1
    while True:
        while l < n and data[pidx[l], dim] <= cut:
            l += 1
        while r >= br1 and data[pidx[r], dim] > cut:
            r -= 1
        if l > r:
            break
        pidx[l], pidx[r] = pidx[r], pidx[l]
        l += 1
        r -= 1
    return br1, l


def _sl_midpoint(data, pidx, lo, hi):
    dim = data.shape[1]
    lengths = hi - lo
    longest = float(lengths.max())
    cut_dim = 0
    max_spread = -1.0
    for d in range(dim):
        if lengths[d] >= (1 - _FNN_ERR) * longest:
            spr = _spread(data, pidx, d)
            if spr > max_spread:
                max_spread = spr
                cut_dim = d
    ideal = (float(lo[cut_dim]) + float(hi[cut_dim])) / 2
    coords = data[pidx, cut_dim]
    low = float(coords.min())
    high = float(coords.max())
    if ideal < low:
        cut = low
    elif ideal > high:
        cut = high
    else:
        cut = ideal
    br1, br2 = _plane_split(data, pidx, cut_dim, cut)
    n = len(pidx)
    half = n // 2
    if ideal < low:
        n_lo = 1
    elif ideal > high:
        n_lo = n - 1
    elif br1 > half:
        n_lo = br1
    elif br2 < half:
        n_lo = br2
    else:
        n_lo = half
    return cut_dim, cut, n_lo, float(lo[cut_dim]), float(hi[cut_dim])


def _build(data, pidx, lo, hi):
    if len(pidx) <= 1:
        return ("leaf", list(pidx))
    cut_dim, cut, n_lo, bound_lo, bound_hi = _sl_midpoint(data, pidx, lo, hi)
    saved_hi = hi[cut_dim]
    hi[cut_dim] = cut
    left = _build(data, pidx[:n_lo], lo, hi)
    hi[cut_dim] = saved_hi
    saved_lo = lo[cut_dim]
    lo[cut_dim] = cut
    right = _build(data, pidx[n_lo:], lo, hi)
    lo[cut_dim] = saved_lo
    return ("split", cut_dim, cut, bound_lo, bound_hi, left, right)


def _search(node, data, query, queue, box_dist):
    kind = node[0]
    if kind == "leaf":
        limit = queue.key[queue.k - 1] if queue.n == queue.k else math.inf
        for index in node[1]:
            dist = _sq_dist(data[index], query)
            if dist <= limit:
                queue.insert(dist, index)
                limit = queue.key[queue.k - 1] if queue.n == queue.k else math.inf
        return
    _kind, cut_dim, cut, bound_lo, bound_hi, left, right = node
    cut_diff = float(query[cut_dim]) - cut
    if cut_diff < 0:
        _search(left, data, query, queue, box_dist)
        box_diff = bound_lo - float(query[cut_dim])
        if box_diff < 0:
            box_diff = 0.0
        box_dist = box_dist + cut_diff * cut_diff - box_diff * box_diff
        limit = queue.key[queue.k - 1] if queue.n == queue.k else math.inf
        if box_dist < limit:
            _search(right, data, query, queue, box_dist)
    else:
        _search(right, data, query, queue, box_dist)
        box_diff = float(query[cut_dim]) - bound_hi
        if box_diff < 0:
            box_diff = 0.0
        box_dist = box_dist + cut_diff * cut_diff - box_diff * box_diff
        limit = queue.key[queue.k - 1] if queue.n == queue.k else math.inf
        if box_dist < limit:
            _search(left, data, query, queue, box_dist)


def _box_distance(query, lo, hi):
    dist = 0.0
    for d in range(query.shape[0]):
        if query[d] < lo[d]:
            t = float(lo[d] - query[d])
            dist += t * t
        elif query[d] > hi[d]:
            t = float(query[d] - hi[d])
            dist += t * t
    return dist


def _kd_euclidean(data, query, k, drop_first):
    n, dim = data.shape
    if query.shape[1] != dim:
        raise ValueError("Number of columns must be same!.")
    take = k + 1 if drop_first else k
    if take > n:
        raise ValueError("k should be less than sample size")
    pidx = list(range(n))
    lo, hi = _enclose(data, pidx)
    # Construction mutates a working copy. The search uses the original box.
    root = _build(data, pidx, lo.copy(), hi.copy())
    index = np.empty((query.shape[0], k), dtype=int)
    dist = np.empty((query.shape[0], k), dtype=float)
    for row in range(query.shape[0]):
        queue = _MinK(take)
        _search(root, data, query[row], queue, _box_distance(query[row], lo, hi))
        start = 1 if drop_first else 0
        for j in range(k):
            index[row, j] = int(queue.info[start + j]) + 1
            dist[row, j] = math.sqrt(float(queue.key[start + j]))
    return index, dist


def _euclidean(data, query, k, drop_first):
    """Return 1-based indices and Euclidean distances, shape (m, k)."""
    n, dim = data.shape
    m = query.shape[0]
    if query.shape[1] != dim:
        raise ValueError("Number of columns must be same!.")
    take = k + 1 if drop_first else k
    if take > n:
        raise ValueError("k should be less than sample size")
    index = np.empty((m, k), dtype=int)
    dist = np.empty((m, k), dtype=float)
    for row in range(m):
        queue = _MinK(take)
        q = query[row]
        for i in range(n):
            queue.insert(_sq_dist(data[i], q), i)
        start = 1 if drop_first else 0
        for j in range(k):
            index[row, j] = int(queue.info[start + j]) + 1
            dist[row, j] = math.sqrt(float(queue.key[start + j]))
    return index, dist


def _float_length(left, right):
    total = np.float32(0)
    for col in range(left.shape[0]):
        delta = np.float32(left[col]) - np.float32(right[col])
        total = np.float32(total + delta * delta)
    return float(np.sqrt(total))


def _cover(data, query, k, drop_first):
    """Cover-tree distances are single-precision Euclidean lengths.

    Self is omitted for ``get.knn``. Equal lengths keep the earlier point.
    """
    n, dim = data.shape
    m = query.shape[0]
    if query.shape[1] != dim:
        raise ValueError("Number of columns must be same!.")
    if k > n - (1 if drop_first else 0):
        raise ValueError("k should be less than sample size")
    index = np.empty((m, k), dtype=int)
    dist = np.empty((m, k), dtype=float)
    for row in range(m):
        pairs = []
        for i in range(n):
            if drop_first and i == row:
                continue
            pairs.append((_float_length(query[row], data[i]), i))
        pairs.sort(key=lambda item: item[0])
        for j in range(k):
            dist[row, j] = pairs[j][0]
            index[row, j] = pairs[j][1] + 1
    return index, dist


def _correlation(data, query, k, skip_self):
    """class::VR distance ``1 - inner product``, 1-based indices."""
    n, dim = data.shape
    m = query.shape[0]
    if query.shape[1] != dim:
        raise ValueError("Number of columns must be same!.")
    if k > n - (1 if skip_self else 0):
        raise ValueError("too many ties in knn")
    index = np.empty((m, k), dtype=int)
    dist = np.empty((m, k), dtype=float)
    room = _MAX_TIES + k
    for row in range(m):
        kn = k
        nndist = np.full(room, _SENTINEL)
        pos = np.full(room, -1, dtype=int)
        q = query[row]
        for j in range(n):
            if skip_self and j == row:
                continue
            inner = 0.0
            for col in range(dim):
                inner += float(q[col]) * float(data[j, col])
            value = 1.0 - inner
            if value <= nndist[k - 1]:
                for slot in range(kn + 1):
                    if value < nndist[slot]:
                        for move in range(kn, slot, -1):
                            nndist[move] = nndist[move - 1]
                            pos[move] = pos[move - 1]
                        nndist[slot] = value
                        pos[slot] = j
                        if nndist[kn] <= nndist[k - 1]:
                            kn += 1
                            if kn == _MAX_TIES - 1:
                                raise ValueError("too many ties in knn")
                        break
            nndist[kn] = _SENTINEL
        index[row] = pos[:k] + 1
        dist[row] = nndist[:k]
    return index, dist


def get_knn(data, k=10, algorithm=None):
    algorithm = match_arg(algorithm, _CHOICES)
    data = _as_matrix(data, "data")
    n = data.shape[0]
    if k >= n:
        raise ValueError("k should be less than sample size")
    if algorithm == "CR":
        index, dist = _correlation(data, data, int(k), skip_self=True)
    elif algorithm == "kd_tree":
        index, dist = _kd_euclidean(data, data, int(k), drop_first=True)
    elif algorithm == "brute":
        index, dist = _euclidean(data, data, int(k), drop_first=True)
    else:
        index, dist = _cover(data, data, int(k), drop_first=True)
    return {"nn.index": index, "nn.dist": dist}


def get_knnx(data, query, k=10, algorithm=None):
    algorithm = match_arg(algorithm, _CHOICES)
    data = _as_matrix(data, "data")
    query = _as_matrix(query, "query")
    n = data.shape[0]
    if k > n:
        raise ValueError("k should be less than sample size")
    if algorithm == "CR":
        index, dist = _correlation(data, query, int(k), skip_self=False)
    elif algorithm == "kd_tree":
        index, dist = _kd_euclidean(data, query, int(k), drop_first=False)
    elif algorithm == "brute":
        index, dist = _euclidean(data, query, int(k), drop_first=False)
    else:
        index, dist = _cover(data, query, int(k), drop_first=False)
    return {"nn.index": index, "nn.dist": dist}


def knn_index(data, k=10, algorithm=None):
    return get_knn(data, k, algorithm)["nn.index"]


def knn_dist(data, k=10, algorithm=None):
    return get_knn(data, k, algorithm)["nn.dist"]


def knnx_index(data, query, k=10, algorithm=None):
    return get_knnx(data, query, k, algorithm)["nn.index"]


def knnx_dist(data, query, k=10, algorithm=None):
    return get_knnx(data, query, k, algorithm)["nn.dist"]
