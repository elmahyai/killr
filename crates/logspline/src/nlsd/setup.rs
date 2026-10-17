//! Setting up a model in `src/nlsd.c`: the integration points (`getip`), the
//! basis coefficients (`getc1`, `getc2`), the starting knots and values
//! (`startspace`, `startnow`, `rearrange`).

use super::base::{DataS, Space};
use super::quad::pol3;
use crate::lsdall::rprintf;

/// `getonec1`: the basis function that starts at knot `i`, from knots `j..j+3`.
fn getonec1(c: &mut [f64], i: usize, t: &[f64], j: usize) {
    c[i] = 1.0;
    c[i + 3] = (t[j + 2] - t[j]) * (t[j] - t[j + 1]) / ((t[j + 2] - t[j + 3]) * (t[j + 1] - t[j + 3]));
    c[i + 2] = (c[i + 3] * (t[j + 1] - t[j + 3]) + t[j + 1] - t[j]) / (t[j + 2] - t[j + 1]);
    c[i + 1] = -1.0 - c[i + 3] - c[i + 2];
}

/// `getc1`: the coefficients of basis function `i` in the truncated power
/// basis, with `k` knots.
fn getc1(t: &[f64], c: &mut [f64], i: usize, k: usize) {
    let mut d = [0.0f64; 10];
    for j in 0..=k + 1 {
        c[j] = 0.0;
    }
    if i == 0 {
        let a = t[2] - t[0];
        let b = t[2] - t[1];
        c[2] = 1.0;
        c[3] = -a / b;
        c[4] = -c[2] - c[3];
        c[1] = -3.0 * (t[0] * t[0] + c[3] * t[1] * t[1] + c[4] * t[2] * t[2]);
        c[0] = -t[2] * c[1] - c[2] * a * a * a - c[3] * b * b * b;
    }
    if i == 1 {
        c[k - 1] = 1.0;
        c[k] = (t[k - 3] - t[k - 1]) / (t[k - 1] - t[k - 2]);
        c[k + 1] = -c[k] - c[k - 1];
    }
    if i == 2 {
        getonec1(c, k - 2, t, k - 4);
    }
    if i > 2 {
        getonec1(c, i - 1, t, i - 3);
        getonec1(&mut d, 0, t, i - 2);
        let mut a = 0.0f64;
        let mut b = 0.0f64;
        for j in 0..4 {
            let mut r = t[k - 1] - t[i + j - 2];
            a += d[j] * r * r * r;
            r = t[k - 1] - t[i + j - 3];
            b += c[i + j - 1] * r * r * r;
        }
        for j in 0..4 {
            c[i + j] -= d[j] * b / a;
        }
    }
}

/// `getc2`: for each basis function, the cubic coefficients on each
/// integration interval (`c2`), the interval range (`c3`), and `sumunc`.
fn getc2(spc: &mut Space, data: &DataS) {
    let nip = spc.nip as usize;
    let nk = spc.nk as usize;
    let ndim = spc.ndim as usize;
    let mut m: usize = 0;
    for i in 0..ndim {
        let bn = &mut spc.basis[i];
        bn.c3[0] = bn.iks[0] - 1;
        bn.c3[1] = bn.iks[2] + 1;
        if i == 0 {
            bn.c3[0] = 0;
        }
        if i == 1 || i == 2 {
            bn.c3[1] = nip as i32;
        }
        if i > 2 {
            bn.c3[1] = bn.iks[4] + 1;
        }
        // get basis.c2
        for j in 0..nip {
            for k in 0..4 {
                bn.c2[j][k] = 0.0;
            }
        }
        for j in bn.c3[0]..=bn.c3[1] {
            let ju = j as usize;
            let mut l = 5usize;
            if i == 0 || i == 1 {
                l = 3;
            }
            if i == 2 {
                l = 4;
            }
            if i == 0 {
                bn.c2[ju][0] += bn.c1[0];
                bn.c2[ju][1] += bn.c1[1];
            }
            for n in 0..l {
                if i == 0 {
                    m = n;
                }
                if i == 1 {
                    m = nk - 3 + n;
                }
                if i == 2 {
                    m = nk - 4 + n;
                }
                if i > 2 {
                    m = i + n - 3;
                }
                let a = spc.knots[m];
                let mut b = bn.c1[2 + m];
                if j >= bn.iks[n] {
                    bn.c2[ju][3] += b;
                    b *= a;
                    bn.c2[ju][2] -= 3.0 * b;
                    b *= a;
                    bn.c2[ju][1] += 3.0 * b;
                    b *= a;
                    bn.c2[ju][0] -= b;
                }
            }
        }
        // get basis.sumunc
        bn.sumunc = 0.0;
        for mm in 0..data.ndata as usize {
            let l = data.idata[mm];
            if l >= bn.c3[0] && l <= bn.c3[1] {
                bn.sumunc += pol3(&bn.c2[l as usize], data.data[mm]);
            }
        }
    }
}

