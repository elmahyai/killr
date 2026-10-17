"""Time-based merge for survival data (survival::tmerge)."""

from __future__ import annotations

import math
import re
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from survival.fromtimeline import Categorical, TimelineFrame, _duplicated
from survival.neardate import neardate
from survival.surv_split import _as_table, _column_len


_UNSET = object()


def tdc(time, value=None, init=None):
    return {"kind": "tdc", "time": time, "value": value, "default": init, "censor": None}


def cumtdc(time, value=None, init=None):
    return {"kind": "cumtdc", "time": time, "value": value, "default": init, "censor": None}


def event(time, value=None, censor=None):
    return {"kind": "event", "time": time, "value": value, "censor": censor}


def cumevent(time, value=None, censor=None):
    return {"kind": "cumevent", "time": time, "value": value, "censor": censor}


def _make_names(text: str) -> str:
    out = re.sub(r"[^A-Za-z0-9._]", ".", str(text))
    if out and out[0].isdigit():
        out = "X." + out
    return out


def _col_list(col: Any) -> list[Any]:
    if isinstance(col, Categorical):
        return list(col.values)
    if isinstance(col, np.ndarray):
        return col.tolist()
    return list(col)


def _is_na(x: Any) -> bool:
    if x is None:
        return True
    if isinstance(x, float) and math.isnan(x):
        return True
    return False


def _match_vec(x, table):
    first: dict[Any, int] = {}
    for index, value in enumerate(table, start=1):
        if value not in first:
            first[value] = index
    out = []
    for value in x:
        if _is_na(value):
            out.append(None)
        else:
            out.append(first.get(value))
    return out


