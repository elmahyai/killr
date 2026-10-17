//! GLS log-likelihood and coefficient estimate from nlme `src/nlmefit.c`.
//!
//! `gls_loglik` and `gls_estimate` factor the condensed `[X | y]` matrix with
//! `QR()` in `src/matrix.c`. That constructor calls R's `dqrdc2` at tolerance
//! `sqrt(DBL_EPSILON)` and seeds `pivot` with `0 .. ncol - 1`.

use std::time::Instant;

// R's `dqrdc2` calls the BLAS `DNRM2`, `DDOT`, and `DAXPY`. R on this machine
// links `libblas.so.3`, which is OpenBLAS 0.3.29; these calls use the same
// library, so the rounding (long-double `dnrm2`, SIMD and FMA `ddot`/`daxpy`)
// is R's. Plain Rust loops do not reproduce R's bits.
#[link(name = "blas")]
extern "C" {
    fn dnrm2_(n: *const i32, x: *const f64, incx: *const i32) -> f64;
    fn ddot_(
        n: *const i32,
        x: *const f64,
        incx: *const i32,
        y: *const f64,
        incy: *const i32,
    ) -> f64;
    fn daxpy_(
        n: *const i32,
        a: *const f64,
        x: *const f64,
        incx: *const i32,
        y: *mut f64,
        incy: *const i32,
    );
}

/// `y[y0..y0+n] += a * x[x0..x0+n]` through BLAS `DAXPY`, as `dqrdc2` does.
/// The two ranges lie in different columns and do not overlap.
fn daxpy_column(n: usize, a: f64, x: &mut [f64], x0: usize, y0: usize) {
    if n == 0 {
        return;
    }
    assert!(x0 + n <= x.len() && y0 + n <= x.len() && (x0 + n <= y0 || y0 + n <= x0));
    let len = n as i32;
    let inc = 1_i32;
    let base = x.as_mut_ptr();
    // SAFETY: both ranges are in bounds and disjoint (checked above).
    unsafe { daxpy_(&len, &a, base.add(x0), &inc, base.add(y0), &inc) }
}

fn dnrm2(x: &[f64], start: usize, n: usize) -> f64 {
    if n == 0 {
        return 0.0;
    }
    let xs = &x[start..start + n];
    let len = n as i32;
    let inc = 1_i32;
    // SAFETY: `xs` holds `n` contiguous f64 values; `len` and `inc` outlive the call.
    unsafe { dnrm2_(&len, xs.as_ptr(), &inc) }
}

fn dscal(n: usize, a: f64, x: &mut [f64], start: usize) {
    for k in 0..n {
        x[start + k] *= a;
    }
}

fn daxpy(n: usize, a: f64, x: &[f64], x0: usize, y: &mut [f64], y0: usize) {
    if n == 0 || a == 0.0 {
        return;
    }
    for k in 0..n {
        y[y0 + k] += a * x[x0 + k];
    }
}

fn ddot(n: usize, x: &[f64], x0: usize, y: &[f64], y0: usize) -> f64 {
    if n == 0 {
        return 0.0;
    }
    let xs = &x[x0..x0 + n];
    let ys = &y[y0..y0 + n];
    let len = n as i32;
    let inc = 1_i32;
    // SAFETY: `xs` and `ys` each hold `n` contiguous f64 values.
    unsafe { ddot_(&len, xs.as_ptr(), &inc, ys.as_ptr(), &inc) }
}

fn rotate_f64(values: &mut [f64], col: usize, p: usize) {
    let saved = values[col];
    for j in (col + 1)..p {
        values[j - 1] = values[j];
    }
    values[p - 1] = saved;
}

fn rotate_i32(values: &mut [i32], col: usize, p: usize) {
    let saved = values[col];
    for j in (col + 1)..p {
        values[j - 1] = values[j];
    }
    values[p - 1] = saved;
}

fn rotate_column(x: &mut [f64], ldx: usize, n: usize, p: usize, col: usize) {
    for i in 0..n {
        let saved = x[col * ldx + i];
        for j in (col + 1)..p {
            x[(j - 1) * ldx + i] = x[j * ldx + i];
        }
        x[(p - 1) * ldx + i] = saved;
    }
}

