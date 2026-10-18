//! LINPACK routines used by logspline, remade from `src/allpack.f`.
//!
//! The Fortran source is LINPACK (Cleve Moler and Jack Dongarra), which the
//! file header states is public domain. The routines are `XDSIFA` (symmetric
//! indefinite factorization), `XDSISL` (solve), `XDSIDI` (determinant, inverse,
//! inertia), and `XSSORT` (Singleton's quicksort). The BLAS calls they make
//! (`DAXPY`, `DDOT`, `DCOPY`, `DSWAP`, `IDAMAX`) are written inline, in the
//! loop order of the Fortran, so no external BLAS is linked.
//!
//! Matrices are column-major with leading dimension `lda`, exactly as in the
//! Fortran. Subscripts passed to the helpers are 1-based, as in the Fortran.
//! A C `double x[NC][NC]` array passed as `x` in the C source maps to the flat
//! slice `x.as_flattened_mut()` with `lda = NC`, which is the same memory.

/// Flat 0-based offset of the 1-based element `(r, c)` in a column-major matrix.
#[inline]
fn at(lda: usize, r: usize, c: usize) -> usize {
    (r - 1) + (c - 1) * lda
}

/// Reference `IDAMAX`: 1-based index of the first element of largest absolute
/// value among the `n` values starting at `a[start]` with unit stride.
fn idamax(a: &[f64], start: usize, n: usize) -> usize {
    if n < 1 {
        return 0;
    }
    let mut imax = 1;
    let mut dmax = a[start].abs();
    for i in 2..=n {
        let v = a[start + i - 1].abs();
        if v > dmax {
            imax = i;
            dmax = v;
        }
    }
    imax
}

/// Reference `DDOT` with unit stride, including its unrolled-by-five order.
fn ddot(x: &[f64], xs: usize, y: &[f64], ys: usize, n: usize) -> f64 {
    let mut dtemp = 0.0f64;
    let m = n % 5;
    for i in 0..m {
        dtemp += x[xs + i] * y[ys + i];
    }
    if n < 5 {
        return dtemp;
    }
    let mut i = m;
    while i < n {
        dtemp = dtemp
            + x[xs + i] * y[ys + i]
            + x[xs + i + 1] * y[ys + i + 1]
            + x[xs + i + 2] * y[ys + i + 2]
            + x[xs + i + 3] * y[ys + i + 3]
            + x[xs + i + 4] * y[ys + i + 4];
        i += 5;
    }
    dtemp
}

/// Reference `DAXPY` within one array: `a[ys+i] += da * a[xs+i]`.
/// The two column ranges never overlap in these routines.
fn axpy_in(a: &mut [f64], n: usize, da: f64, xs: usize, ys: usize) {
    if da == 0.0 {
        return;
    }
    for i in 0..n {
        let v = a[xs + i];
        a[ys + i] += da * v;
    }
}

/// Reference `DAXPY` from `x` into a different array `y`.
fn axpy_to(x: &[f64], xs: usize, da: f64, y: &mut [f64], ys: usize, n: usize) {
    if da == 0.0 {
        return;
    }
    for i in 0..n {
        y[ys + i] += da * x[xs + i];
    }
}

/// Reference `DSWAP` within one array between two column ranges.
fn swap_in(a: &mut [f64], n: usize, xs: usize, ys: usize) {
    for i in 0..n {
        a.swap(xs + i, ys + i);
    }
}