/// `getip`: the integration points, the interval of each observation (`idata`),
/// and the knot indices of each basis function (`iks`).
fn getip(spc: &mut Space, data: &mut DataS) {
    let nk = spc.nk as usize;
    let mut iips = vec![0i32; spc.ips.len()];
    // the first two points
    iips[0] = -4;
    iips[1] = spc.iknots[0];
    spc.ips[0] = spc.low;
    spc.ips[1] = spc.knots[0];
    let mut nip: usize = 1;
    // get the actual integration points
    for i in 1..nk {
        let diff = spc.iknots[i] - spc.iknots[i - 1];
        let jn = (diff / 100) + 1;
        // integration points in between knots
        for k in 1..jn {
            nip += 1;
            iips[nip] = spc.iknots[i - 1] + k * (spc.iknots[i] - spc.iknots[i - 1]) / jn;
            spc.ips[nip] = data.data[iips[nip] as usize];
        }
        // every knot is an integration point
        nip += 1;
        spc.ips[nip] = spc.knots[i];
        iips[nip] = spc.iknots[i];
    }
    // the last integration point
    nip += 1;
    spc.ips[nip] = spc.upp;
    iips[nip] = data.ndata + 4;
    // get nip
    nip += 1;
    spc.nip = nip as i32;
    // get idata
    for i in 0..nip - 1 {
        let mut j = iips[i];
        while j <= iips[i + 1] - 1 {
            if j >= 0 && j < data.ndata {
                data.idata[j as usize] = i as i32;
            }
            j += 1;
        }
    }
    // get basis.iks
    let kips = &mut iips;
    for i in 0..nk {
        let j = spc.iknots[i];
        kips[i] = data.idata[j as usize];
    }
    for i in 0..3 {
        spc.basis[0].iks[i] = kips[i];
    }
    for i in 0..3 {
        spc.basis[1].iks[i] = kips[(i + nk) - 3];
    }
    if spc.ndim > 2 {
        for i in 0..4 {
            spc.basis[2].iks[i] = kips[(i + nk) - 4];
        }
    }
    let ndim = spc.ndim as usize;
    for j in 3..ndim {
        for i in 0..5 {
            spc.basis[j].iks[i] = kips[j + i - 3];
        }
    }
}

/// `setupspace`: integration points and basis coefficients for a model.
pub fn setupspace(spc: &mut Space, data: &mut DataS) {
    getip(spc, data);
    let nk = spc.nk as usize;
    let ndim = spc.ndim as usize;
    for i in 0..ndim {
        getc1(&spc.knots, &mut spc.basis[i].c1, i, nk);
    }
    getc2(spc, data);
}

/// `startnow`: the starting values of the coefficients, from the data
/// beyond the two end knots.
pub fn startnow(spc: &mut Space, data: &DataS) {
    let nk = spc.nk as usize;
    for i in 0..spc.ndim as usize {
        spc.basis[i].beta = 0.0;
    }
    let r0 = (spc.knots[0] + spc.knots[1]) / 2.0;
    let r1 = (spc.knots[nk - 2] + spc.knots[nk - 1]) / 2.0;
    let mut j0: i32 = 0;
    let mut j1: i32 = 0;
    let mut s0 = 0.0f64;
    let mut s1 = 0.0f64;
    for i in 0..data.ndata as usize {
        if data.data[i] < r0 {
            s0 += r0 - data.data[i];
            j0 += 2;
        }
        if data.data[i] > r1 {
            s1 += data.data[i] - r1;
            j1 += 2;
        }
    }
    s0 = 2.0 * s0 / (j0 as f64);
    s1 = 2.0 * s1 / (j1 as f64);
    if spc.ilow == 1 {
        spc.basis[0].beta = -1.0 / (s0 * spc.basis[0].c1[1]).abs();
    }
    if spc.iupp == 1 {
        let nip = spc.nip as usize;
        spc.basis[1].beta = -1.0 / (s1 * spc.basis[1].c2[nip][1]).abs();
    }
}

