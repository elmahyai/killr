"""Anova recursive partition, following rpart's C tree.

Continuous predictors, primary splits, competitors, surrogates, the
complexity table, and cross-validation. Categorical predictors and the
classification and Poisson rules are not in this tree.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_PACKAGES = Path(__file__).resolve().parents[2]
if str(_PACKAGES / "boot") not in sys.path:
    sys.path.insert(0, str(_PACKAGES / "boot"))
from boot.rng import sample_int  # noqa: E402

LEFT = -1
RIGHT = 1


class Split:
    def __init__(self):
        self.improve = 0.0
        self.adj = 0.0
        self.spoint = 0.0
        self.nextsplit = None
        self.var_num = 0
        self.count = 0
        self.csplit = [0]


class Node:
    def __init__(self):
        self.risk = 0.0
        self.complexity = 0.0
        self.sum_wt = 0.0
        self.primary = None
        self.surrogate = None
        self.rightson = None
        self.leftson = None
        self.num_obs = 0
        self.lastsurrogate = 0
        self.response_est = [0.0]


class CpRow:
    def __init__(self):
        self.cp = 0.0
        self.risk = 0.0
        self.xrisk = 0.0
        self.xstd = 0.0
        self.nsplit = 0
        self.forward = None
        self.back = None


class _Rp:
    def __init__(self):
        self.min_node = 7
        self.min_split = 20
        self.complexity = 0.01
        self.maxpri = 5
        self.maxsur = 5
        self.usesurrogate = 2
        self.sur_agree = 0
        self.maxnode = 2 ** 30 - 1
        self.n = 0
        self.nvar = 0
        self.numcat = []
        self.wt = []
        self.iscale = 0.0
        self.vcost = []
        self.xdata = []
        self.ydata = []
        self.tempvec = []
        self.xtemp = []
        self.ytemp = []
        self.wtemp = []
        self.sorts = []
        self.which = []
        self.csplit = [0]
        self.alpha = 0.0
        self.num_unique_cp = 1
        self.cptable_tail = None


def _mysort(start, stop, x, cvec):
    while start < stop:
        if (stop - start) < 11:
            for i in range(start + 1, stop + 1):
                temp = x[i]
                tempd = cvec[i]
                j = i - 1
                while j >= start and x[j] > temp:
                    x[j + 1] = x[j]
                    cvec[j + 1] = cvec[j]
                    j -= 1
                x[j + 1] = temp
                cvec[j + 1] = tempd
            return
        i = start
        j = stop
        k = (start + stop) // 2
        median = x[k]
        if x[i] >= x[k]:
            if x[j] > x[k]:
                median = x[j] if x[i] > x[j] else x[i]
        else:
            if x[j] < x[k]:
                median = x[i] if x[i] > x[j] else x[j]
        while i < j:
            while x[i] < median:
                i += 1
            while x[j] > median:
                j -= 1
            if i < j:
                if x[i] > x[j]:
                    x[i], x[j] = x[j], x[i]
                    cvec[i], cvec[j] = cvec[j], cvec[i]
                i += 1
                j -= 1
        while x[i] >= median and i > start:
            i -= 1
        while x[j] <= median and j < stop:
            j += 1
        if (i - start) < (stop - j):
            if (i - start) > 0:
                _mysort(start, i, x, cvec)
            start = j
        else:
            if (stop - j) > 0:
                _mysort(j, stop, x, cvec)
            stop = i


def _anovass(n, y, value_box, risk_box, wt):
    temp = 0.0
    twt = 0.0
    for i in range(n):
        temp += y[i] * wt[i]
        twt += wt[i]
    mean = temp / twt
    ss = 0.0
    for i in range(n):
        diff = y[i] - mean
        ss += diff * diff * wt[i]
    value_box[0] = mean
    risk_box[0] = ss


def _anova(n, y, x, edge, improve_box, split_box, csplit, myrisk, wt):
    right_wt = 0.0
    right_n = n
    right_sum = 0.0
    for i in range(n):
        right_sum += y[i] * wt[i]
        right_wt += wt[i]
    grandmean = right_sum / right_wt
    left_sum = 0.0
    left_wt = 0.0
    left_n = 0
    right_sum = 0.0
    best = 0.0
    direction = LEFT
    where = 0
    i = 0
    while right_n > edge:
        left_wt += wt[i]
        right_wt -= wt[i]
        left_n += 1
        right_n -= 1
        temp = (y[i] - grandmean) * wt[i]
        left_sum += temp
        right_sum -= temp
        if x[i + 1] != x[i] and left_n >= edge:
            temp = left_sum * left_sum / left_wt + right_sum * right_sum / right_wt
            if temp > best:
                best = temp
                where = i
                direction = LEFT if left_sum < right_sum else RIGHT
        i += 1
    improve_box[0] = best / myrisk if myrisk else 0.0
    if best > 0:
        csplit[0] = direction
        split_box[0] = (x[where] + x[where + 1]) / 2.0


def _insert_split(head_box, ncat, improve, limit):
    if ncat == 0:
        ncat = 1
    head = head_box[0]
    if head is None:
        created = Split()
        head_box[0] = created
        return created
    if limit < 2:
        if improve <= head.improve:
            return None
        return head
    nlist = 1
    last = head
    before_last = None
    while last.nextsplit is not None:
        before_last = last
        last = last.nextsplit
        nlist += 1
    previous = head
    cursor = head
    while cursor is not None:
        if improve > cursor.improve:
            break
        previous = cursor
        cursor = cursor.nextsplit
    if nlist == limit:
        if cursor is None:
            return None
        if previous is before_last:
            last.nextsplit = None
        else:
            before_last.nextsplit = None
            last.nextsplit = cursor
        placed = last
    else:
        placed = Split()
        placed.nextsplit = cursor
    if cursor is head:
        head_box[0] = placed
    else:
        previous.nextsplit = placed
    return placed


def _bsplit(rp, me, n1, n2):
    me.primary = None
    head_box = [None]
    for i in range(rp.nvar):
        index = rp.sorts[i]
        k = 0
        for j in range(n1, n2):
            kk = index[j]
            if kk >= 0 and rp.wt[kk] > 0:
                rp.xtemp[k] = rp.xdata[i][kk]
                rp.ytemp[k] = rp.ydata[kk]
                rp.wtemp[k] = rp.wt[kk]
                k += 1
        if k == 0 or rp.xtemp[0] == rp.xtemp[k - 1]:
            continue
        improve_box = [0.0]
        split_box = [0.0]
        _anova(k, rp.ytemp, rp.xtemp, rp.min_node, improve_box, split_box, rp.csplit, me.risk, rp.wtemp)
        improve = improve_box[0]
        if improve > rp.iscale:
            rp.iscale = improve
        if improve > rp.iscale * 1e-10:
            improve = improve / rp.vcost[i]
            head_box[0] = me.primary
            placed = _insert_split(head_box, 0, improve, rp.maxpri)
            me.primary = head_box[0]
            if placed is not None:
                placed.improve = improve
                placed.var_num = i
                placed.spoint = split_box[0]
                placed.count = k
                placed.csplit = [rp.csplit[0]]


def _choose_surg(rp, n1, n2, y, x, order, tleft, tright):
    lastx = 0.0
    ll = rl = 0
    llwt = rlwt = 0.0
    for i in range(n2 - 1, n1 - 1, -1):
        j = order[i]
        if j >= 0:
            lastx = x[j]
            if y[j] == LEFT:
                if rp.wt[j] > 0:
                    ll += 1
                llwt += rp.wt[j]
            elif y[j] == RIGHT:
                if rp.wt[j] > 0:
                    rl += 1
                rlwt += rp.wt[j]
    agree = llwt if llwt > rlwt else rlwt
    majority = agree
    total_wt = llwt + rlwt
    lr = rr = 0
    lrwt = rrwt = 0.0
    csplit = LEFT
    split = lastx
    success = 0
    i = n1
    while (ll + rl) >= 2:
        j = order[i]
        if j >= 0:
            if (lr + rr) >= 2 and x[j] != lastx:
                if (llwt + rrwt) > agree:
                    success = 1
                    agree = llwt + rrwt
                    csplit = RIGHT
                    split = (x[j] + lastx) / 2.0
                elif (lrwt + rlwt) > agree:
                    success = 1
                    agree = lrwt + rlwt
                    csplit = LEFT
                    split = (x[j] + lastx) / 2.0
            if y[j] == LEFT:
                if rp.wt[j] > 0:
                    ll -= 1
                    lr += 1
                llwt -= rp.wt[j]
                lrwt += rp.wt[j]
            elif y[j] == RIGHT:
                if rp.wt[j] > 0:
                    rl -= 1
                    rr += 1
                rlwt -= rp.wt[j]
                rrwt += rp.wt[j]
            lastx = x[j]
        i += 1
        if i >= n2 and (ll + rl) >= 2:
            break
    if not success:
        return 0.0, 0.0, LEFT, 0.0
    if rp.sur_agree == 0:
        total_wt = tleft + tright
        majority = tleft if tleft > tright else tright
    agreement = agree / total_wt
    majority /= total_wt
    adj = (agreement - majority) / (1.0 - majority)
    return agreement, split, csplit, adj


def _surrogate(rp, me, n1, n2):
    var = me.primary.var_num
    split = me.primary.spoint
    extra = me.primary.csplit[0]
    tempy = [0] * rp.n
    for i in range(n1, n2):
        j = rp.sorts[var][i]
        if j < 0:
            tempy[-(j + 1)] = 0
        else:
            tempy[j] = extra if rp.xdata[var][j] < split else -extra
    lcount = 0.0
    rcount = 0.0
    for i in range(n1, n2):
        j = rp.sorts[var][i]
        if j < 0:
            j = -(1 + j)
        if tempy[j] == LEFT:
            lcount += rp.wt[j]
        elif tempy[j] == RIGHT:
            rcount += rp.wt[j]
    if lcount < rcount:
        me.lastsurrogate = RIGHT
    elif lcount > rcount:
        me.lastsurrogate = LEFT
    else:
        me.lastsurrogate = 0
    me.surrogate = None
    head_box = [None]
    for i in range(rp.nvar):
        if var == i:
            continue
        agreement, spoint, csplit, adj = _choose_surg(
            rp, n1, n2, tempy, rp.xdata[i], rp.sorts[i], lcount, rcount
        )
        if adj <= 1e-10:
            continue
        head_box[0] = me.surrogate
        placed = _insert_split(head_box, 0, agreement, rp.maxsur)
        me.surrogate = head_box[0]
        if placed is not None:
            placed.improve = agreement
            placed.var_num = i
            placed.count = 0
            placed.adj = adj
            placed.spoint = spoint
            placed.csplit = [csplit]


def _nodesplit(rp, me, nodenum, n1, n2):
    leftson = 2 * nodenum
    rightson = leftson + 1
    tsplit = me.primary
    pvar = tsplit.var_num
    someleft = 0
    nleft = 0
    nright = 0
    psplit = tsplit.spoint
    extra = tsplit.csplit[0]
    for i in range(n1, n2):
        j = rp.sorts[pvar][i]
        if j < 0:
            someleft += 1
        else:
            k = extra if rp.xdata[pvar][j] < psplit else -extra
            if k == LEFT:
                rp.which[j] = leftson
                nleft += 1
            else:
                rp.which[j] = rightson
                nright += 1
    if someleft > 0 and rp.usesurrogate > 0:
        for i in range(n1, n2):
            j = rp.sorts[pvar][i]
            if j >= 0:
                continue
            j = -(j + 1)
            tsplit = me.surrogate
            while tsplit is not None:
                var = tsplit.var_num
                value = rp.xdata[var][j]
                if value != value:  # missing
                    tsplit = tsplit.nextsplit
                    continue
                tsplit.count += 1
                direction = tsplit.csplit[0] if value < tsplit.spoint else -tsplit.csplit[0]
                if direction == LEFT:
                    rp.which[j] = leftson
                    nleft += 1
                else:
                    rp.which[j] = rightson
                    nright += 1
                someleft -= 1
                break
    if someleft > 0 and rp.usesurrogate == 2 and me.lastsurrogate:
        if me.lastsurrogate < 0:
            dest = leftson
            nleft += someleft
        else:
            dest = rightson
            nright += someleft
        for i in range(n1, n2):
            j = rp.sorts[pvar][i]
            if j < 0:
                j = -(j + 1)
                if rp.which[j] == nodenum:
                    rp.which[j] = dest
    for k in range(rp.nvar):
        sindex = rp.sorts[k]
        i1 = n1
        i2 = i1 + nleft
        i3 = i2 + nright
        for i in range(n1, n2):
            j = sindex[i]
            if j < 0:
                j = -(j + 1)
            if rp.which[j] == leftson:
                sindex[i1] = sindex[i]
                i1 += 1
            elif rp.which[j] == rightson:
                rp.tempvec[i2] = sindex[i]
                i2 += 1
            else:
                rp.tempvec[i3] = sindex[i]
                i3 += 1
        for i in range(n1 + nleft, n2):
            sindex[i] = rp.tempvec[i]
    return nleft, nright


def _free_children(node):
    node.primary = None
    node.surrogate = None
    node.rightson = None
    node.leftson = None


def _partition(rp, nodenum, me, n1, n2):
    n = n2 - n1
    if nodenum > 1:
        twt = 0.0
        k = 0
        for i in range(n1, n2):
            j = rp.sorts[0][i]
            if j < 0:
                j = -(1 + j)
            rp.wtemp[k] = rp.wt[j]
            rp.ytemp[k] = rp.ydata[j]
            twt += rp.wt[j]
            k += 1
        value_box = [0.0]
        risk_box = [0.0]
        _anovass(n, rp.ytemp, value_box, risk_box, rp.wtemp)
        me.response_est[0] = value_box[0]
        me.risk = risk_box[0]
        me.num_obs = n
        me.sum_wt = twt
        tempcp = me.risk if me.risk < me.complexity else me.complexity
    else:
        tempcp = me.risk
    if me.num_obs < rp.min_split or tempcp <= rp.alpha or nodenum > rp.maxnode:
        me.complexity = rp.alpha
        _free_children(me)
        return 0, me.risk
    _bsplit(rp, me, n1, n2)
    if me.primary is None:
        me.complexity = rp.alpha
        _free_children(me)
        return 0, me.risk
    if rp.maxsur > 0:
        _surrogate(rp, me, n1, n2)
    else:
        me.surrogate = None
    nleft, nright = _nodesplit(rp, me, nodenum, n1, n2)
    me.leftson = Node()
    me.leftson.complexity = tempcp - rp.alpha
    left_split, left_risk = _partition(rp, 2 * nodenum, me.leftson, n1, n1 + nleft)
    tempcp = (me.risk - left_risk) / (left_split + 1)
    tempcp2 = me.risk - me.leftson.risk
    if tempcp < tempcp2:
        tempcp = tempcp2
    if tempcp > me.complexity:
        tempcp = me.complexity
    me.rightson = Node()
    me.rightson.complexity = tempcp - rp.alpha
    right_split, right_risk = _partition(
        rp, 1 + 2 * nodenum, me.rightson, n1 + nleft, n1 + nleft + nright
    )
    tempcp = (me.risk - (left_risk + right_risk)) / (left_split + right_split + 1)
    if me.rightson.complexity > me.leftson.complexity:
        if tempcp > me.leftson.complexity:
            left_risk = me.leftson.risk
            left_split = 0
            tempcp = (me.risk - (left_risk + right_risk)) / (left_split + right_split + 1)
            if tempcp > me.rightson.complexity:
                right_risk = me.rightson.risk
                right_split = 0
    elif tempcp > me.rightson.complexity:
        right_split = 0
        right_risk = me.rightson.risk
        tempcp = (me.risk - (left_risk + right_risk)) / (left_split + right_split + 1)
        if tempcp > me.leftson.complexity:
            left_risk = me.leftson.risk
            left_split = 0
    me.complexity = (me.risk - (left_risk + right_risk)) / (left_split + right_split + 1)
    if me.complexity <= rp.alpha:
        _free_children(me)
        for i in range(n1, n2):
            j = rp.sorts[0][i]
            if j < 0:
                j = -(1 + j)
            rp.which[j] = nodenum
        return 0, me.risk
    return left_split + right_split + 1, left_risk + right_risk


def _make_cp_list(rp, me, parent, head):
    me_cp = me.complexity if me.complexity <= parent else parent
    if me.complexity > parent:
        me.complexity = parent
    if me_cp < rp.alpha:
        me_cp = rp.alpha
    if me.leftson is not None:
        _make_cp_list(rp, me.leftson, me_cp, head)
        _make_cp_list(rp, me.rightson, me_cp, head)
    if me_cp < parent:
        cplist = head
        cptemp = None
        while cplist is not None:
            if me_cp == cplist.cp:
                return
            if me_cp > cplist.cp:
                break
            cptemp = cplist
            cplist = cplist.forward
        created = CpRow()
        created.cp = me_cp
        created.back = cptemp
        created.forward = cptemp.forward
        if cptemp.forward is not None:
            cptemp.forward.back = created
        else:
            rp.cptable_tail = created
        cptemp.forward = created
        rp.num_unique_cp += 1


def _make_cp_table(rp, me, parent, nsplit):
    if me.leftson is not None:
        _make_cp_table(rp, me.leftson, me.complexity, 0)
        cplist = _make_cp_table(rp, me.rightson, me.complexity, nsplit + 1)
    else:
        cplist = rp.cptable_tail
    while cplist.cp < parent:
        cplist.risk += me.risk
        cplist.nsplit += nsplit
        cplist = cplist.back
    return cplist


def _fix_cp(me, parent_cp):
    if me.complexity > parent_cp:
        me.complexity = parent_cp
    if me.leftson is not None:
        _fix_cp(me.leftson, me.complexity)
        _fix_cp(me.rightson, me.complexity)


def _branch(rp, tree, obs):
    if tree.leftson is None:
        return None
    tsplit = tree.primary
    j = tsplit.var_num
    value = rp.xdata[j][obs]
    if value == value:
        direction = tsplit.csplit[0] if value < tsplit.spoint else -tsplit.csplit[0]
        return tree.leftson if direction == LEFT else tree.rightson
    if rp.usesurrogate == 0:
        return None
    tsplit = tree.surrogate
    while tsplit is not None:
        j = tsplit.var_num
        value = rp.xdata[j][obs]
        if value == value:
            direction = tsplit.csplit[0] if value < tsplit.spoint else -tsplit.csplit[0]
            return tree.leftson if direction == LEFT else tree.rightson
        tsplit = tsplit.nextsplit
    if rp.usesurrogate < 2:
        return None
    return tree.leftson if tree.lastsurrogate == LEFT else tree.rightson


def _rundown(rp, tree, obs, cp):
    obs2 = -(1 + obs) if obs < 0 else obs
    xpred = [0.0] * len(cp)
    xtemp = [0.0] * len(cp)
    otree = tree
    for i, threshold in enumerate(cp):
        while threshold < tree.complexity:
            nxt = _branch(rp, tree, obs)
            if nxt is None:
                for j in range(i, len(cp)):
                    xpred[j] = otree.response_est[0]
                    y = rp.ydata[obs2]
                    diff = y - otree.response_est[0]
                    xtemp[j] = diff * diff
                return xpred, xtemp
            tree = nxt
            otree = tree
        xpred[i] = tree.response_est[0]
        y = rp.ydata[obs2]
        diff = y - tree.response_est[0]
        xtemp[i] = diff * diff
    return xpred, xtemp


def _xval(rp, n_xval, head, x_grp, savesort):
    alphasave = rp.alpha
    savew = rp.which[:]
    cp = [0.0] * rp.num_unique_cp
    cp[0] = 10 * head.cp
    cplist = head
    for i in range(1, rp.num_unique_cp):
        cp[i] = math.sqrt(cplist.cp * cplist.forward.cp)
        cplist = cplist.forward
    total_wt = sum(rp.wt)
    old_wt = total_wt
    for xgroup in range(n_xval):
        for j in range(rp.nvar):
            k = 0
            for i in range(rp.n):
                ii = savesort[j][i]
                if ii < 0:
                    ii = -(1 + ii)
                if x_grp[ii] != xgroup + 1:
                    rp.sorts[j][k] = savesort[j][i]
                    k += 1
        last = k
        k = 0
        temp = 0.0
        for i in range(rp.n):
            rp.which[i] = 1
            if x_grp[i] == xgroup + 1:
                rp.sorts[0][last] = i
                last += 1
            else:
                rp.ytemp[k] = rp.ydata[i]
                rp.wtemp[k] = rp.wt[i]
                temp += rp.wt[i]
                k += 1
        for j in range(rp.num_unique_cp):
            cp[j] *= temp / old_wt
        rp.alpha *= temp / old_wt
        old_wt = temp
        xtree = Node()
        xtree.num_obs = k
        value_box = [0.0]
        risk_box = [0.0]
        _anovass(k, rp.ytemp, value_box, risk_box, rp.wtemp)
        xtree.response_est[0] = value_box[0]
        xtree.risk = risk_box[0]
        xtree.complexity = xtree.risk
        _partition(rp, 1, xtree, 0, k)
        _fix_cp(xtree, xtree.complexity)
        for i in range(k, rp.n):
            j = rp.sorts[0][i]
            _pred, xtemp = _rundown(rp, xtree, j, cp)
            cplist = head
            for jj in range(rp.num_unique_cp):
                cplist.xrisk += xtemp[jj] * rp.wt[j]
                cplist.xstd += xtemp[jj] * xtemp[jj] * rp.wt[j]
                cplist = cplist.forward
    cplist = head
    while cplist is not None:
        cplist.xstd = math.sqrt(cplist.xstd - cplist.xrisk * cplist.xrisk / total_wt)
        cplist = cplist.forward
    rp.alpha = alphasave
    rp.which = savew


def _rows_from_tree(rp, tree):
    scale = 1.0 / tree.risk
    nodes = []
    splits = []

    def walk(me, node_id):
        primary = []
        cursor = me.primary
        while cursor is not None:
            primary.append(cursor)
            cursor = cursor.nextsplit
        surrogates = []
        cursor = me.surrogate
        while cursor is not None:
            surrogates.append(cursor)
            cursor = cursor.nextsplit
        terminal = me.complexity <= rp.alpha or me.leftson is None
        record = {
            "id": node_id,
            "risk": me.risk,
            "complexity": me.complexity * scale,
            "wt": me.sum_wt,
            "yval": me.response_est[0],
            "n": me.num_obs,
            "nprimary": 0 if terminal else len(primary),
            "nsurrogate": 0 if terminal else len(surrogates),
            "split_index": 0 if terminal else len(splits) + 1,
        }
        nodes.append(record)
        if not terminal:
            for spl in primary:
                splits.append({
                    "var": spl.var_num,
                    "count": spl.count,
                    "ncat": spl.csplit[0],
                    "improve": spl.improve,
                    "index": spl.spoint,
                    "adj": 0.0,
                })
            for spl in surrogates:
                splits.append({
                    "var": spl.var_num,
                    "count": spl.count,
                    "ncat": spl.csplit[0],
                    "improve": spl.improve,
                    "index": spl.spoint,
                    "adj": spl.adj,
                })
            walk(me.leftson, 2 * node_id)
            walk(me.rightson, 2 * node_id + 1)

    walk(tree, 1)
    id_to_row = {node["id"]: i + 1 for i, node in enumerate(nodes)}
    where = []
    for obs in range(rp.n):
        k = rp.which[obs]
        while True:
            if k in id_to_row:
                where.append(id_to_row[k])
                break
            k //= 2
    return nodes, splits, where, scale


def _cp_rows(head, scale, with_xval):
    rows = []
    cursor = head
    while cursor is not None:
        row = [cursor.cp * scale, float(cursor.nsplit), cursor.risk * scale]
        if with_xval:
            row.extend([cursor.xrisk * scale, cursor.xstd * scale])
        rows.append(row)
        cursor = cursor.forward
    return rows


def _prepare(y, x, wt, control, cost):
    rp = _Rp()
    n = len(y)
    nvar = len(x[0])
    rp.n = n
    rp.nvar = nvar
    rp.min_split = int(control["minsplit"])
    rp.min_node = int(control["minbucket"])
    rp.complexity = float(control["cp"])
    rp.maxpri = int(control["maxcompete"]) + 1
    if rp.maxpri < 1:
        rp.maxpri = 1
    rp.maxsur = int(control["maxsurrogate"])
    rp.usesurrogate = int(control["usesurrogate"])
    rp.sur_agree = int(control["surrogatestyle"])
    rp.maxnode = int(2.0 ** float(control["maxdepth"])) - 1
    rp.wt = [1.0] * n if wt is None else [float(item) for item in wt]
    rp.vcost = [1.0] * nvar if cost is None else [float(item) for item in cost]
    rp.numcat = [0] * nvar
    rp.ydata = [float(item) for item in y]
    rp.xdata = [[float(x[row][col]) for row in range(n)] for col in range(nvar)]
    rp.tempvec = [0] * n
    rp.xtemp = [0.0] * n
    rp.ytemp = [0.0] * n
    rp.wtemp = [0.0] * n
    rp.which = [1] * n
    rp.csplit = [0]
    rp.sorts = []
    for i in range(nvar):
        tempvec = []
        xtemp = []
        for k in range(n):
            value = rp.xdata[i][k]
            if value != value or math.isinf(value):
                tempvec.append(-(k + 1))
                xtemp.append(0.0)
            else:
                tempvec.append(k)
                xtemp.append(value)
        _mysort(0, n - 1, xtemp, tempvec)
        rp.sorts.append(tempvec)
    return rp


def grow_anova(y, x, wt=None, control=None, cost=None, xgroups=None):
    """Grow an anova tree. ``x`` is a list of rows."""
    from rpart.control import rpart_control

    if control is None:
        control = rpart_control()
    rp = _prepare(y, x, wt, control, cost)
    value_box = [0.0]
    risk_box = [0.0]
    _anovass(rp.n, rp.ydata, value_box, risk_box, rp.wt)
    tree = Node()
    tree.num_obs = rp.n
    tree.sum_wt = sum(rp.wt)
    tree.response_est[0] = value_box[0]
    tree.risk = risk_box[0]
    tree.complexity = tree.risk
    rp.alpha = rp.complexity * tree.risk
    xval = int(control["xval"])
    savesort = [column[:] for column in rp.sorts] if xval > 1 else None
    _partition(rp, 1, tree, 0, rp.n)
    head = CpRow()
    head.cp = tree.complexity
    head.risk = tree.risk
    head.nsplit = 0
    rp.num_unique_cp = 1
    rp.cptable_tail = head
    groups = None
    if tree.rightson is not None:
        _make_cp_list(rp, tree, tree.complexity, head)
        _make_cp_table(rp, tree, tree.complexity, 0)
        if xval > 1:
            if xgroups is None:
                pool = [((i % xval) + 1) for i in range(rp.n)]
                draw = sample_int(rp.n)
                groups = [pool[slot - 1] for slot in draw]
            else:
                groups = list(xgroups)
            _xval(rp, xval, head, groups, savesort)
    nodes, splits, where, scale = _rows_from_tree(rp, tree)
    return {
        "nodes": nodes,
        "splits": splits,
        "where": where,
        "cptable": _cp_rows(head, scale, xval > 1 and tree.rightson is not None),
        "xgroups": groups,
        "y": rp.ydata[:],
        "x": [[rp.xdata[col][row] for col in range(rp.nvar)] for row in range(rp.n)],
        "wt": rp.wt[:],
        "iscale": rp.iscale,
        "risk": tree.risk,
    }


def _rundown2(rp, tree, obs, cp):
    otree = tree
    out = []
    i = 0
    ncp = rp.num_unique_cp
    while i < ncp:
        while cp[i] < tree.complexity:
            nxt = _branch(rp, tree, obs)
            if nxt is None:
                while i < ncp:
                    out.append(otree.response_est[0])
                    i += 1
                return out
            tree = nxt
            otree = tree
        out.append(tree.response_est[0])
        i += 1
    return out


def xpred_anova(y, x, wt, control, cp, toprisk, xgroups, n_xval, iscale=0.0):
    """Cross-validated anova predictions at each complexity value."""
    rp = _prepare(y, x, wt, control, None)
    rp.iscale = float(iscale)
    ncp = len(cp)
    rp.num_unique_cp = ncp
    scaled = [float(value) * float(toprisk) for value in cp]
    rp.alpha = float(control["cp"]) * float(toprisk)
    savesort = [column[:] for column in rp.sorts]
    xval = int(n_xval)
    groups = list(xgroups)
    total_wt = sum(rp.wt)
    old_wt = total_wt
    predict = [[0.0] * ncp for _ in range(rp.n)]
    for xgroup in range(xval):
        for j in range(rp.nvar):
            k = 0
            for i in range(rp.n):
                ii = savesort[j][i]
                if ii < 0:
                    ii = -(1 + ii)
                if groups[ii] != xgroup + 1:
                    rp.sorts[j][k] = savesort[j][i]
                    k += 1
        last = k
        k = 0
        temp = 0.0
        for i in range(rp.n):
            rp.which[i] = 1
            if groups[i] == xgroup + 1:
                rp.sorts[0][last] = i
                last += 1
            else:
                rp.ytemp[k] = rp.ydata[i]
                rp.wtemp[k] = rp.wt[i]
                temp += rp.wt[i]
                k += 1
        for j in range(ncp):
            scaled[j] *= temp / old_wt
        rp.alpha *= temp / old_wt
        old_wt = temp
        xtree = Node()
        xtree.num_obs = k
        value_box = [0.0]
        risk_box = [0.0]
        _anovass(k, rp.ytemp, value_box, risk_box, rp.wtemp)
        xtree.response_est[0] = value_box[0]
        xtree.risk = risk_box[0]
        xtree.complexity = xtree.risk
        _partition(rp, 1, xtree, 0, k)
        _fix_cp(xtree, xtree.complexity)
        for i in range(k, rp.n):
            j = rp.sorts[0][i]
            predict[j] = _rundown2(rp, xtree, j, scaled)
    return predict