/// `XDSIFA`: factor a symmetric matrix by elimination with symmetric pivoting.
///
/// `a` is column-major with leading dimension `lda`. Only the upper triangle is
/// referenced. `kpvt` receives the pivot indices (1-based, negative for 2x2
/// blocks), and `info` is 0 on success or the index of a singular block.
pub fn dsifa(a: &mut [f64], lda: usize, n: usize, kpvt: &mut [i32], info: &mut i32) {
    let alpha = (1.0f64 + 17.0f64.sqrt()) / 8.0;
    *info = 0;
    let mut k = n;
    while k != 0 {
        if k == 1 {
            kpvt[0] = 1;
            if a[at(lda, 1, 1)] == 0.0 {
                *info = 1;
            }
            break;
        }
        let km1 = k - 1;
        let absakk = a[at(lda, k, k)].abs();
        let imax = idamax(a, at(lda, 1, k), k - 1);
        let colmax = a[at(lda, imax, k)].abs();
        let mut kstep;
        let mut swap;
        if absakk < alpha * colmax {
            // label 30
            let mut rowmax = 0.0f64;
            for j in (imax + 1)..=k {
                rowmax = rowmax.max(a[at(lda, imax, j)].abs());
            }
            if imax != 1 {
                let jmax = idamax(a, at(lda, 1, imax), imax - 1);
                rowmax = rowmax.max(a[at(lda, jmax, imax)].abs());
            }
            if a[at(lda, imax, imax)].abs() >= alpha * rowmax {
                kstep = 1;
                swap = true;
            } else if absakk < alpha * colmax * (colmax / rowmax) {
                // label 70
                kstep = 2;
                swap = imax != km1;
            } else {
                kstep = 1;
                swap = false;
            }
        } else {
            kstep = 1;
            swap = false;
        }
        // label 90
        if absakk.max(colmax) == 0.0 {
            kpvt[k - 1] = k as i32;
            *info = k as i32;
        } else if kstep == 1 {
            // label 100 / 120
            if swap {
                swap_in(a, imax, at(lda, 1, imax), at(lda, 1, k));
                for jj in imax..=k {
                    let j = k + imax - jj;
                    let t = a[at(lda, j, k)];
                    a[at(lda, j, k)] = a[at(lda, imax, j)];
                    a[at(lda, imax, j)] = t;
                }
            }
            for jj in 1..=km1 {
                let j = k - jj;
                let mulk = -a[at(lda, j, k)] / a[at(lda, k, k)];
                let t = mulk;
                axpy_in(a, j, t, at(lda, 1, k), at(lda, 1, j));
                a[at(lda, j, k)] = mulk;
            }
            kpvt[k - 1] = k as i32;
            if swap {
                kpvt[k - 1] = imax as i32;
            }
        } else {
            // label 140
            if swap {
                swap_in(a, imax, at(lda, 1, imax), at(lda, 1, k - 1));
                for jj in imax..=km1 {
                    let j = km1 + imax - jj;
                    let t = a[at(lda, j, k - 1)];
                    a[at(lda, j, k - 1)] = a[at(lda, imax, j)];
                    a[at(lda, imax, j)] = t;
                }
                let t = a[at(lda, k - 1, k)];
                a[at(lda, k - 1, k)] = a[at(lda, imax, k)];
                a[at(lda, imax, k)] = t;
            }
            // label 160
            let km2 = k - 2;
            if km2 != 0 {
                let ak = a[at(lda, k, k)] / a[at(lda, k - 1, k)];
                let akm1 = a[at(lda, k - 1, k - 1)] / a[at(lda, k - 1, k)];
                let denom = 1.0f64 - ak * akm1;
                for jj in 1..=km2 {
                    let j = km1 - jj;
                    let bk = a[at(lda, j, k)] / a[at(lda, k - 1, k)];
                    let bkm1 = a[at(lda, j, k - 1)] / a[at(lda, k - 1, k)];
                    let mulk = (akm1 * bk - bkm1) / denom;
                    let mulkm1 = (ak * bkm1 - bk) / denom;
                    let t = mulk;
                    axpy_in(a, j, t, at(lda, 1, k), at(lda, 1, j));
                    let t = mulkm1;
                    axpy_in(a, j, t, at(lda, 1, k - 1), at(lda, 1, j));
                    a[at(lda, j, k)] = mulk;
                    a[at(lda, j, k - 1)] = mulkm1;
                }
            }
            // label 180
            kpvt[k - 1] = 1 - k as i32;
            if swap {
                kpvt[k - 1] = -(imax as i32);
            }
            kpvt[k - 2] = kpvt[k - 1];
        }
        // label 190
        k -= kstep;
    }
}