/// Rank-revealing QR from R `src/appl/dqrdc2.f`.
///
/// `jpvt` is permuted with the columns. nlme seeds it with `0 .. p - 1`.
/// Returns the rank `k`.
pub fn dqrdc2(
    x: &mut [f64],
    ldx: usize,
    n: usize,
    p: usize,
    tol: f64,
    qraux: &mut [f64],
    jpvt: &mut [i32],
) -> i32 {
    let mut work1 = vec![0.0; p];
    let mut work2 = vec![0.0; p];
    if n > 0 {
        for j in 0..p {
            let norm = dnrm2(x, j * ldx, n);
            qraux[j] = norm;
            work1[j] = norm;
            work2[j] = if norm == 0.0 { 1.0 } else { norm };
        }
    }
    let lup = n.min(p);
    let mut k = (p as i32) + 1;
    for col in 0..lup {
        let l = (col as i32) + 1;
        loop {
            if l >= k || qraux[col] >= work2[col] * tol {
                break;
            }
            rotate_column(x, ldx, n, p, col);
            rotate_i32(jpvt, col, p);
            rotate_f64(qraux, col, p);
            rotate_f64(&mut work1, col, p);
            rotate_f64(&mut work2, col, p);
            k -= 1;
        }
        if l != n as i32 {
            let length = n - col;
            let diag = col * ldx + col;
            let mut nrmxl = dnrm2(x, diag, length);
            if nrmxl != 0.0 {
                if x[diag] != 0.0 {
                    nrmxl = nrmxl.copysign(x[diag]);
                }
                dscal(length, 1.0 / nrmxl, x, diag);
                x[diag] = 1.0 + x[diag];
                if p >= col + 2 {
                    for j in (col + 1)..p {
                        let column = j * ldx + col;
                        let t = -ddot(length, x, diag, x, column) / x[diag];
                        daxpy_column(length, t, x, diag, column);
                        if qraux[j] != 0.0 {
                            let entry = x[j * ldx + col].abs() / qraux[j];
                            let mut tt = 1.0 - entry * entry;
                            if tt < 0.0 {
                                tt = 0.0;
                            }
                            if tt.abs() >= 1.0e-6 {
                                qraux[j] *= tt.sqrt();
                            } else {
                                let below = if col + 1 < n { n - col - 1 } else { 0 };
                                qraux[j] = dnrm2(x, j * ldx + col + 1, below);
                                work1[j] = qraux[j];
                            }
                        }
                    }
                }
                qraux[col] = x[diag];
                x[diag] = -nrmxl;
            }
        }
    }
    k = (k - 1).min(n as i32);
    k
}

fn qr_nlme(mat: &mut [f64], n: usize, ncol: usize) -> (i32, Vec<i32>) {
    let mut qraux = vec![0.0; ncol];
    let mut pivot: Vec<i32> = (0..ncol as i32).collect();
    let rank = dqrdc2(
        mat,
        n,
        n,
        ncol,
        f64::EPSILON.sqrt(),
        &mut qraux,
        &mut pivot,
    );
    (rank, pivot)
}

/// `gls_loglik`. `log_lik` is updated in place unless the rank is short,
/// which stores `-DBL_MAX` and leaves `l_rss` unchanged.
pub fn gls_loglik(
    xy: &[f64],
    n: usize,
    p: usize,
    reml: i32,
    mut log_lik: f64,
    mut l_rss: f64,
    sigma: f64,
) -> (f64, f64) {
    let ncol = p + 1;
    assert!(xy.len() >= n * ncol, "Xy must be column-major n by p+1");
    let mut mat = xy[..n * ncol].to_vec();
    let (rank, _) = qr_nlme(&mut mat, n, ncol);
    if rank - 1 != p as i32 {
        log_lik = -f64::MAX;
    } else {
        let step = n + 1;
        let f = mat[p * step].abs();
        l_rss = f.ln();
        let nr = (n as i32) - reml * (p as i32);
        if sigma > 0.0 {
            let mut h = 0.0;
            if reml == 1 {
                for i in 0..p {
                    h += mat[i * step].abs().ln();
                }
            }
            log_lik -= (f * f) / (2.0 * sigma * sigma);
            log_lik -= (nr as f64) * sigma.ln();
            log_lik -= h;
        } else {
            log_lik -= (nr as f64) * l_rss;
            if reml == 1 {
                for i in 0..p {
                    log_lik -= mat[i * step].abs().ln();
                }
            }
        }
    }
    (log_lik, l_rss)
}

