//! Column-major helpers and the LINPACK pieces `nlmefit.c` calls.
//!
//! `dqrdc2` is R's rank-revealing QR. Pivot labels stay zero-based, matching
//! the `0 .. p-1` vector `QR()` stores before the Fortran call.

pub fn sqrt_eps() -> f64 {
    f64::EPSILON.sqrt()
}

pub fn at(ld: usize, row: usize, col: usize) -> usize {
    row + col * ld
}

pub fn d_sum_sqr(x: &[f64], start: usize, n: usize) -> f64 {
    let mut acc = 0.0;
    for i in 0..n {
        let v = x[start + i];
        acc += v * v;
    }
    acc
}

pub fn d_dot(x: &[f64], x0: usize, incx: usize, y: &[f64], y0: usize, incy: usize, n: usize) -> f64 {
    let mut acc = 0.0;
    for i in 0..n {
        acc += x[x0 + i * incx] * y[y0 + i * incy];
    }
    acc
}

pub fn d_axpy(y: &mut [f64], y0: usize, a: f64, x: &[f64], x0: usize, n: usize) {
    if n == 0 || a == 0.0 {
        return;
    }
    for i in 0..n {
        y[y0 + i] += a * x[x0 + i];
    }
}

pub fn copy_mat(y: &mut [f64], ldy: usize, y0: usize, x: &[f64], ldx: usize, x0: usize, nrow: usize, ncol: usize) {
    for j in 0..ncol {
        for i in 0..nrow {
            y[y0 + i + j * ldy] = x[x0 + i + j * ldx];
        }
    }
}

pub fn copy_trans(y: &mut [f64], ldy: usize, y0: usize, x: &[f64], ldx: usize, x0: usize, nrow: usize, ncol: usize) {
    for i in 0..nrow {
        for j in 0..ncol {
            y[y0 + j + i * ldy] = x[x0 + i + j * ldx];
        }
    }
}

pub fn scale_mat(y: &mut [f64], ldy: usize, y0: usize, a: f64, x: &[f64], ldx: usize, x0: usize, nrow: usize, ncol: usize) {
    for j in 0..ncol {
        for i in 0..nrow {
            y[y0 + i + j * ldy] = a * x[x0 + i + j * ldx];
        }
    }
}

pub fn plus_equals_mat(y: &mut [f64], ldy: usize, y0: usize, x: &[f64], ldx: usize, x0: usize, nrow: usize, ncol: usize) {
    for j in 0..ncol {
        for i in 0..nrow {
            y[y0 + i + j * ldy] += x[x0 + i + j * ldx];
        }
    }
}

pub fn zero_mat(y: &mut [f64], ldy: usize, y0: usize, nrow: usize, ncol: usize) {
    for j in 0..ncol {
        for i in 0..nrow {
            y[y0 + i + j * ldy] = 0.0;
        }
    }
}

pub fn mult_into(z: &mut [f64], ldz: usize, z0: usize, x: &[f64], ldx: usize, x0: usize, xrows: usize, xcols: usize, y: &[f64], ldy: usize, y0: usize, ycols: usize) {
    let mut tmp = vec![0.0; xrows * ycols];
    for col in 0..ycols {
        for k in 0..xcols {
            let coef = y[y0 + k + col * ldy];
            if coef == 0.0 {
                continue;
            }
            for r in 0..xrows {
                tmp[r + col * xrows] += coef * x[x0 + r + k * ldx];
            }
        }
    }
    for col in 0..ycols {
        for r in 0..xrows {
            z[z0 + r + col * ldz] = tmp[r + col * xrows];
        }
    }
}

// R's `dqrdc2` and `dqrsl` call the BLAS `DNRM2`, `DDOT`, and `DAXPY`. R on
// this machine links `libblas.so.3` (OpenBLAS 0.3.29), and the rounding of
// those routines (long-double `dnrm2`, SIMD and FMA `ddot`/`daxpy`) is part of
// R's `lRSS`. A plain Rust loop is one or two ulps off, and a central
// difference of the log-likelihood turns that into a 1e-5 gradient error.
#[link(name = "blas")]
extern "C" {
    fn dnrm2_(n: *const i32, x: *const f64, incx: *const i32) -> f64;
    fn ddot_(n: *const i32, x: *const f64, incx: *const i32, y: *const f64, incy: *const i32) -> f64;
    fn daxpy_(n: *const i32, a: *const f64, x: *const f64, incx: *const i32, y: *mut f64, incy: *const i32);
}