/// `XDSISL`: solve `A x = b` after `dsifa`. `b` is overwritten with `x`.
pub fn dsisl(a: &[f64], lda: usize, n: usize, kpvt: &[i32], b: &mut [f64]) {
    let mut k = n;
    // forward elimination
    while k != 0 {
        if kpvt[k - 1] >= 0 {
            if k != 1 {
                let kp = kpvt[k - 1] as usize;
                if kp != k {
                    b.swap(k - 1, kp - 1);
                }
                axpy_to(a, at(lda, 1, k), b[k - 1], b, 0, k - 1);
            }
            b[k - 1] /= a[at(lda, k, k)];
            k -= 1;
        } else {
            if k != 2 {
                let kp = kpvt[k - 1].unsigned_abs() as usize;
                if kp != k - 1 {
                    b.swap(k - 2, kp - 1);
                }
                axpy_to(a, at(lda, 1, k), b[k - 1], b, 0, k - 2);
                axpy_to(a, at(lda, 1, k - 1), b[k - 2], b, 0, k - 2);
            }
            let ak = a[at(lda, k, k)] / a[at(lda, k - 1, k)];
            let akm1 = a[at(lda, k - 1, k - 1)] / a[at(lda, k - 1, k)];
            let bk = b[k - 1] / a[at(lda, k - 1, k)];
            let bkm1 = b[k - 2] / a[at(lda, k - 1, k)];
            let denom = ak * akm1 - 1.0f64;
            b[k - 1] = (akm1 * bk - bkm1) / denom;
            b[k - 2] = (ak * bkm1 - bk) / denom;
            k -= 2;
        }
    }
    // back substitution
    k = 1;
    while k <= n {
        if kpvt[k - 1] >= 0 {
            if k != 1 {
                b[k - 1] += ddot(a, at(lda, 1, k), b, 0, k - 1);
                let kp = kpvt[k - 1] as usize;
                if kp != k {
                    b.swap(k - 1, kp - 1);
                }
            }
            k += 1;
        } else {
            if k != 1 {
                b[k - 1] += ddot(a, at(lda, 1, k), b, 0, k - 1);
                b[k] += ddot(a, at(lda, 1, k + 1), b, 0, k - 1);
                let kp = kpvt[k - 1].unsigned_abs() as usize;
                if kp != k {
                    b.swap(k - 1, kp - 1);
                }
            }
            k += 2;
        }
    }
}

