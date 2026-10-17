//! The Newton iteration of `src/nlsd.c` (`iter`, `iterx`), the likelihood,
//! score and information (`pompall`), and the Rao statistic used to pick
//! new knots (`rao`, `praox`, `getnewc2`, `save22coden`).

use super::base::{lusolve2, mat, myexp, mylog, Basis, DataS, Mat, Space, MAXKNOTS};
use super::quad::{inp3, l1int, l2int, m1int, mat3, pol3};
use super::setup::startnow;
use super::Glob;
use crate::lsdall::rprintf;

/// `iter`: fit one model, trying unbounded tails first when the space has them.
pub fn iter(g: &mut Glob, spc: &mut Space, data: &mut DataS, silent: i32, xxa: &mut f64) -> i32 {
    let xpp = spc.upp;
    let mut lpp = spc.upp;
    let mut lll = spc.low;
    let xll = spc.low;
    let mut n: i32 = 0;
    let mll = spc.ilow;
    let muu = spc.iupp;
    // bounded intervals
    if spc.ilow == 0 && spc.iupp == 0 {
        return iterx(g, spc, data, silent, xxa);
    }
    loop {
        // try unbounded intervals
        n += 1;
        if (spc.basis[1].beta < 0.0 || muu == 0) && (spc.basis[0].beta < 0.0 || mll == 0) {
            spc.low = xll;
            spc.ilow = mll;
            spc.upp = xpp;
            spc.iupp = muu;
            let oops = iterx(g, spc, data, silent, xxa);
            if oops == 0 || n == 6 {
                return oops;
            }
        }
        spc.iupp = 0;
        spc.ilow = 0;
        // widen bounded intervals
        if muu == 1 {
            spc.upp = 4.0 * lpp - 3.0 * spc.low;
        }
        if mll == 1 {
            spc.low = 4.0 * lll - 3.0 * spc.upp;
        }
        lpp = spc.upp;
        lll = spc.low;
        let oops = iterx(g, spc, data, silent, xxa);
        spc.iupp = muu;
        spc.upp = xpp;
        spc.ilow = mll;
        spc.low = xll;
        if oops != 0 {
            return oops;
        }
        if !(n < 6) {
            break;
        }
    }
    9999
}