def _copy_table(table: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, col in table.items():
        if isinstance(col, Categorical):
            out[key] = Categorical(list(col.values), list(col.levels))
        elif isinstance(col, np.ndarray):
            out[key] = np.array(col, copy=True)
        else:
            out[key] = list(col)
    return out


def _nrow(table: dict[str, Any]) -> int:
    return _column_len(next(iter(table.values())))


def _subset_rows(table: dict[str, Any], idx) -> dict[str, Any]:
    idx = np.asarray(idx, dtype=int)
    out: dict[str, Any] = {}
    for key, col in table.items():
        if isinstance(col, Categorical):
            out[key] = Categorical([col.values[i] for i in idx], col.levels)
        elif isinstance(col, np.ndarray):
            out[key] = col[idx]
        else:
            out[key] = [col[i] for i in idx]
    return out


def _expand_rows(table: dict[str, Any], jrep: np.ndarray) -> dict[str, Any]:
    jrep = np.asarray(jrep, dtype=int) - 1
    out: dict[str, Any] = {}
    for key, col in table.items():
        if isinstance(col, Categorical):
            out[key] = Categorical([col.values[i] for i in jrep], col.levels)
        elif isinstance(col, np.ndarray):
            out[key] = col[jrep]
        else:
            out[key] = [col[i] for i in jrep]
    return out


def _tmerge_control(**kwargs):
    idname = kwargs.get("idname", "id")
    tstartname = kwargs.get("tstartname", "tstart")
    tstopname = kwargs.get("tstopname", "tstop")
    delay = kwargs.get("delay", 0)
    na_rm = kwargs.get("na_rm", kwargs.get("na.rm", True))
    tdcstart = kwargs.get("tdcstart", float("nan"))
    extras = {k: v for k, v in kwargs.items() if k not in ("idname", "tstartname", "tstopname", "delay", "na_rm", "na.rm", "tdcstart")}
    if extras:
        raise ValueError("unrecognized option(s):" + ",".join(extras))
    if not isinstance(idname, str) or _make_names(idname) != idname:
        raise ValueError("idname option must be a valid variable name")
    if tstartname is not None and (not isinstance(tstartname, str) or _make_names(tstartname) != tstartname):
        raise ValueError("tstart option must be NULL or a valid variable name")
    if not isinstance(tstopname, str) or _make_names(tstopname) != tstopname:
        raise ValueError("tstop option must be a valid variable name")
    if not isinstance(delay, (int, float)) or delay < 0:
        raise ValueError("delay option must be a number >= 0")
    if not isinstance(na_rm, (bool, np.bool_)):
        raise ValueError("na.rm option must be TRUE or FALSE")
    return {
        "idname": idname,
        "tstartname": tstartname,
        "tstopname": tstopname,
        "delay": float(delay),
        "na.rm": bool(na_rm),
        "tdcstart": tdcstart,
    }


def _ctmerge2(id_base, time1, id_new, ntime) -> np.ndarray:
    id_base = np.asarray(id_base, dtype=int)
    time1 = np.asarray(time1, dtype=float)
    id_new = np.asarray(id_new, dtype=int)
    ntime = np.asarray(ntime, dtype=float)
    n1 = id_base.size
    n2 = id_new.size
    index = np.zeros(n1, dtype=int)
    k = 0
    for i in range(n1):
        while k < n2 and id_new[k] < id_base[i]:
            k += 1
        while k < n2 and id_new[k] == id_base[i] and ntime[k] <= time1[i]:
            index[i] = k + 1
            k += 1
        k = max(0, k - 1)
    return index


def _ctmerge(id_base, time1, newx, id_new, ntime, x) -> np.ndarray:
    id_base = np.asarray(id_base, dtype=int)
    time1 = np.asarray(time1, dtype=float)
    newx = np.asarray(newx, dtype=float).copy()
    id_new = np.asarray(id_new, dtype=int)
    ntime = np.asarray(ntime, dtype=float)
    x = np.asarray(x, dtype=float)
    n1 = id_base.size
    n2 = id_new.size
    oldid = -1
    k = 0
    for i in range(n1):
        if id_base[i] != oldid:
            csum = 0.0
            oldid = id_base[i]
            hasone = 0
        while k < n2 and id_new[k] < id_base[i]:
            k += 1
        while k < n2 and id_new[k] == id_base[i] and ntime[k] <= time1[i]:
            csum += x[k]
            hasone = 1
            k += 1
        if hasone == 1:
            if math.isnan(newx[i]):
                newx[i] = csum
            else:
                newx[i] = newx[i] + csum
    return newx


@dataclass
class TmergeFrame:
    names: list[str]
    columns: list[Any]
    tm_retain: dict[str, Any] | None = None
    tcount: np.ndarray | None = None
    tcount_rownames: list[str] | None = None

    def __len__(self) -> int:
        return _column_len(self.columns[0]) if self.columns else 0


def is_tmerge(x: Any) -> bool:
    return isinstance(x, TmergeFrame)


def _frame_to_table(frame: TmergeFrame) -> dict[str, Any]:
    return {n: c for n, c in zip(frame.names, frame.columns)}


def _table_to_frame(table: dict[str, Any], **attrs) -> TmergeFrame:
    names = list(table.keys())
    return TmergeFrame(names, [table[n] for n in names], **attrs)


def _resolve(data2_table, var):
    if isinstance(var, str) and var in data2_table:
        return _col_list(data2_table[var])
    return _col_list(var)


def _arg_kind(spec):
    if isinstance(spec, dict) and "kind" in spec:
        return spec["kind"]
    raise ValueError("not a recognized type")


def _tcount_row(itype, subtype, idmiss, etime, id_sub):
    counts = {1: 0, 2: 0, 3: 0, 4: 0, 6: 0, 7: 0, 8: 0}
    for it, st in zip(itype, subtype):
        key = it if it != 5 else it + st
        counts[key] = counts.get(key, 0) + 1
    row = [counts.get(i, 0) for i in (1, 2, 3, 4, 6, 7, 8)]
    tied = 0
    by_id: dict[Any, list] = {}
    for e, i in zip(etime, id_sub):
        by_id.setdefault(i, []).append(e)
    for vals in by_id.values():
        dup = _duplicated(vals)
        tied += int(sum(dup))
    row.extend([tied, idmiss])
    return row


def tmerge(
    data1,
    data2,
    *,
    id,
    tstart=_UNSET,
    tstop=_UNSET,
    options=None,
    **operations,
):
    if data1 is None or data2 is None or id is None:
        raise ValueError("the data1, data2, and id arguments are required")

    if isinstance(data1, TmergeFrame):
        frame1 = data1
        table1 = _copy_table(_frame_to_table(frame1))
    else:
        table1 = _copy_table(_as_table(data1))
        frame1 = TmergeFrame(list(table1.keys()), [table1[k] for k in table1])

    data2_table = _as_table(data2)
    firstcall = frame1.tm_retain is None
    tname = None
    tevent_obj = None
    tdcvar: list[str] = []

    if not firstcall:
        tm_retain = frame1.tm_retain or {}
        tname = tm_retain["tname"]
        tevent_obj = tm_retain.get("tevent")
        tdcvar = list(tm_retain.get("tdcvar") or [])
        if _nrow(table1) != tm_retain["n"]:
            raise ValueError("tmerge object has been modified, size")
        for v in tname.values():
            if v not in table1:
                raise ValueError("tmerge object has been modified, missing variables")
        if tevent_obj:
            for ename in tevent_obj["name"]:
                if ename not in table1:
                    raise ValueError("tmerge object has been modified, missing variables")
        for v in tdcvar:
            if v not in table1:
                raise ValueError("tmerge object has been modified, missing variables")

    if firstcall and isinstance(id, str):
        if options is None:
            options = {"idname": id}
        elif options.get("idname") is None:
            options = {**options, "idname": id}

    if options is not None:
        if not isinstance(options, dict):
            raise ValueError("options must be a list")
        kw = dict(options)
        if "na.rm" in kw:
            kw["na_rm"] = kw.pop("na.rm")
        if tname is not None:
            merged = {**tname, **{k: v for k, v in kw.items() if k not in tname}}
            for k in ("idname", "tstartname", "tstopname", "delay", "tdcstart"):
                if k in kw:
                    merged[k] = kw[k]
            if "na_rm" in kw:
                merged["na.rm"] = kw["na_rm"]
            topt = _tmerge_control(**merged)
        else:
            topt = _tmerge_control(**kw)
    elif tname:
        topt = _tmerge_control(**tname)
    else:
        topt = _tmerge_control()

    if isinstance(id, str):
        if id not in data2_table:
            raise ValueError("id variable not found in data2")
        id_values = _col_list(data2_table[id])
    else:
        id_values = _col_list(id)
    if any(_is_na(v) for v in id_values):
        raise ValueError("id variable cannot have missing values")

    tstart_vals = _UNSET
    tstop_vals = _UNSET
    if firstcall:
        if tstop is not _UNSET:
            tstop_vals = _resolve(data2_table, tstop)
            if len(tstop_vals) != len(id_values):
                raise ValueError("tstop and id must be the same length")
        if tstart is not _UNSET:
            tstart_vals = _resolve(data2_table, tstart)
            if len(tstart_vals) == 1:
                tstart_vals = tstart_vals * len(id_values)
            if len(tstart_vals) != len(id_values):
                raise ValueError("tstart and id must be the same length")
            if tstop_vals is not _UNSET and any(a >= b for a, b in zip(tstart_vals, tstop_vals)):
                raise ValueError("tstart must be < tstop")
    elif tstart is not _UNSET or tstop is not _UNSET:
        raise ValueError("tstart and tstop arguments only apply to the first call")

    argname = list(operations.keys())
    if any(not n for n in argname):
        raise ValueError("all additional argments must have a name")
    argclass = [_arg_kind(operations[n]) for n in argname]
    if any(c is None for c in argclass):
        bad = [argname[i] for i, c in enumerate(argclass) if c is None]
        raise ValueError("argument(s) " + " ".join(bad) + " not a recognized type")

    tcount = np.zeros((len(argname), 9), dtype=int)
    tcens: dict[str, Any] = {}
    tevent: list[str] = []
    if tevent_obj:
        tevent = list(tevent_obj["name"])
        for i, ename in enumerate(tevent):
            tcens[ename] = tevent_obj["censor"][i]

    newdata = _copy_table(table1)
    idmiss = 0

    if firstcall:
        if not isinstance(id, str):
            raise ValueError("on the first call 'id' must be a single variable name")
        if id not in table1:
            raise ValueError("id variable not found in data1")
        baseid = _col_list(table1[id])
        newdata[topt["idname"]] = baseid
        if len(set(baseid)) != len(baseid):
            raise ValueError(
                "for the first call (that establishes the time range) data1 must have no duplicate identifiers"
            )

        if tstop_vals is _UNSET:
            if not argclass or argclass[0] != "event":
                raise ValueError("neither a tstop argument nor an initial event argument was found")
            first_spec = operations[argname[0]]
            etime0 = _resolve(data2_table, first_spec["time"])
            last = [not d for d in _duplicated(id_values)]
            tstop_map = {}
            for i in range(len(id_values)):
                if last[i]:
                    tstop_map[id_values[i]] = etime0[i]
            uid = list(dict.fromkeys([id_values[i] for i in range(len(id_values)) if last[i]]))
            indx2 = _match_vec(uid, baseid)
            if any(x is None for x in indx2):
                raise ValueError("setting the range, and data2 has id values not in data1")
            if any(_match_vec([b], id_values)[0] is None for b in baseid):
                raise ValueError("setting the range, and data1 has id values not in data2")
            newdata = _subset_rows(newdata, [i - 1 for i in indx2])
            tstop_vals = [tstop_map[baseid[i - 1]] for i in indx2]
        else:
            if not (len(baseid) == len(id_values) and baseid == id_values):
                indx2 = _match_vec(id_values, baseid)
                if any(x is None for x in indx2):
                    raise ValueError("setting the range, and data2 has id values not in data1")
                if any(_match_vec([b], id_values)[0] is None for b in baseid):
                    raise ValueError("setting the range, and data1 has id values not in data2")
                newdata = _subset_rows(newdata, [i - 1 for i in indx2])

        if any(_is_na(v) for v in tstop_vals):
            raise ValueError("missing time value, when that variable defines the span")
        if tstart_vals is _UNSET:
            for ts in tstop_vals:
                if ts <= 0:
                    raise ValueError(f"found an ending time of {ts}, the default starting time of 0 is invalid")
            tstart_vals = [0.0] * len(tstop_vals)
        if any(a >= b for a, b in zip(tstart_vals, tstop_vals)):
            raise ValueError("tstart must be < tstop")

        newdata[topt["tstartname"]] = list(tstart_vals)
        newdata[topt["tstopname"]] = list(tstop_vals)
        n = _nrow(newdata)

        if len(set(id_values)) != len(id_values):
            uid_order = []
            seen = set()
            for v in id_values:
                if v not in seen:
                    uid_order.append(v)
                    seen.add(v)
            indx1_sort = [_match_vec([v], uid_order)[0] for v in id_values]
            order = sorted(range(len(id_values)), key=lambda i: (indx1_sort[i], tstop_vals[i]))
            newdata = _subset_rows(newdata, order)
            tstart_vals = [tstart_vals[i] for i in order]
            tstop_vals = [tstop_vals[i] for i in order]
            newdata[topt["tstartname"]] = tstart_vals
            newdata[topt["tstopname"]] = tstop_vals

        temp = _col_list(newdata[topt["idname"]])
        tstarts = _col_list(newdata[topt["tstartname"]])
        tstops = _col_list(newdata[topt["tstopname"]])
        n = _nrow(newdata)
        if any(a >= b for a, b in zip(tstarts, tstops)):
            raise ValueError("tstart must be < tstop")
        for i in range(n - 1):
            if tstops[i] > tstarts[i + 1] and temp[i] == temp[i + 1]:
                raise ValueError("first call has created overlapping or duplicated time intervals")
    else:
        idmatch = _match_vec(id_values, _col_list(newdata[topt["idname"]]))
        idmiss = sum(1 for m in idmatch if not m)

    saveid = list(id_values)

    for ii, aname in enumerate(argname):
        argi = operations[aname]
        baseid = _col_list(newdata[topt["idname"]])
        dstart = _col_list(newdata[topt["tstartname"]])
        dstop = _col_list(newdata[topt["tstopname"]])

        etime = _resolve(data2_table, argi["time"])
        if idmiss == 0:
            keep = [True] * len(etime)
        else:
            idmatch = _match_vec(saveid, _col_list(newdata[topt["idname"]]))
            keep = [bool(m) for m in idmatch]

        if len(etime) != len(saveid):
            raise ValueError(f"argument {aname} is not the same length as id")

        yinc = None
        if argi.get("value") is not None:
            yinc = _resolve(data2_table, argi["value"])
            if len(yinc) != len(saveid):
                raise ValueError(f"argument {aname} is not the same length as id")
            if topt["na.rm"]:
                keep = [k and not _is_na(e) and not _is_na(v) for k, e, v in zip(keep, etime, yinc)]
            else:
                keep = [k and not _is_na(e) for k, e in zip(keep, etime)]
            etime = [e for e, k in zip(etime, keep) if k]
            yinc = [v for v, k in zip(yinc, keep) if k]
        else:
            keep = [k and not _is_na(e) for k, e in zip(keep, etime)]
            etime = [e for e, k in zip(etime, keep) if k]

        id_sub = [v for v, k in zip(saveid, keep) if k]
        order = sorted(
            range(len(id_sub)),
            key=lambda i: (_match_vec([id_sub[i]], baseid)[0] or 0, etime[i]),
        )
        id_sub = [id_sub[i] for i in order]
        etime = [etime[i] for i in order]
        if yinc is not None:
            yinc = [yinc[i] for i in order]

        if topt["delay"] > 0 and argclass[ii] in ("tdc", "cumtdc"):
            mintime: dict[Any, float] = {}
            for bid, ds in zip(baseid, dstart):
                cur = mintime.get(bid)
                if cur is None or ds < cur:
                    mintime[bid] = float(ds)
            etime = [e if e <= mintime[i] else e + topt["delay"] for e, i in zip(etime, id_sub)]

        indx1 = neardate(id_sub, baseid, etime, dstart, best="prior")
        indx2 = neardate(id_sub, baseid, etime, dstop, best="after")

        itype = []
        for j in range(len(etime)):
            i1, i2, et = indx1[j], indx2[j], etime[j]
            if i1 is None:
                itype.append(1)
            elif i2 is None:
                itype.append(2)
            elif i2 > i1:
                itype.append(3)
            elif et == dstart[i1 - 1] or et == dstop[i2 - 1]:
                itype.append(5)
            else:
                itype.append(4)

        subtype = []
        for j, it in enumerate(itype):
            if it != 5:
                subtype.append(0)
            elif indx1[j] == indx2[j] + 1:
                subtype.append(1)
            elif etime[j] == dstart[indx1[j] - 1]:
                subtype.append(2)
            else:
                subtype.append(3)

        tcount[ii, :] = _tcount_row(itype, subtype, idmiss, etime, id_sub)

        indx4 = [j for j, it in enumerate(itype) if it == 4]
        if indx4:
            pairs = list(dict.fromkeys((indx1[j], etime[j]) for j in indx4))
            n_add: dict[int, int] = {}
            for irow, _ in pairs:
                n_add[irow] = n_add.get(irow, 0) + 1
            nrow0 = _nrow(newdata)
            irep = np.ones(nrow0, dtype=int)
            erow = sorted({indx1[j] for j in indx4})
            for er in erow:
                irep[er - 1] = 1 + n_add[er]
            jrep = np.concatenate([np.full(rep, r, dtype=int) for r, rep in enumerate(irep, start=1)])
            newdata = _expand_rows(newdata, jrep)
            dstart = _col_list(newdata[topt["tstartname"]])
            dstop = _col_list(newdata[topt["tstopname"]])
            iend = np.cumsum(irep)[irep > 1]
            newrows = []
            pos = 0
            ic_by_row: dict[int, list] = {}
            for irow, et in pairs:
                ic_by_row.setdefault(irow, []).append(et)
            flat_times = []
            for er in erow:
                flat_times.extend(ic_by_row[er])
            for er in erow:
                na = n_add[er]
                end_row = iend[pos]
                newrows.extend(list(-np.arange(na - 1, -1, -1) + end_row))
                pos += 1
            for k, nr in enumerate(newrows):
                tval = flat_times[k]
                dstart[nr - 1] = tval
                dstop[nr - 2] = tval
            newdata[topt["tstartname"]] = dstart
            newdata[topt["tstopname"]] = dstop
            for ename in tevent:
                cens_val = tcens[ename]
                col = _col_list(newdata[ename])
                for nr in newrows:
                    col[nr - 2] = cens_val
                newdata[ename] = col
            baseid = _col_list(newdata[topt["idname"]])
            dstart = _col_list(newdata[topt["tstartname"]])
            dstop = _col_list(newdata[topt["tstopname"]])
            indx1 = neardate(id_sub, baseid, etime, dstart, best="prior")
            indx2 = neardate(id_sub, baseid, etime, dstop, best="after")
            for j in range(len(itype)):
                if itype[j] == 4:
                    subtype[j] = 1
                    itype[j] = 5

        newvar = newdata.get(aname)
        if argclass[ii] in ("tdc", "cumtdc"):
            if aname in tevent:
                raise ValueError(f"attempt to turn event variable{aname}into a tdc")
            if aname not in tdcvar:
                tdcvar.append(aname)
                if newvar is not None and argclass[ii] == "tdc":
                    warnings.warn(f"replacement of variable '{aname}'")
                    newvar = None

        if argclass[ii] == "tdc":
            default = argi.get("default")
            if default is None:
                default = topt["tdcstart"]
            uid = list(dict.fromkeys(baseid))
            uid_map = {u: i + 1 for i, u in enumerate(uid)}
            index = _ctmerge2(
                [uid_map[b] for b in baseid],
                np.asarray(dstart, dtype=float),
                [uid_map[i] for i in id_sub],
                np.asarray(etime, dtype=float),
            )
            if newvar is None:
                if yinc is None:
                    newvar = [0 if ix == 0 else 1 for ix in index]
                else:
                    newvar = [yinc[max(1, ix) - 1] for ix in index]
                    if any(ix == 0 for ix in index):
                        if _is_na(default):
                            for k, ix in enumerate(index):
                                if ix == 0:
                                    newvar[k] = float("nan")
                        else:
                            for k, ix in enumerate(index):
                                if ix == 0:
                                    newvar[k] = default
            elif yinc is None:
                nv = _col_list(newvar)
                if all(_is_na(v) or v == 0 or v == 1 for v in nv):
                    nv = list(nv)
                    for k, ix in enumerate(index):
                        if ix != 0:
                            nv[k] = 1
                    newvar = nv
                else:
                    raise ValueError(f"tdc update does not match prior variable type: {aname}")
            else:
                nv = _col_list(newvar)
                for k, ix in enumerate(index):
                    if ix != 0:
                        nv[k] = yinc[ix - 1]
                newvar = nv
            if aname not in tdcvar:
                tdcvar.append(aname)

        if argclass[ii] in ("cumtdc", "cumevent"):
            if yinc is None:
                yinc = [1.0] * len(id_sub)
            elif all(isinstance(v, (bool, np.bool_)) for v in yinc):
                yinc = [float(v) for v in yinc]
            if not all(isinstance(v, (int, float)) for v in yinc):
                raise ValueError("invalid increment for cumtdc or cumevent")

        ykeep = None
        if argclass[ii] == "cumevent":
            ykeep = [v != 0 for v in yinc]
            bm = _match_vec(id_sub, baseid)
            grouped: dict[Any, list[float]] = {}
            for yi, b in zip(yinc, bm):
                grouped.setdefault(b, []).append(yi)
            for b in grouped:
                grouped[b] = list(np.cumsum(grouped[b]))
            pos = {b: 0 for b in grouped}
            yinc_new = []
            for yi, b in zip(yinc, bm):
                g = grouped[b]
                yinc_new.append(g[pos[b]])
                pos[b] += 1
            yinc = yinc_new

        if argclass[ii] in ("event", "cumevent"):
            if newvar is not None and aname not in tevent:
                newvar = None
            if yinc is None:
                yinc = [1] * len(id_sub)
            if newvar is None:
                nrow = _nrow(newdata)
                sample = yinc[0]
                if isinstance(sample, (int, float, np.integer, np.floating)):
                    newvar = [0] * nrow
                elif isinstance(sample, str):
                    newvar = [""] * nrow
                elif isinstance(sample, (bool, np.bool_)):
                    newvar = [False] * nrow
                elif isinstance(sample, Categorical):
                    newvar = Categorical([sample.levels[0]] * nrow, sample.levels)
                else:
                    newvar = [0] * nrow

            if isinstance(newvar, Categorical):
                nv = list(newvar.values)
            else:
                nv = _col_list(newvar)
            keep_ev = [(subtype[j] == 1 or subtype[j] == 3) for j in range(len(subtype))]
            if argclass[ii] == "cumevent":
                keep_ev = [k and ykeep[j] for j, k in enumerate(keep_ev)]
            for j, k in enumerate(keep_ev):
                if k and indx2[j] is not None:
                    nv[indx2[j] - 1] = yinc[j]
            if isinstance(newvar, Categorical):
                newvar = Categorical(nv, newvar.levels)
            else:
                newvar = nv

            if aname not in tevent:
                tevent.append(aname)
                y0 = yinc[0]
                if isinstance(y0, Categorical):
                    tcens[aname] = y0.levels[0]
                elif isinstance(y0, bool):
                    tcens[aname] = False
                elif isinstance(y0, str):
                    tcens[aname] = ""
                elif isinstance(y0, int):
                    tcens[aname] = 0
                else:
                    tcens[aname] = 0

        elif argclass[ii] == "cumtdc":
            if aname in tevent:
                raise ValueError(f"attempt to turn event variable{aname}into a cumtdc")
            keep_c = [it != 2 for it in itype]
            indx_c = []
            for j, st in enumerate(subtype):
                if st == 1:
                    indx_c.append(indx1[j])
                elif st == 3:
                    indx_c.append((indx2[j] or 0) + 1)
                else:
                    indx_c.append(indx2[j])
            default = argi.get("default")
            if default is None:
                default = float(topt["tdcstart"]) if not _is_na(topt["tdcstart"]) else float("nan")
            elif not isinstance(default, (int, float)):
                raise ValueError("cumtdc initial value must be numeric")
            if newvar is None:
                newvar = [0.0] * _nrow(newdata) if argi.get("value") is None else [float(default)] * _nrow(newdata)
            nv = np.asarray(_col_list(newvar), dtype=float)
            id_keep = [id_sub[j] for j in range(len(id_sub)) if keep_c[j]]
            et_keep = [etime[j] for j in range(len(etime)) if keep_c[j]]
            y_keep = [yinc[j] for j in range(len(yinc)) if keep_c[j]]
            baseid_int = _match_vec(baseid, baseid)
            id_new_int = _match_vec(id_keep, baseid)
            nv = _ctmerge(
                baseid_int,
                np.asarray(dstart, dtype=float),
                nv,
                id_new_int,
                np.asarray(et_keep, dtype=float),
                np.asarray(y_keep, dtype=float),
            )
            newvar = nv.tolist()

        newdata[aname] = newvar

    tm_retain_out = {
        "tname": {k: topt[k] for k in ("idname", "tstartname", "tstopname")},
        "n": _nrow(newdata),
    }
    if tevent:
        tm_retain_out["tevent"] = {"name": tevent, "censor": [tcens[e] for e in tevent]}
    if tdcvar:
        tm_retain_out["tdcvar"] = list(dict.fromkeys(tdcvar))

    if frame1.tcount is not None:
        full_tcount = np.vstack([frame1.tcount, tcount])
        full_rows = (frame1.tcount_rownames or []) + argname
    else:
        full_tcount = tcount
        full_rows = argname

    return _table_to_frame(newdata, tm_retain=tm_retain_out, tcount=full_tcount, tcount_rownames=full_rows)
