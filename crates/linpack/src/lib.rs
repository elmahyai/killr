//! LINPACK routines used by KernSmooth.
//!
//! `dgefa` and `dgesl` are ported from `src/dgefa.f` and `src/dgesl.f`.
//! `dgedi` is ported from `src/dgedi.f`. `dqrdc` and `dqrsl` are the R LINPACK
//! routines that `blkest` and `cp` call; KernSmooth does not ship those two
//! files. Matrices are column-major, with leading dimension `lda`, matching
//! Fortran. Pivot indices stored here are zero-based. KernSmooth calls `dgesl`
//! with `job = 0`. In that file the `A x = b` steps sit inside `if (job .ne. 0)`,
//! so a zero job runs the transpose steps. `locpol` builds a symmetric moment
//! matrix, and this follows the Fortran as written.

/// Factor `a` by Gaussian elimination with partial pivoting.
///
/// Returns `info`: `0` on success, or `k` (one-based) when `u(k, k)` is zero.
pub fn dgefa(a: &mut [f64], lda: usize, n: usize, ipvt: &mut [usize]) -> i32 {
    let mut info = 0;
    if n == 0 {
        return info;
    }
    let nm1 = n - 1;
    if nm1 >= 1 {
        for k in 0..nm1 {
            let column = col_offset(lda, k) + k;
            let pivot = idamax(&a[column..column + (n - k)]) + k;
            ipvt[k] = pivot;
            if a[at(lda, pivot, k)] == 0.0 {
                info = (k as i32) + 1;
                continue;
            }
            if pivot != k {
                swap(a, lda, pivot, k, k, k);
            }
            let scale = -1.0 / a[at(lda, k, k)];
            let below = n - k - 1;
            dscal(below, scale, a, at(lda, k + 1, k));
            for j in (k + 1)..n {
                let t = a[at(lda, pivot, j)];
                if pivot != k {
                    a[at(lda, pivot, j)] = a[at(lda, k, j)];
                    a[at(lda, k, j)] = t;
                }
                daxpy(below, t, a, at(lda, k + 1, k), at(lda, k + 1, j));
            }
        }
    }
    ipvt[n - 1] = n - 1;
    if a[at(lda, n - 1, n - 1)] == 0.0 {
        info = n as i32;
    }
    info
}

/// Solve a system from the factors produced by [`dgefa`].
///
/// `job != 0` solves `A x = b`. `job == 0` solves `Aᵀ x = b`, which is the
/// branch KernSmooth takes.
pub fn dgesl(a: &[f64], lda: usize, n: usize, ipvt: &[usize], b: &mut [f64], job: i32) {
    if n == 0 {
        return;
    }
    if job != 0 {
        solve_ax(a, lda, n, ipvt, b);
        return;
    }
    solve_atx(a, lda, n, ipvt, b);
}

fn solve_ax(a: &[f64], lda: usize, n: usize, ipvt: &[usize], b: &mut [f64]) {
    let nm1 = n - 1;
    if nm1 >= 1 {
        for k in 0..nm1 {
            let pivot = ipvt[k];
            let t = b[pivot];
            if pivot != k {
                b[pivot] = b[k];
                b[k] = t;
            }
            daxpy_ref(n - k - 1, t, a, at(lda, k + 1, k), b, k + 1);
        }
    }
    for kb in 0..n {
        let k = n - 1 - kb;
        b[k] /= a[at(lda, k, k)];
        let t = -b[k];
        daxpy_ref(k, t, a, at(lda, 0, k), b, 0);
    }
}

fn solve_atx(a: &[f64], lda: usize, n: usize, ipvt: &[usize], b: &mut [f64]) {
    for k in 0..n {
        let t = ddot(k, a, at(lda, 0, k), b, 0);
        b[k] = (b[k] - t) / a[at(lda, k, k)];
    }
    if n < 2 {
        return;
    }
    for kb in 0..(n - 1) {
        let k = n - 2 - kb;
        b[k] += ddot(n - 1 - k, a, at(lda, k + 1, k), b, k + 1);
        let pivot = ipvt[k];
        if pivot != k {
            let t = b[pivot];
            b[pivot] = b[k];
            b[k] = t;
        }
    }
}

fn at(lda: usize, row: usize, col: usize) -> usize {
    col_offset(lda, col) + row
}