/// `iterx`: Newton iterations with step halving for one model. Returns 1 for
/// no convergence, 0 on success, and other codes for the failure modes.
pub fn iterx(g: &mut Glob, spc: &mut Space, data: &mut DataS, silent: i32, xxa: &mut f64) -> i32 {
    let zerror = 0.000001f64;
    let maxiter: i32 = 100;
    let ndim = spc.ndim as usize;
    let mut iter: i32 = 0;
    let mut i1: i32 = 0;
    let mut i2: i32 = 0;
    let mut i: i32 = 0;
    let mut tmp1 = vec![0.0f64; MAXKNOTS + 6];
    let mut tmp2 = vec![0.0f64; MAXKNOTS + 6];
    let mut tmp3: Mat = mat(MAXKNOTS + 6, MAXKNOTS + 6);
    let mut logl: f64;
    let mut lnew: f64 = 0.0;
    let mut factor: f64;
    let mut kk: i32;
    while iter < maxiter {
        // compute logl/score/hessian
        logl = pompall(g, spc, data, 2, &mut i1);
        if iter == 0 && (*xxa).abs() > 0.01 && (*xxa) - logl > 100.0 {
            // try alternate starting values
            lnew = logl;
            for j in 0..ndim {
                tmp1[j] = spc.score[j];
                tmp2[j] = spc.basis[j].beta;
                spc.basis[j].beta = 0.0;
                for i in 0..ndim {
                    tmp3[i][j] = spc.info[i][j];
                }
            }
            startnow(spc, data);
            logl = pompall(g, spc, data, 2, &mut i2);
            if lnew > logl {
                logl = lnew;
                for j in 0..ndim {
                    spc.score[j] = tmp1[j];
                    spc.basis[j].beta = tmp2[j];
                    for i in 0..ndim {
                        spc.info[i][j] = tmp3[i][j];
                    }
                }
            } else {
                i1 = i2;
            }
        }
        // serious ctheta problems
        if i1 == 1 {
            return 7;
        }
        // solve the system
        let j = lusolve2(&spc.info, ndim, &mut spc.score);
        // return 2 - something wrong with system
        if j == 0 {
            return 2;
        }
        // adjust the tail shifts
        if spc.ilow == 1 {
            spc.score[0] = -spc.score[0] / spc.basis[0].beta;
            if spc.score[0] < -100.0 {
                spc.score[0] = -100.0;
            }
        }
        if spc.iupp == 1 {
            spc.score[1] = -spc.score[1] / spc.basis[1].beta;
            if spc.score[1] < -100.0 {
                spc.score[1] = -100.0;
            }
        }
        // find the right step size
        factor = -1.0;
        // tail check
        if spc.ilow == 1 && spc.iupp == 1 && spc.basis[0].beta == 0.0 && spc.basis[1].beta == 0.0 {
            return 6;
        }
        if spc.ilow == 1 && spc.basis[0].beta >= 0.0 {
            return 4;
        }
        if spc.iupp == 1 && spc.basis[1].beta >= 0.0 {
            return 3;
        }
        // adjust beta
        if spc.ilow == 0 {
            spc.basis[0].beta -= factor * spc.score[0];
        } else {
            spc.basis[0].beta = -myexp(factor * spc.score[0] + mylog(-spc.basis[0].beta));
        }
        if spc.iupp == 0 {
            spc.basis[1].beta -= factor * spc.score[1];
        } else {
            spc.basis[1].beta = -myexp(factor * spc.score[1] + mylog(-spc.basis[1].beta));
        }
        for j in 2..ndim {
            spc.basis[j].beta -= factor * spc.score[j];
        }
        loop {
            // new logl
            if spc.ilow == 1 && spc.iupp == 1 && spc.basis[0].beta == 0.0 && spc.basis[1].beta == 0.0 {
                return 6;
            }
            if spc.ilow == 1 && spc.basis[0].beta >= 0.0 {
                return 4;
            }
            if spc.iupp == 1 && spc.basis[1].beta >= 0.0 {
                return 3;
            }
            lnew = pompall(g, spc, data, 0, &mut i);
            // did we win?
            kk = 0;
            if (lnew - logl) < -zerror {
                kk = 1;
            }
            if (lnew - logl) < -zerror * 100.0 && spc.ilow == 1 && spc.basis[0].beta > -1.0e8 {
                kk = 1;
            }
            if (lnew - logl) < -zerror * 100.0 && spc.iupp == 1 && spc.basis[1].beta > -1.0e8 {
                kk = 1;
            }
            if kk == 1 || (i == 1 && factor.abs() > 0.1) {
                // adjust the stepsize
                i = 0;
                factor /= 2.0;
                if spc.ilow == 0 {
                    spc.basis[0].beta += factor * spc.score[0];
                } else {
                    spc.basis[0].beta = -myexp(-factor * spc.score[0] + mylog(-spc.basis[0].beta));
                }
                if spc.iupp == 0 {
                    spc.basis[1].beta += factor * spc.score[1];
                } else {
                    spc.basis[1].beta = -myexp(-factor * spc.score[1] + mylog(-spc.basis[1].beta));
                }
                for j in 2..ndim {
                    spc.basis[j].beta += factor * spc.score[j];
                }
                if factor.abs() < 0.00001
                    && ((spc.iupp == 1 && spc.basis[1].beta > -1.0e8)
                        || (spc.ilow == 1 && spc.basis[0].beta > -1.0e8))
                {
                    return 5;
                }
                if factor.abs() < 0.00001 {
                    return 8;
                }
                // return 5/8 - too much step-halving
            }
            if i == 1 {
                return 7;
            }
            if kk != 1 {
                break;
            }
        }
        // convergence
        if (lnew - logl).abs() < zerror && factor.abs() > 0.96 {
            iter = maxiter + 1000;
        }
        if (lnew - logl).abs() < zerror * 100.0 && spc.ilow == 1 && spc.basis[0].beta > -1.0e8 {
            iter = maxiter + 1000;
        }
        if (lnew - logl).abs() < zerror * 100.0 && spc.iupp == 1 && spc.basis[1].beta > -1.0e8 {
            iter = maxiter + 1000;
        }
        iter += 1;
    }
    if iter < maxiter + 500 {
        // return 1 - no convergence
        return 1;
    }
    let logl = pompall(g, spc, data, 1, &mut i);
    *xxa = logl;
    spc.aic = logl;
    if silent == 1 {
        rprintf(&format!("|| logl= {:.2} (nd={})\n", logl, ndim));
    }
    spc.cth = g.ctheta;
    0
}