fn copy_mat(y: &mut [f64], ldy: usize, x: &[f64], ldx: usize, nrow: usize, ncol: usize) {
    for col in 0..ncol {
        let dest = col * ldy;
        let src = col * ldx;
        y[dest..dest + nrow].copy_from_slice(&x[src..src + nrow]);
    }
}

fn dtrsl_upper(t: &[f64], ldt: usize, n: usize, b: &mut [f64]) -> i32 {
    for info in 1..=n {
        if t[(info - 1) * ldt + (info - 1)] == 0.0 {
            return info as i32;
        }
    }
    b[n - 1] /= t[(n - 1) * ldt + (n - 1)];
    if n >= 2 {
        for jj in 2..=n {
            let j = n - jj + 1;
            let temp = -b[j];
            daxpy(j, temp, t, j * ldt, b, 0);
            b[j - 1] /= t[(j - 1) * ldt + (j - 1)];
        }
    }
    0
}

fn invert_upper(mat: &mut [f64], ldmat: usize, ncol: usize) -> i32 {
    if ncol == 0 {
        return if mat.first().copied().unwrap_or(0.0) == 0.0 {
            1
        } else {
            0
        };
    }
    let mut b = vec![0.0; ncol];
    for i in (2..=ncol).rev() {
        for j in 0..(i - 1) {
            b[j] = 0.0;
        }
        b[i - 1] = 1.0;
        let info = dtrsl_upper(mat, ldmat, i, &mut b);
        if info != 0 {
            return info;
        }
        let dest = (i - 1) * ldmat;
        mat[dest..dest + i].copy_from_slice(&b[..i]);
    }
    if mat[0] == 0.0 {
        return 1;
    }
    mat[0] = 1.0 / mat[0];
    0
}

fn mult_mat(
    z: &mut [f64],
    ldz: usize,
    x: &[f64],
    ldx: usize,
    xrows: usize,
    xcols: usize,
    y: &[f64],
    ldy: usize,
    ycols: usize,
) {
    let mut tmp = vec![0.0; xrows * ycols];
    for i in 0..ycols {
        let t = i * xrows;
        let ycol = i * ldy;
        for j in 0..xcols {
            daxpy(xrows, y[ycol + j], x, j * ldx, &mut tmp, t);
        }
    }
    copy_mat(z, ldz, &tmp, xrows, xrows, ycols);
}

/// Coefficient estimate, scale, log-likelihood, and upper-triangular
/// inverse of the leading `R` factor, as `gls_estimate` writes them.
#[derive(Clone, Debug)]
pub struct GlsEstimate {
    pub beta: Vec<f64>,
    pub sigma: f64,
    pub log_lik: f64,
    pub var_beta: Vec<f64>,
    pub rank: i32,
    pub pivot: Vec<i32>,
}

pub fn gls_estimate(
    xy: &[f64],
    n: usize,
    p: usize,
    reml: i32,
    mut sigma: f64,
    mut log_lik: f64,
) -> GlsEstimate {
    let pp1 = p + 1;
    assert!(xy.len() >= n * pp1, "Xy must be column-major n by p+1");
    let mut mat = xy[..n * pp1].to_vec();
    let (rank, pivot) = qr_nlme(&mut mat, n, pp1);
    let rk = rank.max(0) as usize;
    let mut beta = vec![0.0; p];
    let mut var_beta = vec![0.0; p * p];
    if rk == 0 {
        return GlsEstimate {
            beta,
            sigma,
            log_lik,
            var_beta,
            rank,
            pivot,
        };
    }
    let mut factor = vec![0.0; pp1 * pp1];
    for i in 0..rk {
        let src = i * n;
        let dest = i * rk;
        factor[dest..dest + i + 1].copy_from_slice(&mat[src..src + i + 1]);
    }
    let rkm1 = rk - 1;
    let rkp1 = rk + 1;
    let nr = (n as i32) - reml * (p as i32);
    if sigma > 0.0 {
        let mut h = 0.0;
        log_lik = factor[rk * rk - 1].abs();
        if reml == 1 {
            for i in 0..rkm1 {
                h += factor[i * rkp1].abs().ln();
            }
        }
        log_lik = -(log_lik * log_lik) / (2.0 * sigma * sigma);
        log_lik -= (nr as f64) * sigma.ln();
        log_lik -= h;
    } else {
        sigma = factor[rk * rk - 1].abs();
        log_lik -= (nr as f64) * sigma.ln();
        sigma /= (nr as f64).sqrt();
        if reml == 1 {
            for i in 0..rkm1 {
                log_lik -= factor[i * rkp1].abs().ln();
            }
        }
    }
    if rkm1 > 0 {
        copy_mat(&mut var_beta, rkm1, &factor, rk, rkm1, rkm1);
        invert_upper(&mut var_beta, rkm1, rkm1);
        mult_mat(
            &mut beta,
            rkm1,
            &var_beta,
            rkm1,
            rkm1,
            rkm1,
            &factor[rkm1 * rk..],
            rk,
            1,
        );
    }
    GlsEstimate {
        beta,
        sigma,
        log_lik,
        var_beta,
        rank,
        pivot,
    }
}