/// `XDSIDI`: determinant, inverse, and inertia from `dsifa` output.
///
/// `job` selects the parts exactly as in LINPACK: the units digit asks for the
/// inverse, the tens digit for the determinant, and the hundreds digit for the
/// inertia. `inert` is the Fortran `INERT(3)` array, so `inert[0]` is `INERT(1)`.
pub fn dsidi(
    a: &mut [f64],
    lda: usize,
    n: usize,
    kpvt: &[i32],
    det: &mut [f64; 2],
    inert: &mut [i32],
    work: &mut [f64],
    job: i32,
) {
    let noinv = job % 10 == 0;
    let nodet = (job % 100) / 10 == 0;
    let noert = (job % 1000) / 100 == 0;
    if !(nodet && noert) {
        if !noert {
            inert[0] = 0;
            inert[1] = 0;
            inert[2] = 0;
        }
        if !nodet {
            det[0] = 1.0;
            det[1] = 0.0;
        }
        let ten = 10.0f64;
        let mut t = 0.0f64;
        for k in 1..=n {
            let mut d = a[at(lda, k, k)];
            if kpvt[k - 1] <= 0 {
                if t != 0.0 {
                    d = t;
                    t = 0.0;
                } else {
                    t = a[at(lda, k, k + 1)].abs();
                    d = (d / t) * a[at(lda, k + 1, k + 1)] - t;
                }
            }
            if !noert {
                if d > 0.0 {
                    inert[0] += 1;
                }
                if d < 0.0 {
                    inert[1] += 1;
                }
                if d == 0.0 {
                    inert[2] += 1;
                }
            }
            if !nodet {
                det[0] *= d;
                if det[0] != 0.0 {
                    while det[0].abs() < 1.0 {
                        det[0] *= ten;
                        det[1] -= 1.0;
                    }
                    while det[0].abs() >= ten {
                        det[0] /= ten;
                        det[1] += 1.0;
                    }
                }
            }
        }
    }
    if noinv {
        return;
    }
    let mut k = 1usize;
    while k <= n {
        let km1 = k - 1;
        let kstep;
        if kpvt[k - 1] >= 0 {
            a[at(lda, k, k)] = 1.0 / a[at(lda, k, k)];
            if km1 >= 1 {
                for i in 0..km1 {
                    work[i] = a[at(lda, i + 1, k)];
                }
                for j in 1..=km1 {
                    let v = ddot(a, at(lda, 1, j), work, 0, j);
                    a[at(lda, j, k)] = v;
                    axpy_in(a, j - 1, work[j - 1], at(lda, 1, j), at(lda, 1, k));
                }
                let v = ddot(work, 0, a, at(lda, 1, k), km1);
                a[at(lda, k, k)] += v;
            }
            kstep = 1;
        } else {
            let t = a[at(lda, k, k + 1)].abs();
            let ak = a[at(lda, k, k)] / t;
            let akp1 = a[at(lda, k + 1, k + 1)] / t;
            let akkp1 = a[at(lda, k, k + 1)] / t;
            let d = t * (ak * akp1 - 1.0f64);
            a[at(lda, k, k)] = akp1 / d;
            a[at(lda, k + 1, k + 1)] = ak / d;
            a[at(lda, k, k + 1)] = -akkp1 / d;
            if km1 >= 1 {
                for i in 0..km1 {
                    work[i] = a[at(lda, i + 1, k + 1)];
                }
                for j in 1..=km1 {
                    let v = ddot(a, at(lda, 1, j), work, 0, j);
                    a[at(lda, j, k + 1)] = v;
                    axpy_in(a, j - 1, work[j - 1], at(lda, 1, j), at(lda, 1, k + 1));
                }
                let v = ddot(work, 0, a, at(lda, 1, k + 1), km1);
                a[at(lda, k + 1, k + 1)] += v;
                let v = ddot(a, at(lda, 1, k), a, at(lda, 1, k + 1), km1);
                a[at(lda, k, k + 1)] += v;
                for i in 0..km1 {
                    work[i] = a[at(lda, i + 1, k)];
                }
                for j in 1..=km1 {
                    let v = ddot(a, at(lda, 1, j), work, 0, j);
                    a[at(lda, j, k)] = v;
                    axpy_in(a, j - 1, work[j - 1], at(lda, 1, j), at(lda, 1, k));
                }
                let v = ddot(work, 0, a, at(lda, 1, k), km1);
                a[at(lda, k, k)] += v;
            }
            kstep = 2;
        }
        // label 220: undo the interchanges
        let ks = kpvt[k - 1].unsigned_abs() as usize;
        if ks != k {
            swap_in(a, ks, at(lda, 1, ks), at(lda, 1, k));
            for jb in ks..=k {
                let j = k + ks - jb;
                let temp = a[at(lda, j, k)];
                a[at(lda, j, k)] = a[at(lda, ks, j)];
                a[at(lda, ks, j)] = temp;
            }
            if kstep != 1 {
                let temp = a[at(lda, ks, k + 1)];
                a[at(lda, ks, k + 1)] = a[at(lda, k, k + 1)];
                a[at(lda, k, k + 1)] = temp;
            }
        }
        k += kstep;
    }
}