/// `pompall`: the log-likelihood (`what == 0`), plus the score and information
/// (`what >= 1`) for the model `spc`. Sets `g.ctheta` and writes the results to
/// `spc.score` and `spc.info`. `xp` is 1 if the normalizing constant failed.
pub fn pompall(g: &mut Glob, spc: &mut Space, data: &mut DataS, what: i32, xp: &mut i32) -> f64 {
    let nip = spc.nip as usize;
    let ndim = spc.ndim as usize;
    let mut f = 0.0f64;
    let mut coef = mat(nip + 3, 5);
    // numerical integration
    for i in 0..nip - 1 {
        for j in 0..4 {
            coef[i][j] = 0.0;
            for k in 0..ndim {
                coef[i][j] += spc.basis[k].beta * spc.basis[k].c2[i][j];
            }
        }
    }
    let ips = spc.ips.clone();
    if spc.ilow == 1 {
        l1int(&mut g.kints[0], ips[1], &coef[0], 1, what);
    } else {
        l2int(&mut g.kints[0], spc.low, ips[1], &coef[0], what);
    }
    for i in 1..nip - 2 {
        m1int(&mut g.kints[i], ips[i], ips[i + 1], what, &coef[i], 0);
    }
    if spc.iupp == 1 {
        l1int(&mut g.kints[nip - 2], ips[nip - 2], &coef[nip - 2], -1, what);
    } else {
        l2int(&mut g.kints[nip - 2], ips[nip - 2], spc.upp, &coef[nip - 2], what);
    }
    // ctheta
    g.ctheta = 0.0;
    for i in 0..nip - 1 {
        g.ctheta += g.kints[i][0];
    }
    if g.ctheta > 0.0 {
        *xp = 0;
    } else {
        *xp = 1;
        return 0.0;
    }
    g.ctheta = mylog(g.ctheta);
    // logl - uncensored
    let mut logl = 0.0f64;
    for i in 0..data.ndata as usize {
        if data.same[i] == 0 {
            f = pol3(&coef[data.idata[i] as usize], data.data[i]) - g.ctheta;
        }
        logl += f;
    }
    g.ctheta = myexp(-g.ctheta);
    if what == 0 {
        return logl;
    }
    // get ctheta-j and ctheta-jk
    let mut cz = vec![0.0f64; MAXKNOTS + 6];
    let mut czz = mat(MAXKNOTS + 6, MAXKNOTS + 6);
    for i in 0..nip - 1 {
        savecode1(spc, i, &mut cz, &mut czz, &g.kints[i]);
    }
    // score and hessian - basic
    let nd = data.ndata as f64;
    for i in 0..ndim {
        for j in 0..ndim {
            czz[i][j] = nd * czz[i][j] * g.ctheta;
        }
        cz[i] = -nd * cz[i] * g.ctheta;
    }
    for i in 0..ndim {
        for j in 0..ndim {
            czz[i][j] -= cz[i] * cz[j] / nd;
        }
    }
    if what == 1 {
        for i in 0..ndim {
            g.cuu[i] = cz[i];
        }
    }
    // uncensored - score
    for i in 0..ndim {
        cz[i] += spc.basis[i].sumunc;
    }
    // symmetrize
    for i in 0..ndim {
        for j in i + 1..ndim {
            czz[i][j] = czz[j][i];
        }
    }
    for i in 0..ndim {
        spc.score[i] = cz[i];
        for j in 0..ndim {
            spc.info[i][j] = czz[i][j];
        }
    }
    logl
}

/// `savecode1`: add the contribution of interval `j` to the score `cz` and the
/// information `czz` (`what` holds the integrals over that interval).
fn savecode1(spc: &Space, j: usize, cz: &mut [f64], czz: &mut Mat, what: &[f64]) {
    let ndim = spc.ndim as usize;
    for k in 0..ndim {
        let bk = &spc.basis[k];
        if j as i32 >= bk.c3[0] && j as i32 <= bk.c3[1] {
            cz[k] += inp3(what, &bk.c2[j]);
            for j2 in 0..=k {
                let bj2 = &spc.basis[j2];
                if j as i32 >= bj2.c3[0] && j as i32 <= bj2.c3[1] {
                    czz[k][j2] += mat3(what, &bk.c2[j], &bj2.c2[j]);
                }
            }
        }
    }
}

