//! The model search of `src/nlsd.c`: `nlsd` (adding and deleting dimensions),
//! `adddim` with its knot finders, and `betaadd`.

use super::base::{definespace, luinverse, mat, swapspace, DataS, Mat, Space, MAXKNOTS};
use super::iterate::{iter, rao};
use super::remove::remdim;
use super::setup::{setupspace, startspace};
use super::Glob;
use crate::lsdall::rprintf;

/// `nlsd`: search for the best model. `best` receives the best model found,
/// `logs[i]` and `ad[i]` record the fit at dimension i+1.
#[allow(clippy::too_many_arguments)]
pub fn nlsd(
    g: &mut Glob,
    best: &mut Space,
    data: &mut DataS,
    alpha: f64,
    ndmax_in: i32,
    mind: i32,
    strt: i32,
    silent: i32,
    logs: &mut [f64],
    ad: &mut [i32],
) -> i32 {
    let mut trynew = definespace(data.ndata);
    let mut current = definespace(data.ndata);

    // starting
    swapspace(&mut current, best);
    let i = startspace(&mut current, data, strt, silent);
    if i == 0 {
        return 39;
    }

    // initialization
    let mut ndmax = ndmax_in;
    let ndm2 = ndmax;
    if ndmax < 0 {
        ndmax = -ndmax;
    }
    best.aic = 10f64.powf(150.0);
    for i in 0..MAXKNOTS {
        logs[i] = -(10f64.powf(150.0));
    }

    let mut add: i32 = 1;
    let mut oops: i32 = 0;
    let mut oops2: i32 = 0;
    let mut oops3: i32 = 0;
    let mut coco: i32 = 0;
    let mut xxa: f64 = 0.0;

    // we start in adding mode
    loop {
        // fits the model
        if oops3 == 0 {
            oops = iter(g, &mut current, data, silent, &mut xxa);
        }
        if (oops > 0 || oops3 > 0) && ndmax > current.ndim {
            // problems: restart from other starting values
            loop {
                let mut i: i32 = -1;
                while i > -4 {
                    xxa = 0.0;
                    coco += 1;
                    let j = startspace(&mut current, data, i, silent);
                    if j == 0 {
                        return 39;
                    }
                    if coco == 10 {
                        return 39;
                    }
                    oops = iter(g, &mut current, data, silent, &mut xxa);
                    oops2 += 1;
                    if oops == 0 {
                        i = -10;
                    }
                    i -= 1;
                }
                if !(oops != 0 && ndmax > current.ndim) {
                    break;
                }
            }
        }
        if oops2 > 2 {
            oops2 -= 1;
        }
        if oops != 0 {
            if best.aic < -1.0e149 {
                return 40;
            } else {
                swapspace(&mut current, best);
            }
            add = 0;
        }

        if oops == 0 {
            // compute aic
            let nd = current.ndim as usize;
            logs[nd - 1] = current.aic;
            ad[nd - 1] = 1;
            current.aic = (current.ndim as f64) * alpha - 2.0 * current.aic;
            if current.ndim == ndmax {
                add = 0;
            }
            // did we improve
            if current.aic < best.aic {
                swapspace(best, &current);
            }
        }

        // continue
        if add == 1 && ndm2 < 0 {
            // was there any recent improvement?
            let nd = current.ndim;
            let mut i: i32 = 2;
            while i < nd - 2 {
                if logs[(nd - 1) as usize] - logs[(i - 1) as usize]
                    < ((nd - i) as f64) / 2.0 - 0.5
                {
                    add = 0;
                    ndmax = current.ndim;
                }
                i += 1;
            }
        }
        // adds dimensions, computes new starting values
        if add == 1 {
            add = adddim(g, &mut current, &mut trynew, data, mind, silent);
            if add != 1 && oops2 < 2 {
                ndmax = current.ndim;
            }
            if add != 1 && oops2 >= 2 {
                oops3 = 1;
                add = 1;
            }
        }
        // keep on adding?
        if add != 1 {
            break;
        }
    }

    // start deleting
    if current.ndim > 2 {
        loop {
            // removes dimensions, computes new starting values
            if ndmax > 2 {
                remdim(&mut current, data, &mut trynew, silent);
            }
            // fits the model
            oops = iter(g, &mut current, data, silent, &mut xxa);
            if oops != 0 {
                oops += 100;
                best.ndim = ndmax - 1;
                return oops;
            }
            // compute aic
            let nd = current.ndim as usize;
            if current.aic > logs[nd - 1] {
                logs[nd - 1] = current.aic;
                ad[nd - 1] = 2;
            }
            current.aic = (current.ndim as f64) * alpha - 2.0 * current.aic;
            // did we improve
            if current.aic < best.aic {
                swapspace(best, &current);
            }
            // does further deleting make sense
            if !(current.aic - best.aic < alpha * ((current.ndim - 2) as f64)) {
                break;
            }
        }
    }

    best.ndim = ndmax - 1;
    if oops2 > 0 {
        return 100;
    }
    0
}