fn dnrm2(x: &[f64], start: usize, n: usize, inc: usize) -> f64 {
    if n == 0 {
        return 0.0;
    }
    let len = n as i32;
    let incx = inc as i32;
    // SAFETY: `x[start + (n - 1) * inc]` is in bounds for every caller in this file.
    unsafe { dnrm2_(&len, x.as_ptr().add(start), &incx) }
}

/// `DDOT` over `n` contiguous entries of `x` at `x0` and of `y` at `y0`.
fn ddot_contig(n: usize, x: &[f64], x0: usize, y: &[f64], y0: usize) -> f64 {
    if n == 0 {
        return 0.0;
    }
    let len = n as i32;
    let inc = 1_i32;
    // SAFETY: both ranges hold `n` contiguous values, checked by the slicing.
    unsafe { ddot_(&len, x[x0..x0 + n].as_ptr(), &inc, y[y0..y0 + n].as_ptr(), &inc) }
}

/// `DAXPY` on two disjoint column ranges of one matrix: `x[y0..] += a * x[x0..]`.
fn daxpy_within(n: usize, a: f64, x: &mut [f64], x0: usize, y0: usize) {
    if n == 0 {
        return;
    }
    assert!(x0 + n <= x.len() && y0 + n <= x.len() && (x0 + n <= y0 || y0 + n <= x0));
    let len = n as i32;
    let inc = 1_i32;
    let base = x.as_mut_ptr();
    // SAFETY: both ranges are in bounds and disjoint (asserted above).
    unsafe { daxpy_(&len, &a, base.add(x0), &inc, base.add(y0), &inc) }
}

/// `DAXPY` from `x[x0..]` into `y[y0..]` for two different slices.
fn daxpy_into(n: usize, a: f64, x: &[f64], x0: usize, y: &mut [f64], y0: usize) {
    if n == 0 {
        return;
    }
    let len = n as i32;
    let inc = 1_i32;
    // SAFETY: both ranges hold `n` contiguous values, checked by the slicing.
    unsafe { daxpy_(&len, &a, x[x0..x0 + n].as_ptr(), &inc, y[y0..y0 + n].as_mut_ptr(), &inc) }
}

/// R `dqrdc2`. Returns the numerical rank. `pivot` is permuted in place.
pub fn dqrdc2(x: &mut [f64], ldx: usize, n: usize, p: usize, tol: f64, qraux: &mut [f64], pivot: &mut [i32]) -> usize {
    let mut work1 = vec![0.0; p];
    let mut work2 = vec![0.0; p];
    if n > 0 {
        for j in 0..p {
            let nrm = dnrm2(x, j * ldx, n, 1);
            qraux[j] = nrm;
            work1[j] = nrm;
            work2[j] = if nrm == 0.0 { 1.0 } else { nrm };
        }
    }
    let lup = n.min(p);
    let mut k = p + 1;
    for l in 1..=lup {
        loop {
            if l >= k || qraux[l - 1] >= work2[l - 1] * tol {
                break;
            }
            for i in 0..n {
                let t = x[i + (l - 1) * ldx];
                for j in (l + 1)..=p {
                    x[i + (j - 2) * ldx] = x[i + (j - 1) * ldx];
                }
                x[i + (p - 1) * ldx] = t;
            }
            let ip = pivot[l - 1];
            let t = qraux[l - 1];
            let tt = work1[l - 1];
            let ttt = work2[l - 1];
            for j in (l + 1)..=p {
                pivot[j - 2] = pivot[j - 1];
                qraux[j - 2] = qraux[j - 1];
                work1[j - 2] = work1[j - 1];
                work2[j - 2] = work2[j - 1];
            }
            pivot[p - 1] = ip;
            qraux[p - 1] = t;
            work1[p - 1] = tt;
            work2[p - 1] = ttt;
            k -= 1;
        }
        if l != n {
            let col = l - 1;
            let mut nrmxl = dnrm2(x, col + col * ldx, n - l + 1, 1);
            if nrmxl != 0.0 {
                let diag = x[col + col * ldx];
                if diag != 0.0 {
                    nrmxl = nrmxl.copysign(diag);
                }
                let inv = 1.0 / nrmxl;
                for i in 0..(n - l + 1) {
                    x[(col + i) + col * ldx] *= inv;
                }
                x[col + col * ldx] += 1.0;
                if p >= l + 1 {
                    for j in (l + 1)..=p {
                        let len = n - l + 1;
                        let dot = ddot_contig(len, x, col + col * ldx, x, col + (j - 1) * ldx);
                        let t = -dot / x[col + col * ldx];
                        daxpy_within(len, t, x, col + col * ldx, col + (j - 1) * ldx);
                        if qraux[j - 1] != 0.0 {
                            let mut tt = 1.0 - (x[col + (j - 1) * ldx].abs() / qraux[j - 1]).powi(2);
                            if tt < 0.0 {
                                tt = 0.0;
                            }
                            if tt.abs() >= 1e-6 {
                                qraux[j - 1] *= tt.sqrt();
                            } else {
                                let nrm = dnrm2(x, l + (j - 1) * ldx, n - l, 1);
                                qraux[j - 1] = nrm;
                                work1[j - 1] = nrm;
                            }
                        }
                    }
                }
                qraux[col] = x[col + col * ldx];
                x[col + col * ldx] = -nrmxl;
            }
        }
    }
    (k - 1).min(n)
}