/// `getnewc2`: the basis function for a test knot at `loc`. Fills `bb.c3`,
/// `bb.c2`, `bb.sumunc`, and returns `j0ext`, the interval containing `loc`.
pub fn getnewc2(
    spc: &Space,
    data: &mut DataS,
    loc: f64,
    bb: &mut Basis,
    intext: &mut [f64; 7],
    c2ext: &mut [f64; 4],
) -> i32 {
    let nip = spc.nip as usize;
    let nk = spc.nk as usize;
    let ndim = spc.ndim as usize;
    let mut coef = [0.0f64; 10];
    let mut rrr = [0.0f64; 10];
    let mut t = [0.0f64; 3];
    let mut ii = [0i32; 3];
    let mut cc = [0.0f64; 3];
    // get basis.c3
    t[1] = spc.knots[nk - 2];
    t[2] = spc.knots[nk - 1];
    t[0] = loc;
    for j in 0..3 {
        ii[j] = (nip - 1) as i32;
        for i in 1..nip {
            if spc.ips[i] >= t[j] {
                ii[j] = i as i32;
                break;
            }
        }
    }
    bb.c3[0] = ii[0] - 1;
    if ii[1] < ii[0] - 1 {
        bb.c3[0] = ii[1];
    }
    bb.c3[1] = nip as i32 + 1;
    if bb.c3[0] < 0 {
        bb.c3[0] = 0;
    }
    cc[0] = 1.0;
    cc[1] = (t[0] - t[2]) / (t[2] - t[1]);
    cc[2] = (t[1] - t[0]) / (t[2] - t[1]);
    // get basis.c2
    for j in 0..nip {
        for j0 in 0..4 {
            bb.c2[j][j0] = 0.0;
        }
    }
    for j in bb.c3[0]..=bb.c3[1] {
        let ju = j as usize;
        for j1 in 0..3 {
            if j >= ii[j1] {
                bb.c2[ju][3] += cc[j1];
                bb.c2[ju][2] -= 3.0 * cc[j1] * t[j1];
                bb.c2[ju][1] += 3.0 * cc[j1] * t[j1] * t[j1];
                bb.c2[ju][0] -= cc[j1] * t[j1] * t[j1] * t[j1];
            }
        }
    }
    // get j0ext
    let mut j0ext: i32 = nip as i32 + 100;
    if t[0] < spc.ips[1] {
        j0ext = 0;
    } else {
        let mut i = 1usize;
        while i < nip - 2 {
            if t[0] == spc.ips[i] {
                j0ext = -1;
            } else if t[0] < spc.ips[i + 1] {
                j0ext = i as i32;
            }
            if j0ext < nip as i32 + 50 {
                break;
            }
            i += 1;
        }
    }
    if j0ext > nip as i32 + 50 {
        j0ext = nip as i32 - 2;
    }
    // get c2ext
    for i in 0..4 {
        c2ext[i] = 0.0;
    }
    for j1 in 0..3 {
        if t[j1] <= t[0] {
            c2ext[3] += cc[j1];
            c2ext[2] -= 3.0 * cc[j1] * t[j1];
            c2ext[1] += 3.0 * cc[j1] * t[j1] * t[j1];
            c2ext[0] -= cc[j1] * t[j1] * t[j1] * t[j1];
        }
    }
    // get intext
    if j0ext >= 0 {
        let je = j0ext as usize;
        for j in 0..4 {
            coef[j] = 0.0;
            for k in 0..ndim {
                coef[j] += spc.basis[k].beta * spc.basis[k].c2[je][j];
            }
        }
        if j0ext == 0 {
            if spc.ilow == 1 {
                l1int(&mut rrr, t[0], &coef, 1, 1);
            } else {
                l2int(&mut rrr, spc.low, t[0], &coef, 1);
            }
        }
        if j0ext == nip as i32 - 2 {
            l2int(&mut rrr, spc.ips[je], t[0], &coef, 1);
        }
        if j0ext > 0 && j0ext < nip as i32 - 2 {
            m1int(&mut rrr, spc.ips[je], t[0], 1, &coef, 0);
        }
        for i in 0..7 {
            intext[i] = rrr[i];
        }
    }
    // get basis.sumunc
    bb.sumunc = 0.0;
    for j1 in 0..data.ndata as usize {
        let j0 = data.idata[j1];
        if j0 >= bb.c3[0] && j0 <= bb.c3[1] {
            let ju = j0 as usize;
            if j0 != j0ext || t[0] > data.data[j1] {
                bb.sumunc += pol3(&bb.c2[ju], data.data[j1]);
            } else {
                bb.sumunc += pol3(c2ext, data.data[j1]);
            }
        }
    }
    j0ext
}