fn push_estimate(out: &mut Vec<f64>, fit: &GlsEstimate) {
    out.extend_from_slice(&fit.beta);
    out.push(fit.sigma);
    out.push(fit.log_lik);
    out.extend_from_slice(&fit.var_beta);
    out.push(fit.rank as f64);
    for pivot in &fit.pivot {
        out.push(*pivot as f64);
    }
}

/// The proof case: estimated and fixed sigma, ML and REML, and a zero column.
pub fn gls_case(xy: &[f64], n: usize, p: usize) -> Vec<f64> {
    let mut out = Vec::new();
    for (reml, sigma) in [(1, 0.0), (1, 2.5), (0, 0.0)] {
        let (log_lik, l_rss) = gls_loglik(xy, n, p, reml, 0.0, 0.0, sigma);
        out.push(log_lik);
        out.push(l_rss);
    }
    for sigma in [0.0, 2.5] {
        let fit = gls_estimate(xy, n, p, 1, sigma, 0.0);
        push_estimate(&mut out, &fit);
    }
    let mut deficient = xy.to_vec();
    if n > 0 && xy.len() >= 3 * n {
        for value in &mut deficient[2 * n..3 * n] {
            *value = 0.0;
        }
    }
    let (log_lik, l_rss) = gls_loglik(&deficient, n, p, 1, 0.0, 0.0, 0.0);
    out.push(log_lik);
    out.push(l_rss);
    let fit = gls_estimate(&deficient, n, p, 1, 0.0, 0.0);
    push_estimate(&mut out, &fit);
    out
}

/// Milliseconds for one [`gls_case`], measured with [`Instant`].
pub fn gls_case_ms(xy: &[f64], n: usize, p: usize) -> f64 {
    let start = Instant::now();
    let value = gls_case(xy, n, p);
    let elapsed = start.elapsed().as_secs_f64() * 1000.0;
    std::hint::black_box(value);
    elapsed
}

#[cfg(feature = "python")]
mod python {
    use super::*;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "gls_loglik")]
    fn gls_loglik_py(
        xy: Vec<f64>,
        n: usize,
        p: usize,
        reml: i32,
        log_lik: f64,
        l_rss: f64,
        sigma: f64,
    ) -> (f64, f64) {
        gls_loglik(&xy, n, p, reml, log_lik, l_rss, sigma)
    }

    #[pyfunction]
    #[pyo3(name = "gls_estimate")]
    fn gls_estimate_py(
        xy: Vec<f64>,
        n: usize,
        p: usize,
        reml: i32,
        sigma: f64,
        log_lik: f64,
    ) -> (Vec<f64>, f64, f64, Vec<f64>, i32, Vec<i32>) {
        let fit = gls_estimate(&xy, n, p, reml, sigma, log_lik);
        (
            fit.beta,
            fit.sigma,
            fit.log_lik,
            fit.var_beta,
            fit.rank,
            fit.pivot,
        )
    }

    #[pyfunction]
    #[pyo3(name = "gls_case")]
    fn gls_case_py(xy: Vec<f64>, n: usize, p: usize) -> Vec<f64> {
        gls_case(&xy, n, p)
    }

    #[pyfunction]
    #[pyo3(name = "gls_case_ms")]
    fn gls_case_ms_py(xy: Vec<f64>, n: usize, p: usize) -> f64 {
        gls_case_ms(&xy, n, p)
    }

    #[pymodule]
    fn nlmegls(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(gls_loglik_py, m)?)?;
        m.add_function(wrap_pyfunction!(gls_estimate_py, m)?)?;
        m.add_function(wrap_pyfunction!(gls_case_py, m)?)?;
        m.add_function(wrap_pyfunction!(gls_case_ms_py, m)?)?;
        Ok(())
    }
}