/// `rearrange`: sort the data and move the knots to distinct data points.
/// Returns 1 on success, 0 if the knots could not be made distinct.
fn rearrange(spc: &mut Space, data: &DataS) -> i32 {
    let nk = spc.nk as usize;
    let n = data.ndata as usize;
    let mut sorted = vec![0.0f64; n + 1];
    let mut ix = vec![0i32; n + 1];
    let mut jx = [0i32; 500];
    for i in 0..n {
        sorted[i] = data.data[i];
        ix[i] = i as i32;
    }
    let mut k: usize = 1;
    for i in 1..n {
        if sorted[i] > sorted[k - 1] {
            sorted[k] = sorted[i];
            ix[k] = ix[i];
            k += 1;
        }
    }
    let mut is: usize = 0;
    for i in 0..nk {
        for j in is..k {
            if spc.knots[i] <= sorted[j] {
                jx[i] = j as i32;
                is = j;
                break;
            }
        }
    }
    for _ in 0..10 {
        for j in 1..nk.saturating_sub(1) {
            if jx[j] == jx[j - 1] && jx[j + 1] > jx[j] {
                jx[j] += 1;
            }
        }
        let mut j = nk as i64 - 2;
        while j > 0 {
            let ju = j as usize;
            if jx[ju] == jx[ju + 1] && jx[ju - 1] < jx[ju] {
                jx[ju] -= 1;
            }
            j -= 1;
        }
    }
    let mut l = 1;
    for j in 1..nk {
        if jx[j] == jx[j - 1] {
            l = 0;
        }
    }
    if l == 0 {
        return 0;
    }
    for i in 0..nk {
        spc.iknots[i] = ix[jx[i] as usize];
        spc.knots[i] = sorted[jx[i] as usize];
    }
    1
}

/// `startspace`: place the starting knots for the model (by `strt`), set up
/// the basis and the starting values. Returns 0 if the knots cannot be placed.
pub fn startspace(spc: &mut Space, data: &mut DataS, strt: i32, silent: i32) -> i32 {
    let k = data.ndata;
    let mut ok: i32 = 1;
    let mut l: i32 = 0;
    // place the knots
    if strt == 0 {
        spc.iknots[0] = 0;
        spc.iknots[1] = k / 2;
        spc.iknots[2] = k - 1;
        for i in 0..3 {
            spc.knots[i] = data.data[spc.iknots[i] as usize];
        }
        spc.nk = 3;
        if silent == 1 {
            rprintf(&format!(
                "Starting knots at {:.2}, {:.2} and {:.2} ",
                spc.knots[0], spc.knots[1], spc.knots[2]
            ));
        }
        spc.ndim = 2;
    }
    if strt < 0 {
        let kf = k as f64;
        if strt == -1 {
            l = spc.nk;
            let r = l as f64 + 2.0;
            if l > 3 {
                let s = (l as f64) / ((l as f64) - 3.0);
                for i in 1..(l - 1) {
                    spc.iknots[i as usize] = ((((i - 1) as f64) * s + 1.0) / r * kf) as i32;
                }
            } else {
                spc.iknots[1] = ((k - 1) as f64 / 2.0) as i32;
            }
            spc.iknots[0] = 0;
            spc.iknots[(l - 1) as usize] = k - 1;
        }
        if strt == -2 {
            l = spc.nk;
            let r = l as f64 + 4.0;
            if l > 3 {
                let s = ((l + 2) as f64) / ((l as f64) - 3.0);
                for i in 1..(l - 1) {
                    spc.iknots[i as usize] = ((((i - 1) as f64) * s + 1.0) / r * kf) as i32;
                }
            } else {
                spc.iknots[1] = ((k - 1) as f64 / 2.0) as i32;
            }
            spc.iknots[0] = 1;
            spc.iknots[(l - 1) as usize] = k - 2;
        }
        if strt == -3 {
            l = spc.nk - 2;
            let r = l as f64 + 2.0;
            let mut s = 0.0f64;
            if l > 3 {
                s = (l as f64) / ((l as f64) - 3.0);
            }
            for i in 1..(l - 1) {
                spc.iknots[(i + 1) as usize] = ((((i - 1) as f64) * s + 1.0) / r * (kf - 8.0) + 4.0) as i32;
            }
            spc.iknots[1] = 4;
            spc.iknots[l as usize] = k - 5;
            spc.iknots[0] = 0;
            spc.iknots[(l + 1) as usize] = k - 1;
            l += 2;
        }
        for i in 0..l as usize {
            spc.knots[i] = data.data[spc.iknots[i] as usize];
            if i > 0 && spc.knots[i] <= spc.knots[i - 1] {
                ok = 0;
            }
        }
        spc.nk = l;
        if ok == 0 {
            ok = rearrange(spc, data);
        }
        if ok == 0 {
            return ok;
        }
        spc.ndim = l - 1;
        if silent == 1 {
            rprintf("\nRestart: knots at ");
            for i in 0..l as usize {
                rprintf(&format!("{:.2} ", spc.knots[i]));
            }
        }
    }
    if spc.ilow == 1 {
        spc.low = data.data[0];
    }
    if spc.iupp == 1 {
        spc.upp = data.data[(k - 1) as usize];
    }
    // compute c1, c2, c3 and so on
    setupspace(spc, data);
    // starting values
    startnow(spc, data);
    ok
}