/// `praox`: the new parts of the score and the information for a test basis
/// function. `iext` receives the new information column.
#[allow(clippy::too_many_arguments)]
fn praox(
    g: &mut Glob,
    spc: &Space,
    data: &mut DataS,
    bb: &Basis,
    iext: &mut [f64],
    intext: &[f64; 7],
    c2ext: &[f64; 4],
    j0ext: i32,
) -> f64 {
    let ndim = spc.ndim as usize;
    let nd = data.ndata as f64;
    let mut int2ext = [0.0f64; 7];
    if j0ext >= 0 {
        for i in 0..7 {
            int2ext[i] = g.kints[j0ext as usize][i] - intext[i];
        }
    }
    // get ctheta-j and ctheta-jk
    for j in 0..=ndim {
        iext[j] = 0.0;
    }
    let mut sext = save22coden(g, spc, iext, bb, &int2ext, j0ext, c2ext);
    for j in 0..=ndim {
        iext[j] = nd * iext[j] * g.ctheta;
    }
    sext = -nd * sext * g.ctheta;
    for j in 0..ndim {
        iext[j] -= sext * g.cuu[j] / nd;
    }
    iext[ndim] -= sext * sext / nd;
    sext += bb.sumunc;
    sext
}

/// `save22coden`: the integrals over all intervals for a test basis function.
fn save22coden(
    g: &mut Glob,
    spc: &Space,
    czz: &mut [f64],
    bb: &Basis,
    int2ext: &[f64; 7],
    j0ext: i32,
    c2ext: &[f64; 4],
) -> f64 {
    let ndim = spc.ndim as usize;
    let i1 = spc.nip as usize - 1;
    let mut cz = 0.0f64;
    // correct the new one
    if j0ext >= 0 && (j0ext as usize) < i1 {
        for k in 0..7 {
            g.kints[j0ext as usize][k] -= int2ext[k];
        }
    }
    // regular stuff
    for j in 0..i1 {
        let jj = j as i32;
        if jj >= bb.c3[0] && jj <= bb.c3[1] {
            for k in 0..ndim {
                let bk = &spc.basis[k];
                if jj >= bk.c3[0] && jj <= bk.c3[1] {
                    czz[k] += mat3(&g.kints[j], &bk.c2[j], &bb.c2[j]);
                }
            }
            cz += inp3(&g.kints[j], &bb.c2[j]);
            czz[ndim] += mat3(&g.kints[j], &bb.c2[j], &bb.c2[j]);
        }
    }
    // correct the new one part II
    if j0ext >= 0 && (j0ext as usize) < i1 {
        let je = j0ext as usize;
        for k in 0..ndim {
            let bk = &spc.basis[k];
            if j0ext >= bk.c3[0] && j0ext <= bk.c3[1] && j0ext >= bb.c3[0] && j0ext <= bb.c3[1] {
                czz[k] += mat3(int2ext, &bk.c2[je], c2ext);
            }
        }
        cz += inp3(int2ext, c2ext);
        czz[ndim] += mat3(int2ext, c2ext, c2ext);
        for k in 0..7 {
            g.kints[je][k] += int2ext[k];
        }
    }
    cz
}

/// `rao`: the Rao score statistic for a candidate knot at `loc`.
pub fn rao(g: &mut Glob, spc: &Space, data: &mut DataS, loc: f64) -> f64 {
    let ndim = spc.ndim as usize;
    let nip = spc.nip as usize;
    let mut ii: Mat = mat(MAXKNOTS + 6, MAXKNOTS + 6);
    let mut ss = vec![0.0f64; MAXKNOTS + 6];
    for i in 0..ndim {
        for j in 0..ndim {
            ii[i][j] = spc.info[i][j];
        }
        ss[i] = 0.0;
    }
    let mut bb = Basis {
        beta: 0.0,
        c1: vec![0.0; MAXKNOTS + 6],
        c2: mat(nip + 11, 5),
        sumunc: 0.0,
        c3: [0, 0],
        iks: [0; 5],
    };
    let mut intext = [0.0f64; 7];
    let mut c2ext = [0.0f64; 4];
    let j0ext = getnewc2(spc, data, loc, &mut bb, &mut intext, &mut c2ext);
    let mut row = ii[ndim].clone();
    ss[ndim] = praox(g, spc, data, &bb, &mut row, &intext, &c2ext, j0ext);
    ii[ndim] = row;
    for i in 0..ndim {
        ii[i][ndim] = ii[ndim][i];
    }
    let mut r = ss[ndim];
    // the C code tests `i < 0`, which lusolve2 never returns
    let _ = lusolve2(&ii, ndim + 1, &mut ss);
    ss[ndim] * r
}