fn dqrsl_qty(x: &mut [f64], ldx: usize, n: usize, k: usize, qraux: &[f64], y: &mut [f64]) {
    let ju = k.min(n.saturating_sub(1));
    if ju == 0 {
        return;
    }
    for j in 1..=ju {
        let j0 = j - 1;
        if qraux[j0] == 0.0 {
            continue;
        }
        let temp = x[j0 + j0 * ldx];
        x[j0 + j0 * ldx] = qraux[j0];
        let len = n - j + 1;
        let dot = ddot_contig(len, x, j0 + j0 * ldx, y, j0);
        let t = -dot / x[j0 + j0 * ldx];
        daxpy_into(len, t, x, j0 + j0 * ldx, y, j0);
        x[j0 + j0 * ldx] = temp;
    }
}

pub struct Qr {
    pub qraux: Vec<f64>,
    pub pivot: Vec<i32>,
    pub rank: usize,
    pub nrow: usize,
    pub ncol: usize,
    pub ld: usize,
}

pub fn qr_factor(mat: &mut [f64], ld: usize, nrow: usize, ncol: usize) -> Qr {
    let mut qraux = vec![0.0; ncol];
    let mut pivot: Vec<i32> = (0..ncol as i32).collect();
    let rank = if ncol == 0 || nrow == 0 {
        0
    } else {
        dqrdc2(mat, ld, nrow, ncol, sqrt_eps(), &mut qraux, &mut pivot)
    };
    Qr {
        qraux,
        pivot,
        rank,
        nrow,
        ncol,
        ld,
    }
}

pub fn qr_qty_inplace(mat: &mut [f64], qr: &Qr, y: &mut [f64]) {
    dqrsl_qty(mat, qr.ld, qr.nrow, qr.ncol, &qr.qraux, y);
}

pub fn qr_solve_into(mat: &mut [f64], qr: &Qr, y: &[f64], beta: &mut [f64]) {
    let mut qty = y[..qr.nrow].to_vec();
    dqrsl_qty(mat, qr.ld, qr.nrow, qr.ncol, &qr.qraux, &mut qty);
    let k = qr.ncol;
    let mut b = qty[..k].to_vec();
    for jj in 1..=k {
        let j = k - jj + 1;
        let j0 = j - 1;
        if mat[j0 + j0 * qr.ld] == 0.0 {
            break;
        }
        b[j0] /= mat[j0 + j0 * qr.ld];
        if j != 1 {
            let t = -b[j0];
            for i in 0..j0 {
                b[i] += t * mat[i + j0 * qr.ld];
            }
        }
    }
    beta[..k].copy_from_slice(&b);
}

pub fn qr_log_abs_det(mat: &[f64], qr: &Qr) -> f64 {
    let mut acc = 0.0;
    for j in 0..qr.rank {
        acc += mat[j + j * qr.ld].abs().ln();
    }
    acc
}

pub fn qr_store_r(mat: &[f64], qr: &Qr, dest: &mut [f64], ld_dest: usize, dest0: usize) {
    for i in 0..qr.ncol {
        let rows = if i + 1 > qr.rank { qr.rank } else { i + 1 };
        let dst_col = qr.pivot[i] as usize;
        for r in 0..rows {
            dest[dest0 + r + dst_col * ld_dest] = mat[r + i * qr.ld];
        }
    }
}