fn col_offset(lda: usize, col: usize) -> usize {
    col * lda
}

fn swap(a: &mut [f64], lda: usize, row_a: usize, col_a: usize, row_b: usize, col_b: usize) {
    let left = at(lda, row_a, col_a);
    let right = at(lda, row_b, col_b);
    let t = a[left];
    a[left] = a[right];
    a[right] = t;
}

fn idamax(values: &[f64]) -> usize {
    let mut best = 0;
    let mut max_abs = values.first().copied().unwrap_or(0.0).abs();
    for (index, value) in values.iter().enumerate().skip(1) {
        let magnitude = value.abs();
        if magnitude > max_abs {
            best = index;
            max_abs = magnitude;
        }
    }
    best
}

fn dscal(n: usize, factor: f64, values: &mut [f64], start: usize) {
    for value in &mut values[start..start + n] {
        *value *= factor;
    }
}

fn daxpy(n: usize, factor: f64, values: &mut [f64], x: usize, y: usize) {
    if n == 0 || factor == 0.0 {
        return;
    }
    let mut copied = vec![0.0; n];
    copied.copy_from_slice(&values[x..x + n]);
    for (offset, term) in copied.iter().enumerate() {
        values[y + offset] += factor * term;
    }
}

fn daxpy_ref(n: usize, factor: f64, a: &[f64], x: usize, b: &mut [f64], y: usize) {
    if n == 0 || factor == 0.0 {
        return;
    }
    for offset in 0..n {
        b[y + offset] += factor * a[x + offset];
    }
}

fn ddot(n: usize, a: &[f64], x: usize, b: &[f64], y: usize) -> f64 {
    let mut total = 0.0;
    for offset in 0..n {
        total += a[x + offset] * b[y + offset];
    }
    total
}

/// Determinant and inverse from the factors produced by [`dgefa`].
///
/// `job` follows LINPACK: the tens digit requests the determinant and the ones
/// digit requests the inverse. KernSmooth calls this with `job = 1`, inverse
/// only. Pivot indices are zero-based, matching [`dgefa`]. Returns
/// `(det[0], det[1])` when the determinant was requested, and `(0, 0)`
/// otherwise. The determinant is `det[0] * 10^det[1]`.
pub fn dgedi(a: &mut [f64], lda: usize, n: usize, ipvt: &[usize], job: i32) -> (f64, f64) {
    if n == 0 {
        if job / 10 != 0 {
            return (1.0, 0.0);
        }
        return (0.0, 0.0);
    }
    let mut det1 = 0.0;
    let mut det2 = 0.0;
    if job / 10 != 0 {
        det1 = 1.0;
        let ten = 10.0;
        for i in 0..n {
            if ipvt[i] != i {
                det1 = -det1;
            }
            det1 *= a[at(lda, i, i)];
            if det1 == 0.0 {
                break;
            }
            while det1.abs() < 1.0 {
                det1 *= ten;
                det2 -= 1.0;
            }
            while det1.abs() >= ten {
                det1 /= ten;
                det2 += 1.0;
            }
        }
    }
    if job % 10 == 0 {
        return (det1, det2);
    }

    for k in 0..n {
        let diagonal = at(lda, k, k);
        a[diagonal] = 1.0 / a[diagonal];
        let scale = -a[diagonal];
        dscal(k, scale, a, at(lda, 0, k));
        for j in (k + 1)..n {
            let above = at(lda, k, j);
            let t = a[above];
            a[above] = 0.0;
            daxpy(k + 1, t, a, at(lda, 0, k), at(lda, 0, j));
        }
    }
    if n >= 2 {
        let mut work = vec![0.0; n];
        for k in (0..n - 1).rev() {
            for i in (k + 1)..n {
                work[i] = a[at(lda, i, k)];
                a[at(lda, i, k)] = 0.0;
            }
            for j in (k + 1)..n {
                let t = work[j];
                daxpy(n, t, a, at(lda, 0, j), at(lda, 0, k));
            }
            let pivot = ipvt[k];
            if pivot != k {
                dswap(n, a, at(lda, 0, k), at(lda, 0, pivot));
            }
        }
    }
    (det1, det2)
}