/// `XSSORT`: Singleton's quicksort of `x`, with `y` carried along when
/// `kflag` has absolute value 2. `kflag >= 1` sorts ascending, and a negative
/// `kflag` sorts descending. `y` may be empty when `|kflag| == 1`.
pub fn xssort(x: &mut [f64], y: &mut [f64], n: usize, kflag: i32) {
    if n < 1 {
        return;
    }
    let kk = kflag.abs();
    if kk != 1 && kk != 2 {
        return;
    }
    if kflag < 1 {
        for v in x.iter_mut().take(n) {
            *v = -*v;
        }
    }
    sort_core(x, y, n, kk == 2);
    if kflag >= 1 {
        return;
    }
    for v in x.iter_mut().take(n) {
        *v = -*v;
    }
}

/// Body of `XSSORT` after the sign flip. `paired` is true for the version that
/// also moves `y`. The labels in the comments are those of `allpack.f`.
fn sort_core(x: &mut [f64], y: &mut [f64], nn: usize, paired: bool) {
    // 1-based helpers: X(p) is x[p-1], Y(p) is y[p-1].
    let mut il = [0usize; 22];
    let mut iu = [0usize; 22];
    let mut m: usize = 1;
    let mut i: usize = 1;
    let mut j: usize = nn;
    let mut r: f64 = 0.375;
    let mut k: usize = 0;
    let mut l: usize = 0;
    let mut t: f64 = 0.0;
    let mut ij: usize = 0;
    #[derive(Clone, Copy)]
    enum St {
        L110,
        L125,
        L155,
        L160,
        L165,
    }
    let mut st = St::L110;
    let swap = |x: &mut [f64], y: &mut [f64], p: usize, q: usize| {
        x.swap(p - 1, q - 1);
        if paired {
            y.swap(p - 1, q - 1);
        }
    };
    loop {
        match st {
            St::L110 => {
                if i == j {
                    st = St::L155;
                } else {
                    if r > (0.5898437f32 as f64) {
                        r -= 0.21875;
                    } else {
                        r += 3.90625e-2;
                    }
                    st = St::L125;
                }
            }
            St::L125 => {
                k = i;
                ij = i + ((j - i) as f64 * r) as usize;
                t = x[ij - 1];
                if !(x[i - 1] <= t) {
                    swap(x, y, ij, i);
                    t = x[ij - 1];
                }
                // label 130
                l = j;
                if !(x[j - 1] >= t) {
                    swap(x, y, ij, j);
                    t = x[ij - 1];
                    if !(x[i - 1] <= t) {
                        swap(x, y, ij, i);
                        t = x[ij - 1];
                    }
                }
                // labels 140 through 135: partition loop
                loop {
                    loop {
                        l -= 1;
                        if !(x[l - 1] > t) {
                            break;
                        }
                    }
                    loop {
                        k += 1;
                        if !(x[k - 1] < t) {
                            break;
                        }
                    }
                    if k <= l {
                        swap(x, y, l, k);
                        continue;
                    }
                    break;
                }
                // labels 150, 160
                if (l as isize - i as isize) <= (j as isize - k as isize) {
                    il[m] = k;
                    iu[m] = j;
                    j = l;
                } else {
                    il[m] = i;
                    iu[m] = l;
                    i = k;
                }
                m += 1;
                st = St::L160;
            }
            St::L155 => {
                m -= 1;
                if m == 0 {
                    return;
                }
                i = il[m];
                j = iu[m];
                st = St::L160;
            }
            St::L160 => {
                if j > i {
                    st = St::L125;
                } else if i == 1 {
                    st = St::L110;
                } else {
                    i -= 1;
                    st = St::L165;
                }
            }
            St::L165 => {
                i += 1;
                if i == j {
                    st = St::L155;
                } else {
                    t = x[i];
                    if x[i - 1] <= t {
                        continue;
                    }
                    let ty = if paired { y[i] } else { 0.0 };
                    k = i;
                    // label 170: shift the larger values up and insert t, ty
                    loop {
                        x[k] = x[k - 1];
                        if paired {
                            y[k] = y[k - 1];
                        }
                        k -= 1;
                        if !(t < x[k - 1]) {
                            break;
                        }
                    }
                    x[k] = t;
                    if paired {
                        y[k] = ty;
                    }
                }
            }
        }
    }
}