/// Upper-triangular solve with a right-hand side that does not alias `T`.
pub fn dtrsl_upper_sep(t: &[f64], t0: usize, ldt: usize, n: usize, b: &mut [f64]) -> i32 {
    if n == 0 {
        return 0;
    }
    for i in 0..n {
        if t[t0 + i + i * ldt] == 0.0 {
            return (i as i32) + 1;
        }
    }
    b[n - 1] /= t[t0 + (n - 1) + (n - 1) * ldt];
    if n >= 2 {
        for jj in 2..=n {
            let j = n - jj + 1;
            let temp = -b[j];
            for i in 0..j {
                b[i] += temp * t[t0 + i + j * ldt];
            }
            b[j - 1] /= t[t0 + (j - 1) + (j - 1) * ldt];
        }
    }
    0
}

/// Upper-triangular solve `T x = b` (`dtrsl` job 1).
/// `b0` is the contiguous right-hand side inside the same buffer as `T`.
pub fn dtrsl_upper(dc: &mut [f64], t0: usize, ldt: usize, n: usize, b0: usize) -> i32 {
    if n == 0 {
        return 0;
    }
    for i in 0..n {
        if dc[t0 + i + i * ldt] == 0.0 {
            return (i as i32) + 1;
        }
    }
    dc[b0 + n - 1] /= dc[t0 + (n - 1) + (n - 1) * ldt];
    if n >= 2 {
        for jj in 2..=n {
            let j = n - jj + 1;
            let temp = -dc[b0 + j];
            for i in 0..j {
                dc[b0 + i] += temp * dc[t0 + i + j * ldt];
            }
            dc[b0 + j - 1] /= dc[t0 + (j - 1) + (j - 1) * ldt];
        }
    }
    0
}

/// LINPACK `dpofa` with R's `1e-14` positive-definiteness tolerance.
/// Returns 0, or the 1-based leading minor that failed.
pub fn dpofa(a: &mut [f64], lda: usize, n: usize) -> i32 {
    const EPS: f64 = 1.0e-14;
    for j in 1..=n {
        let mut s = 0.0;
        let jm1 = j - 1;
        if jm1 >= 1 {
            for k in 1..=jm1 {
                let mut t = a[(k - 1) + (j - 1) * lda];
                if k > 1 {
                    let mut dot = 0.0;
                    for i in 0..(k - 1) {
                        dot += a[i + (k - 1) * lda] * a[i + (j - 1) * lda];
                    }
                    t -= dot;
                }
                t /= a[(k - 1) + (k - 1) * lda];
                a[(k - 1) + (j - 1) * lda] = t;
                s += t * t;
            }
        }
        s = a[(j - 1) + (j - 1) * lda] - s;
        if s <= EPS * a[(j - 1) + (j - 1) * lda].abs() {
            return j as i32;
        }
        a[(j - 1) + (j - 1) * lda] = s.sqrt();
    }
    0
}

pub fn chol_factor(a: &[f64], lda: usize, n: usize) -> Result<Vec<f64>, i32> {
    let mut v = vec![0.0; n * n];
    for j in 0..n {
        for i in 0..=j {
            v[i + j * n] = a[i + j * lda];
        }
    }
    let info = dpofa(&mut v, n, n);
    if info != 0 {
        Err(info)
    } else {
        Ok(v)
    }
}

/// `matrixLog_pd` for `q == 1`. Larger `q` uses [`matrix_log_pd`].
pub fn log_chol_pd(params: &[f64], q: usize) -> Vec<f64> {
    let mut l = vec![0.0; q * q];
    if q == 0 {
        return l;
    }
    l[0] = params[0].exp();
    let mut ll = q;
    for i in 1..q {
        l[i * (q + 1)] = params[i].exp();
        let len = i;
        l[i * q..i * q + len].copy_from_slice(&params[ll..ll + len]);
        ll += i;
    }
    l
}