/// Householder QR, ported from R's LINPACK `dqrdc`.
///
/// `job == 0` does not pivot and does not read `jpvt` or `work`. Column
/// indices stored in `jpvt` stay one-based, as in the Fortran routine.
pub fn dqrdc(
    x: &mut [f64],
    ldx: usize,
    n: usize,
    p: usize,
    qraux: &mut [f64],
    jpvt: &mut [i32],
    work: &mut [f64],
    job: i32,
) {
    let mut pl = 1_usize;
    let mut pu = 0_usize;
    if job != 0 {
        for j in 1..=p {
            let original = jpvt[j - 1];
            let swapj = original > 0;
            let negj = original < 0;
            jpvt[j - 1] = j as i32;
            if negj {
                jpvt[j - 1] = -(j as i32);
            }
            if !swapj {
                continue;
            }
            if j != pl {
                dswap(n, x, fort(ldx, 1, pl), fort(ldx, 1, j));
            }
            jpvt[j - 1] = jpvt[pl - 1];
            jpvt[pl - 1] = j as i32;
            pl += 1;
        }
        pu = p;
        for jj in 1..=p {
            let j = p - jj + 1;
            if jpvt[j - 1] >= 0 {
                continue;
            }
            jpvt[j - 1] = -jpvt[j - 1];
            if j != pu {
                dswap(n, x, fort(ldx, 1, pu), fort(ldx, 1, j));
                let swapped = jpvt[pu - 1];
                jpvt[pu - 1] = jpvt[j - 1];
                jpvt[j - 1] = swapped;
            }
            pu -= 1;
        }
    }
    if pu >= pl {
        for j in pl..=pu {
            let norm = dnrm2(x, fort(ldx, 1, j), n);
            qraux[j - 1] = norm;
            work[j - 1] = norm;
        }
    }

    let lup = n.min(p);
    for l in 1..=lup {
        if l >= pl && l < pu {
            let mut max_norm = 0.0;
            let mut maxj = l;
            for j in l..=pu {
                if qraux[j - 1] > max_norm {
                    max_norm = qraux[j - 1];
                    maxj = j;
                }
            }
            if maxj != l {
                dswap(n, x, fort(ldx, 1, l), fort(ldx, 1, maxj));
                qraux[maxj - 1] = qraux[l - 1];
                work[maxj - 1] = work[l - 1];
                let swapped = jpvt[maxj - 1];
                jpvt[maxj - 1] = jpvt[l - 1];
                jpvt[l - 1] = swapped;
            }
        }
        qraux[l - 1] = 0.0;
        if l == n {
            continue;
        }
        let length = n - l + 1;
        let diag = fort(ldx, l, l);
        let mut nrmxl = dnrm2(x, diag, length);
        if nrmxl == 0.0 {
            continue;
        }
        if x[diag] != 0.0 {
            nrmxl = dsign(nrmxl, x[diag]);
        }
        dscal(length, 1.0 / nrmxl, x, diag);
        x[diag] = 1.0 + x[diag];
        if p >= l + 1 {
            for j in (l + 1)..=p {
                let column = fort(ldx, l, j);
                let t = -ddot(length, x, diag, x, column) / x[diag];
                daxpy(length, t, x, diag, column);
                if j >= pl && j <= pu && qraux[j - 1] != 0.0 {
                    let entry = x[fort(ldx, l, j)].abs();
                    let mut tt = 1.0 - (entry / qraux[j - 1]).powi(2);
                    if tt < 0.0 {
                        tt = 0.0;
                    }
                    let saved = tt;
                    tt = 1.0 + 0.05 * tt * (qraux[j - 1] / work[j - 1]).powi(2);
                    if tt == 1.0 {
                        qraux[j - 1] = dnrm2(x, fort(ldx, l + 1, j), n - l);
                        work[j - 1] = qraux[j - 1];
                    } else {
                        qraux[j - 1] *= saved.sqrt();
                    }
                }
            }
        }
        qraux[l - 1] = x[diag];
        x[diag] = -nrmxl;
    }
}