/// `adddim`: add one knot where the score (`rao`) is largest. Returns 1 on
/// success, otherwise the failure code from the knot search.
pub fn adddim(
    g: &mut Glob,
    spc: &mut Space,
    spc2: &mut Space,
    data: &mut DataS,
    mind: i32,
    silent: i32,
) -> i32 {
    let nx = data.ndata;
    let mut sorted = vec![0.0f64; data.ndata as usize + 1];
    let mut uu: i32 = 0;
    let mut ll: i32 = 0;
    let mut bestloc: i32 = -1;
    let mut besti: i32 = -1;
    let mut bestrao: f64 = -1.0;
    let mut loloc: i32 = 0;
    let mut uploc: i32 = 0;
    swapspace(spc2, spc);
    for i in 0..data.ndata as usize {
        sorted[i] = data.data[i];
    }
    // find the interval
    for i in 0..=spc.nk {
        let mut nowloc1: i32 = 0;
        // before first knot
        if i == 0 {
            nowloc1 = findl(&mut ll, &mut uu, mind, &sorted, nx, spc.knots[0]);
        }
        // after last knot
        if i == spc.nk {
            nowloc1 = findr(&mut ll, &mut uu, mind, &sorted, nx, spc.knots[(spc.nk - 1) as usize]);
        }
        // in between knots
        if i > 0 && i < spc.nk {
            nowloc1 = findm(
                &mut ll,
                &mut uu,
                mind,
                &sorted,
                nx,
                spc.knots[(i - 1) as usize],
                spc.knots[i as usize],
            );
        }
        // possible location
        if nowloc1 >= 0 {
            let nowrao1 = rao(g, spc, data, sorted[nowloc1 as usize]);
            if nowrao1 > bestrao {
                loloc = ll;
                uploc = uu;
                bestloc = nowloc1;
                bestrao = nowrao1;
                besti = i;
            }
        }
    }
    if bestloc < 0 {
        return -1;
    }
    // as long as the locations are different, do interval halving
    loop {
        if sorted[uploc as usize] > sorted[loloc as usize] {
            let nowloc2 = findyr(uploc, bestloc, &sorted);
            // two search points, the upper one
            let nowrao2 = if nowloc2 >= 0 {
                rao(g, spc, data, sorted[nowloc2 as usize])
            } else {
                bestrao
            };
            // two search points, the lower one
            let nowloc1 = findyl(bestloc, loloc, &sorted);
            let nowrao1 = if nowloc1 >= 0 {
                rao(g, spc, data, sorted[nowloc1 as usize])
            } else {
                bestrao
            };
            // the middle one is the best, we call it quits
            if bestrao >= nowrao2 && bestrao >= nowrao1 {
                loloc = uploc;
            } else if nowrao1 > bestrao {
                // the lower search point is the best
                uploc = bestloc;
                bestloc = nowloc1;
                bestrao = nowrao1;
            } else {
                // the upper search point is the best
                loloc = bestloc;
                bestloc = nowloc2;
                bestrao = nowrao2;
            }
        }
        if !(sorted[uploc as usize] > sorted[loloc as usize]) {
            break;
        }
    }
    // failure
    if bestloc < 0 {
        return bestloc;
    }
    // done: record the new knot in its correct position
    if besti == spc.nk {
        spc.knots[spc.nk as usize] = sorted[bestloc as usize];
        spc.iknots[spc.nk as usize] = bestloc;
    } else {
        let mut i = spc.nk;
        while i > besti {
            spc.knots[i as usize] = spc.knots[(i - 1) as usize];
            spc.iknots[i as usize] = spc.iknots[(i - 1) as usize];
            i -= 1;
        }
        spc.knots[besti as usize] = sorted[bestloc as usize];
        spc.iknots[besti as usize] = bestloc;
    }
    spc.nk += 1;
    spc.ndim += 1;
    if silent == 1 {
        rprintf(&format!(
            "add({:.2}), rao={:.2} ",
            sorted[bestloc as usize],
            bestrao
        ));
    }
    setupspace(spc, data);
    betaadd(spc, spc2, besti);
    1
}

