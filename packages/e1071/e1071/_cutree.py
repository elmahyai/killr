"""R ``stats`` ``cutree`` for an ``hclust`` merge matrix (``hclust-utils.c``)."""


def cutree(merge: list[list[int]], k_values: list[int]) -> list[list[int]]:
    """Return cluster ids for each k in ``k_values`` (1-based labels)."""
    n = len(merge) + 1
    k_list = [int(k) for k in k_values]
    if any(k < 1 or k > n for k in k_list):
        raise ValueError(f"elements of 'k' must be between 1 and {n}")
    columns = len(k_list)
    ans = [[0] * n for _ in range(columns)]
    sing = [False] * (n + 1)
    m_nr = [0] * (n + 1)
    z = [0] * (n + 1)

    for k in range(1, n + 1):
        sing[k] = True
        m_nr[k] = 0

    for step in range(1, n):
        m1 = merge[step - 1][0]
        m2 = merge[step - 1][1]
        if m1 < 0 and m2 < 0:
            m_nr[-m1] = step
            m_nr[-m2] = step
            sing[-m1] = False
            sing[-m2] = False
        elif m1 < 0 or m2 < 0:
            if m1 < 0:
                j = -m1
                m1 = m2
            else:
                j = -m2
            for l in range(1, n + 1):
                if m_nr[l] == m1:
                    m_nr[l] = step
            m_nr[j] = step
            sing[j] = False
        else:
            for l in range(1, n + 1):
                if m_nr[l] == m1 or m_nr[l] == m2:
                    m_nr[l] = step

        target = n - step
        matched_cols: list[int] = []
        for j, want in enumerate(k_list):
            if want == target:
                matched_cols.append(j)
        if not matched_cols:
            continue
        for l in range(1, n + 1):
            z[l] = 0
        nclust = 0
        for l in range(1, n + 1):
            if sing[l]:
                nclust += 1
                label = nclust
            else:
                if z[m_nr[l]] == 0:
                    nclust += 1
                    z[m_nr[l]] = nclust
                label = z[m_nr[l]]
            for col in matched_cols:
                ans[col][l - 1] = label

    for j, want in enumerate(k_list):
        if want == n:
            for l in range(n):
                ans[j][l] = l + 1

    return ans
