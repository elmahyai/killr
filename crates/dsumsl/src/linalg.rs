//! Packed triangular kernels from `dsumsl.f` (`DLITVM`, `DLIVMU`, `DLTVMU`, `DLVMUL`, `DLUPDT`, `DWZBFG`).

use crate::work::Work;

fn lget(w: &Work, base: i32, jj: i32) -> f64 {
    w.v[(base + jj - 1) as usize]
}
fn lset(w: &mut Work, base: i32, jj: i32, val: f64) {
    w.v[(base + jj - 1) as usize] = val;
}

/// Solve `(L**T) x = y`. `EXIT` on a zero component leaves the remaining rows,
/// matching tseries `DLITVM`.
pub fn dlitvm(w: &mut Work, x: i32, lbase: i32, y: i32) {
    let n = w.n;
    for i in 1..=n {
        let val = w.av(y, i);
        w.sv(x, i, val);
    }
    let mut i0 = n * (n + 1) / 2;
    let np1 = n + 1;
    for ii in 1..=n {
        let i = np1 - ii;
        let xi = w.av(x, i) / lget(w, lbase, i0);
        w.sv(x, i, xi);
        if i <= 1 {
            return;
        }
        i0 -= i;
        if xi == 0.0 {
            break;
        }
        for j in 1..i {
            let ij = i0 + j;
            let val = w.av(x, j) - xi * lget(w, lbase, ij);
            w.sv(x, j, val);
        }
    }
}

/// Solve `L x = y`.
pub fn dlivmu(w: &mut Work, x: i32, lbase: i32, y: i32) {
    let n = w.n;
    let mut k_nz = 0i32;
    for k in 1..=n {
        if w.av(y, k) != 0.0 {
            k_nz = k;
            break;
        }
        w.sv(x, k, 0.0);
    }
    if k_nz == 0 {
        return;
    }
    let mut j = k_nz * (k_nz + 1) / 2;
    w.sv(x, k_nz, w.av(y, k_nz) / lget(w, lbase, j));
    if k_nz >= n {
        return;
    }
    for i in (k_nz + 1)..=n {
        let t = w.dotv(i - 1, lbase + j, x);
        j += i;
        w.sv(x, i, (w.av(y, i) - t) / lget(w, lbase, j));
    }
}

/// `x = L**T y` for packed lower `L` stored by rows.
pub fn dltvmu(w: &mut Work, x: i32, lbase: i32, y: i32) {
    let n = w.n;
    let mut i0 = 0i32;
    for i in 1..=n {
        let yi = w.av(y, i);
        w.sv(x, i, 0.0);
        for j in 1..=i {
            let ij = i0 + j;
            let val = w.av(x, j) + yi * lget(w, lbase, ij);
            w.sv(x, j, val);
        }
        i0 += i;
    }
}

/// `x = L y`. Safe when `x` and `y` alias, because the loop runs from the bottom.
pub fn dlvmul(w: &mut Work, x: i32, lbase: i32, y: i32) {
    let n = w.n;
    let mut i0 = n * (n + 1) / 2;
    let np1 = n + 1;
    for ii in 1..=n {
        let i = np1 - ii;
        i0 -= i;
        let mut t = 0.0;
        for j in 1..=i {
            t += lget(w, lbase, i0 + j) * w.av(y, j);
        }
        w.sv(x, i, t);
    }
}

pub fn dwzbfg(w: &mut Work, lbase: i32, s: i32, wv: i32, y: i32, z: i32) {
    let n = w.n;
    dltvmu(w, wv, lbase, s);
    let shs = w.dotv(n, wv, wv);
    let ys = w.dotv(n, y, s);
    let (cs, cy) = if ys >= 0.1 * shs {
        let cy = 1.0 / (ys.sqrt() * shs.sqrt());
        let cs = 1.0 / shs;
        (cs, cy)
    } else {
        let theta = (1.0 - 0.1) * shs / (shs - ys);
        let epsrt = 0.1_f64.sqrt();
        let cy = theta / (shs * epsrt);
        let cs = (1.0 + (theta - 1.0) / epsrt) / shs;
        (cs, cy)
    };
    dlivmu(w, z, lbase, y);
    for i in 1..=n {
        let val = cy * w.av(z, i) - cs * w.av(wv, i);
        w.sv(z, i, val);
    }
}

pub fn dlupdt(w: &mut Work, beta: i32, gamma: i32, lbase: i32, lambda: i32, wv: i32, z: i32) {
    let n = w.n;
    let mut nu = 1.0;
    let mut eta = 0.0;
    if n > 1 {
        let nm1 = n - 1;
        let mut s = 0.0;
        for i in 1..=nm1 {
            let j = n - i;
            s += w.av(wv, j + 1) * w.av(wv, j + 1);
            w.sv(lambda, j, s);
        }
        for j in 1..=nm1 {
            let wj = w.av(wv, j);
            let a = nu * w.av(z, j) - eta * wj;
            let theta = 1.0 + a * wj;
            let s = a * w.av(lambda, j);
            let mut lj = (theta * theta + a * s).sqrt();
            if theta > 0.0 {
                lj = -lj;
            }
            w.sv(lambda, j, lj);
            let b = theta * wj + s;
            w.sv(gamma, j, b * nu / lj);
            w.sv(beta, j, (a - b * eta) / lj);
            nu = -nu / lj;
            eta = -(eta + (a * a) / (theta - lj)) / lj;
        }
    }
    w.sv(
        lambda,
        n,
        1.0 + (nu * w.av(z, n) - eta * w.av(wv, n)) * w.av(wv, n),
    );
    let np1 = n + 1;
    let mut jj = n * (n + 1) / 2;
    for k in 1..=n {
        let j = np1 - k;
        let lj = w.av(lambda, j);
        let ljj = lget(w, lbase, jj);
        lset(w, lbase, jj, lj * ljj);
        let wj = w.av(wv, j);
        w.sv(wv, j, ljj * wj);
        let zj = w.av(z, j);
        w.sv(z, j, ljj * zj);
        if k != 1 {
            let bj = w.av(beta, j);
            let gj = w.av(gamma, j);
            let mut ij = jj + j;
            for i in (j + 1)..=n {
                let lij = lget(w, lbase, ij);
                lset(
                    w,
                    lbase,
                    ij,
                    lj * lij + bj * w.av(wv, i) + gj * w.av(z, i),
                );
                let wi = w.av(wv, i) + lij * wj;
                w.sv(wv, i, wi);
                let zi = w.av(z, i) + lij * zj;
                w.sv(z, i, zi);
                ij += i;
            }
        }
        jj -= j;
    }
}