/// Apply a QR factorization from [`dqrdc`].
///
/// `job` is the LINPACK decimal code. `100` computes the least-squares
/// coefficient vector, which is what `blkest` and `cp` request. Returns
/// `info`: `0`, or the one-based index of the first zero diagonal when the
/// triangular factor is singular.
pub fn dqrsl(
    x: &mut [f64],
    ldx: usize,
    n: usize,
    k: usize,
    qraux: &[f64],
    y: &[f64],
    qy: &mut [f64],
    qty: &mut [f64],
    b: &mut [f64],
    rsd: &mut [f64],
    xb: &mut [f64],
    job: i32,
) -> i32 {
    let cqy = job / 10_000 != 0;
    let cqty = job % 10_000 != 0;
    let cb = (job % 1000) / 100 != 0;
    let cr = (job % 100) / 10 != 0;
    let cxb = job % 10 != 0;
    if n == 0 {
        return 0;
    }
    let ju = k.min(n - 1);
    if ju == 0 {
        return dqrsl_single(x, ldx, y, qy, qty, b, rsd, xb, cqy, cqty, cb, cr, cxb);
    }
    if cqy {
        qy[..n].copy_from_slice(&y[..n]);
    }
    if cqty {
        qty[..n].copy_from_slice(&y[..n]);
    }
    if cqy {
        for jj in 1..=ju {
            apply_reflector(x, ldx, n, ju - jj + 1, qraux, qy);
        }
    }
    if cqty {
        for j in 1..=ju {
            apply_reflector(x, ldx, n, j, qraux, qty);
        }
    }
    if cb {
        b[..k].copy_from_slice(&qty[..k]);
    }
    if cxb {
        xb[..k].copy_from_slice(&qty[..k]);
        for value in xb.iter_mut().take(n).skip(k) {
            *value = 0.0;
        }
    }
    if cr && k < n {
        rsd[k..n].copy_from_slice(&qty[k..n]);
    }
    if cr {
        for value in rsd.iter_mut().take(k) {
            *value = 0.0;
        }
    }
    let mut info = 0;
    if cb {
        for jj in 1..=k {
            let j = k - jj + 1;
            let diag = fort(ldx, j, j);
            if x[diag] == 0.0 {
                info = j as i32;
                break;
            }
            b[j - 1] /= x[diag];
            if j != 1 {
                daxpy_ref(j - 1, -b[j - 1], x, fort(ldx, 1, j), b, 0);
            }
        }
    }
    if cr || cxb {
        for jj in 1..=ju {
            let j = ju - jj + 1;
            if qraux[j - 1] == 0.0 {
                continue;
            }
            let diag = fort(ldx, j, j);
            let temp = x[diag];
            x[diag] = qraux[j - 1];
            let length = n - j + 1;
            if cr {
                let t = -ddot(length, x, diag, rsd, j - 1) / x[diag];
                daxpy_ref(length, t, x, diag, rsd, j - 1);
            }
            if cxb {
                let t = -ddot(length, x, diag, xb, j - 1) / x[diag];
                daxpy_ref(length, t, x, diag, xb, j - 1);
            }
            x[diag] = temp;
        }
    }
    info
}

fn dqrsl_single(
    x: &mut [f64],
    ldx: usize,
    y: &[f64],
    qy: &mut [f64],
    qty: &mut [f64],
    b: &mut [f64],
    rsd: &mut [f64],
    xb: &mut [f64],
    cqy: bool,
    cqty: bool,
    cb: bool,
    cr: bool,
    cxb: bool,
) -> i32 {
    if cqy {
        qy[0] = y[0];
    }
    if cqty {
        qty[0] = y[0];
    }
    if cxb {
        xb[0] = y[0];
    }
    let mut info = 0;
    if cb {
        let diag = x[fort(ldx, 1, 1)];
        if diag == 0.0 {
            info = 1;
        } else {
            b[0] = y[0] / diag;
        }
    }
    if cr {
        rsd[0] = 0.0;
    }
    info
}

fn apply_reflector(
    x: &mut [f64],
    ldx: usize,
    n: usize,
    j: usize,
    qraux: &[f64],
    target: &mut [f64],
) {
    if qraux[j - 1] == 0.0 {
        return;
    }
    let diag = fort(ldx, j, j);
    let temp = x[diag];
    x[diag] = qraux[j - 1];
    let length = n - j + 1;
    let t = -ddot(length, x, diag, target, j - 1) / x[diag];
    daxpy_ref(length, t, x, diag, target, j - 1);
    x[diag] = temp;
}