pub fn comp_symm_pd(params: &[f64], q: usize) -> Vec<f64> {
    let mut l = vec![0.0; q * q];
    if q == 0 {
        return l;
    }
    let aux = params[0].exp();
    let mut aux1 = params[1].exp();
    aux1 = (aux1 - 1.0 / ((q as f64) - 1.0)) / (aux1 + 1.0);
    let aux2 = aux * (1.0 - aux1).sqrt();
    let aux1 = aux * ((1.0 + ((q as f64) - 1.0) * aux1) / (q as f64)).sqrt();
    for i in 0..q {
        l[i * q] = aux1;
    }
    for i in 1..q {
        let aux = -aux2 / ((i * (i + 1)) as f64).sqrt();
        for j in 0..i {
            l[i + j * q] = aux;
        }
        l[i * (q + 1)] = -aux * (i as f64);
    }
    l
}

pub(crate) fn jacobi_sym(a: &mut [f64], q: usize) -> (Vec<f64>, Vec<f64>) {
    let mut v = vec![0.0; q * q];
    for i in 0..q {
        v[i + i * q] = 1.0;
    }
    let mut values = vec![0.0; q];
    if q == 0 {
        return (values, v);
    }
    for _ in 0..60 {
        let mut p = 0;
        let mut qq = 1;
        let mut max = 0.0;
        for i in 0..q {
            for j in (i + 1)..q {
                let aij = a[i + j * q].abs();
                if aij > max {
                    max = aij;
                    p = i;
                    qq = j;
                }
            }
        }
        if max <= 1e-15 {
            break;
        }
        let app = a[p + p * q];
        let aqq = a[qq + qq * q];
        let apq = a[p + qq * q];
        let tau = (aqq - app) / (2.0 * apq);
        let t = if tau >= 0.0 {
            1.0 / (tau + (1.0 + tau * tau).sqrt())
        } else {
            -1.0 / (-tau + (1.0 + tau * tau).sqrt())
        };
        let c = 1.0 / (1.0 + t * t).sqrt();
        let s = t * c;
        a[p + p * q] = app - t * apq;
        a[qq + qq * q] = aqq + t * apq;
        a[p + qq * q] = 0.0;
        a[qq + p * q] = 0.0;
        for i in 0..q {
            if i != p && i != qq {
                let aip = a[i + p * q];
                let aiq = a[i + qq * q];
                a[i + p * q] = c * aip - s * aiq;
                a[p + i * q] = a[i + p * q];
                a[i + qq * q] = s * aip + c * aiq;
                a[qq + i * q] = a[i + qq * q];
            }
            let vip = v[i + p * q];
            let viq = v[i + qq * q];
            v[i + p * q] = c * vip - s * viq;
            v[i + qq * q] = s * vip + c * viq;
        }
    }
    for i in 0..q {
        values[i] = a[i + i * q];
    }
    for i in 0..q {
        let mut max_i = i;
        let mut max_v = values[i];
        for j in (i + 1)..q {
            if values[j] < max_v {
                max_v = values[j];
                max_i = j;
            }
        }
        if max_i != i {
            values.swap(i, max_i);
            for r in 0..q {
                let tmp = v[r + i * q];
                v[r + i * q] = v[r + max_i * q];
                v[r + max_i * q] = tmp;
            }
        }
        let mut pivot = 0;
        let mut mag = v[0 + i * q].abs();
        for r in 1..q {
            if v[r + i * q].abs() > mag {
                mag = v[r + i * q].abs();
                pivot = r;
            }
        }
        if v[pivot + i * q] < 0.0 {
            for r in 0..q {
                v[r + i * q] = -v[r + i * q];
            }
        }
    }
    (values, v)
}

pub fn matrix_log_pd(params: &[f64], q: usize) -> Vec<f64> {
    let mut l = vec![0.0; q * q];
    if q == 0 {
        return l;
    }
    if q == 1 {
        l[0] = params[0].exp();
        return l;
    }
    let mut src = 0;
    for i in 0..q {
        for r in 0..=i {
            l[r + i * q] = params[src];
            src += 1;
        }
    }
    for i in 0..(q - 1) {
        let ncol = q - (i + 1);
        for j in 0..ncol {
            l[(i + 1 + j) + i * q] = l[i + (i + 1 + j) * q];
        }
    }
    let (values, vectors) = jacobi_sym(&mut l, q);
    let mut scaled = vectors;
    for i in 0..q {
        let ev = values[i].exp();
        for j in 0..q {
            scaled[j + i * q] *= ev;
        }
    }
    let mut out = vec![0.0; q * q];
    copy_trans(&mut out, q, 0, &scaled, q, 0, q, q);
    out
}