/// `findyl`: a location in the interval (l, u); `l` might not have been tested.
fn findyl(u: i32, l: i32, x: &[f64]) -> i32 {
    if x[l as usize] == x[u as usize] {
        return -1;
    }
    let mut i = (u + l - 1) / 2;
    if x[i as usize] != x[u as usize] {
        return i;
    }
    i = (i + l) / 2;
    if x[i as usize] != x[u as usize] {
        return i;
    }
    l
}

/// `findyr`: a location in the interval (l, u); `u` might not have been tested.
fn findyr(u: i32, l: i32, x: &[f64]) -> i32 {
    if x[l as usize] == x[u as usize] {
        return -1;
    }
    let mut i = (u + l + 1) / 2;
    if x[i as usize] != x[l as usize] {
        return i;
    }
    i = (i + u) / 2;
    if x[i as usize] != x[l as usize] {
        return i;
    }
    u
}

/// `findl`: a candidate knot on (0, knot1). `ll` and `uu` give the range still
/// to search.
fn findl(ll: &mut i32, uu: &mut i32, mind: i32, x: &[f64], nx: i32, knt: f64) -> i32 {
    *uu = dlocation(0, x, nx, knt);
    if *uu < mind {
        return -1;
    }
    let mut i = (*uu - 1) / 2;
    if *uu - i < mind + 1 {
        i = *uu - mind - 1;
    }
    *ll = 0;
    *uu -= mind + 1;
    i
}

/// `findr`: a candidate knot on (knot-last, nx-1).
fn findr(ll: &mut i32, uu: &mut i32, mind: i32, x: &[f64], nx: i32, knt: f64) -> i32 {
    *ll = dlocation(1, x, nx, knt);
    if nx - 1 - *ll < mind {
        return -1;
    }
    let mut i = (nx + *ll) / 2;
    if i - *ll < mind + 1 {
        i = *ll + mind + 1;
    }
    *uu = nx - 1;
    *ll += mind + 1;
    i
}

/// `findm`: a candidate knot on the interval (k0, k1).
fn findm(ll: &mut i32, uu: &mut i32, mind: i32, x: &[f64], nx: i32, k0: f64, k1: f64) -> i32 {
    *ll = dlocation(1, x, nx, k0);
    *uu = dlocation(0, x, nx, k1);
    if *uu - *ll < 2 * mind + 1 {
        return -1;
    }
    *uu -= mind + 1;
    *ll += mind + 1;
    (*uu + *ll) / 2
}

/// `dlocation`: the lowest index (`what == 0`) or the highest index (`what == 1`)
/// of `x` at which `x` compares with `k`.
fn dlocation(what: i32, x: &[f64], nx: i32, k: f64) -> i32 {
    let nxu = nx as usize;
    if what == 1 {
        if x[0] > k {
            return 0;
        }
        if x[nxu - 1] <= k {
            return nx - 1;
        }
        for i in 0..nxu - 1 {
            if x[i + 1] > k && x[i] <= k {
                return i as i32;
            }
        }
    }
    if x[nxu - 1] < k {
        return nx - 1;
    }
    if x[0] >= k {
        return 0;
    }
    for i in 1..nxu {
        if x[i] >= k && x[i - 1] < k {
            return i as i32;
        }
    }
    nx
}

/// `betaadd`: new starting values for the coefficients after a knot is added,
/// by solving one coefficient matrix with respect to the other.
pub fn betaadd(spc: &mut Space, spc2: &Space, besti: i32) {
    let k = (spc.ndim + 3) as usize;
    let mut t1: Mat = mat(k + 1, k + 1);
    let mut v1 = vec![0.0f64; MAXKNOTS + 6];
    for i in 0..(spc2.nk + 2) as usize {
        v1[i] = 0.0;
        for j in 0..spc2.ndim as usize {
            v1[i] += spc2.basis[j].beta * spc2.basis[j].c1[i];
        }
    }
    let mut i = spc2.nk;
    while i > besti {
        v1[(i + 2) as usize] = v1[(i + 1) as usize];
        i -= 1;
    }
    v1[(besti + 2) as usize] = 0.0;
    for i in 0..k {
        for j in 0..k {
            t1[i][j] = 0.0;
        }
    }
    for j in 0..k {
        for i in 0..k - 3 {
            t1[i][j] = spc.basis[i].c1[j];
        }
    }
    for i in k - 2..k {
        t1[i][i] = 1.0;
    }
    t1[k - 3][0] = 1.0;
    // luinverse works on the k x k block, 0-based
    let mut tk: Mat = (0..k).map(|r| t1[r][..k].to_vec()).collect();
    luinverse(&mut tk, k);
    for i in 0..k - 3 {
        spc.basis[i].beta = 0.0;
        for j in 0..k {
            spc.basis[i].beta += tk[j][i] * v1[j];
        }
    }
}