fn fort(ldx: usize, row: usize, col: usize) -> usize {
    (col - 1) * ldx + (row - 1)
}

fn dswap(n: usize, values: &mut [f64], x: usize, y: usize) {
    if x == y {
        return;
    }
    for offset in 0..n {
        let left = x + offset;
        let right = y + offset;
        let t = values[left];
        values[left] = values[right];
        values[right] = t;
    }
}

fn dnrm2(values: &[f64], start: usize, n: usize) -> f64 {
    if n < 1 {
        return 0.0;
    }
    if n == 1 {
        return values[start].abs();
    }
    let mut scale = 0.0;
    let mut ssq = 1.0;
    for value in &values[start..start + n] {
        if *value != 0.0 {
            let absxi = value.abs();
            if scale < absxi {
                let ratio = scale / absxi;
                ssq = 1.0 + ssq * ratio * ratio;
                scale = absxi;
            } else {
                let ratio = absxi / scale;
                ssq += ratio * ratio;
            }
        }
    }
    scale * ssq.sqrt()
}

fn dsign(magnitude: f64, sign_source: f64) -> f64 {
    if sign_source >= 0.0 {
        magnitude.abs()
    } else {
        -magnitude.abs()
    }
}

#[cfg(test)]
mod tests {
    use super::{dgefa, dgedi, dgesl, dqrdc, dqrsl};

    #[test]
    fn solves_a_two_by_two_system() {
        let mut matrix = vec![1.0, 3.0, 2.0, 4.0];
        let mut pivots = [0, 0];
        let info = dgefa(&mut matrix, 2, 2, &mut pivots);
        assert_eq!(info, 0);
        let mut right = vec![5.0, 11.0];
        dgesl(&matrix, 2, 2, &pivots, &mut right, 1);
        assert!((right[0] - 1.0).abs() < 1e-12);
        assert!((right[1] - 2.0).abs() < 1e-12);
    }

    #[test]
    fn job_zero_solves_the_transpose() {
        let mut matrix = vec![1.0, 3.0, 2.0, 4.0];
        let mut pivots = [0, 0];
        dgefa(&mut matrix, 2, 2, &mut pivots);
        let mut right = vec![7.0, 10.0];
        dgesl(&matrix, 2, 2, &pivots, &mut right, 0);
        assert!((right[0] - 1.0).abs() < 1e-12);
        assert!((right[1] - 2.0).abs() < 1e-12);
    }

    #[test]
    fn dgedi_inverts_the_factored_matrix() {
        let original = vec![1.0, 3.0, 2.0, 4.0];
        let mut matrix = original.clone();
        let mut pivots = [0, 0];
        let info = dgefa(&mut matrix, 2, 2, &mut pivots);
        assert_eq!(info, 0);
        dgedi(&mut matrix, 2, 2, &pivots, 1);
        let mut product = [0.0; 4];
        for col in 0..2 {
            for row in 0..2 {
                for k in 0..2 {
                    product[col * 2 + row] += original[k * 2 + row] * matrix[col * 2 + k];
                }
            }
        }
        assert!((product[0] - 1.0).abs() < 1e-12);
        assert!(product[1].abs() < 1e-12);
        assert!(product[2].abs() < 1e-12);
        assert!((product[3] - 1.0).abs() < 1e-12);
    }

    #[test]
    fn least_squares_fit_recovers_a_line() {
        let mut matrix = vec![1.0, 1.0, 1.0, 0.0, 1.0, 2.0];
        let mut qraux = [0.0; 2];
        let mut pivots = [];
        let mut work = [];
        dqrdc(&mut matrix, 3, 3, 2, &mut qraux, &mut pivots, &mut work, 0);
        let y = [1.0, 3.0, 5.0];
        let mut qty = [0.0; 3];
        let mut coef = [0.0; 2];
        let mut unused = [];
        let info = dqrsl(
            &mut matrix,
            3,
            3,
            2,
            &qraux,
            &y,
            &mut unused,
            &mut qty,
            &mut coef,
            &mut [],
            &mut [],
            100,
        );
        assert_eq!(info, 0);
        assert!((coef[0] - 1.0).abs() < 1e-12);
        assert!((coef[1] - 2.0).abs() < 1e-12);
    }
}
