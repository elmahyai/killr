//! Correlation recalc kernels from nlme `src/corStruct.c`.
//!
//! `symm_recalc`, `nat_recalc`, `comp_symm_recalc`, and `ar1_recalc` rebuild the
//! inverse square-root factor of each group's correlation and left-multiply the
//! matching rows of column-major `Xy`. `logdet` is decreased by the log of the
//! absolute diagonal of the Cholesky factor (the same accumulation as the C
//! routines). Parameters are unconstrained, as `recalc.*` passes them.
#[link(name = "blas")]
extern "C" {
    // R's BLAS (libblas.so.3, OpenBLAS 0.3.29 on this machine), as nlmegls uses it.
    fn ddot_(
        n: *const i32,
        x: *const f64,
        incx: *const i32,
        y: *const f64,
        incy: *const i32,
    ) -> f64;
}


use std::time::Instant;

const PI: f64 = std::f64::consts::PI;

struct GroupLayout {
    n: usize,
    groups: Vec<(usize, usize)>,
}

fn group_layout(pdims: &[i32], xy_len: usize, zxcol: i32) -> Result<GroupLayout, String> {
    if pdims.len() < 4 {
        return Err("pdims needs N, M, maxLen, and sumLenSq".to_string());
    }
    if zxcol < 0 {
        return Err("ZXcol must be non-negative".to_string());
    }
    let n = usize_from_i32(pdims[0], "N")?;
    let m = usize_from_i32(pdims[1], "M")?;
    let zxcol = zxcol as usize;
    if pdims.len() < 4 + 2 * m {
        return Err("pdims is shorter than len and start".to_string());
    }
    if zxcol == 0 {
        if xy_len != 0 {
            return Err("Xy must be empty when ZXcol is 0".to_string());
        }
    } else if xy_len != n.saturating_mul(zxcol) {
        return Err(format!(
            "Xy length {xy_len} does not equal N ({n}) * ZXcol ({zxcol})"
        ));
    }
    let mut groups = Vec::with_capacity(m);
    for i in 0..m {
        let len = usize_from_i32(pdims[4 + i], "len")?;
        let start = usize_from_i32(pdims[4 + m + i], "start")?;
        if len > 0 && (start >= n || start + len > n) {
            return Err(format!(
                "group {i} rows {start}..{} fall outside N={n}",
                start + len
            ));
        }
        groups.push((start, len));
    }
    Ok(GroupLayout { n, groups })
}

fn usize_from_i32(value: i32, name: &str) -> Result<usize, String> {
    if value < 0 {
        return Err(format!("{name} must be non-negative"));
    }
    Ok(value as usize)
}

/// LINPACK `dpofa` with R's `1e-14` positive-definiteness cutoff.
/// Returns 0, or the 1-based leading minor that failed.
fn dpofa(a: &mut [f64], lda: usize, n: usize) -> i32 {
    const EPS: f64 = 1.0e-14;
    for j in 1..=n {
        let mut s = 0.0;
        let jm1 = j - 1;
        if jm1 >= 1 {
            for k in 1..=jm1 {
                let mut t = a[(k - 1) + (j - 1) * lda];
                if k > 1 {
                    // LINPACK dpofa: ddot(k-1, a(1,k), 1, a(1,j), 1). R uses the BLAS ddot,
                    // whose SIMD order a plain loop does not reproduce.
                    let len = (k - 1) as i32;
                    let inc = 1i32;
                    let dot = unsafe {
                        ddot_(
                            &len,
                            a.as_ptr().add((k - 1) * lda),
                            &inc,
                            a.as_ptr().add((j - 1) * lda),
                            &inc,
                        )
                    };
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

/// nlme `chol`: copy the upper triangle, zero the rest, then `dpofa`.
/// `info` is ignored by the recalc kernels, matching `symm_fact`.
fn chol_inplace(a: &mut [f64], n: usize) -> i32 {
    for j in 0..n {
        for i in (j + 1)..n {
            a[i + j * n] = 0.0;
        }
    }
    dpofa(a, n, n)
}

/// `dtrsl` job 11: solve `t(R) x = b` for upper-triangular `R`.
/// A zero diagonal leaves `b` unchanged and returns that 1-based index.
fn dtrsl_trans_upper(t: &[f64], ldt: usize, n: usize, b: &mut [f64]) -> i32 {
    for info in 0..n {
        if t[info + info * ldt] == 0.0 {
            return (info as i32) + 1;
        }
    }
    if n == 0 {
        return 0;
    }
    b[0] /= t[0];
    for j in 1..n {
        // LINPACK dtrsl: b(j) - ddot(j-1, t(1,j), 1, b(1), 1), with the BLAS ddot as in R.
        let len = j as i32;
        let inc = 1i32;
        let dot = unsafe { ddot_(&len, t.as_ptr().add(j * ldt), &inc, b.as_ptr(), &inc) };
        b[j] -= dot;
        b[j] /= t[j + j * ldt];
    }
    0
}

/// `mult_mat`: replace the group rows of column-major `Xy` with `factor %*% rows`.
fn apply_factor(xy: &mut [f64], n: usize, row: usize, len: usize, zxcol: usize, factor: &[f64]) {
    if len == 0 || zxcol == 0 {
        return;
    }
    let mut tmp = vec![0.0; len * zxcol];
    for col in 0..zxcol {
        let y = row + col * n;
        let dest = col * len;
        for j in 0..len {
            let scale = xy[y + j];
            let xcol = j * len;
            for r in 0..len {
                tmp[dest + r] += scale * factor[xcol + r];
            }
        }
    }
    for col in 0..zxcol {
        let z = row + col * n;
        let src = col * len;
        xy[z..z + len].copy_from_slice(&tmp[src..src + len]);
    }
}

fn symm_full_corr(pars: &[f64], max_c: usize) -> Vec<f64> {
    let npar = max_c * max_c.saturating_sub(1) / 2;
    let mut work = vec![0.0; max_c * (max_c + 1) / 2];
    let mut src = 0usize;
    let mut dest = 0usize;
    for i in 0..max_c {
        let mut aux = 1.0;
        for _j in 0..i {
            let mut aux1 = pars[src].exp();
            aux1 = PI * aux1 / (1.0 + aux1);
            work[dest] = aux * aux1.cos();
            aux *= aux1.sin();
            dest += 1;
            src += 1;
        }
        work[dest] = aux;
        dest += 1;
    }
    debug_assert_eq!(src, npar);
    let mut crr = vec![0.0; npar];
    let mut src = 0usize;
    let mut dest = 0usize;
    for i in 0..max_c.saturating_sub(1) {
        let ip1 = i + 1;
        src += i;
        let mut src1 = src;
        for j in ip1..max_c {
            src1 += j;
            let mut acc = 0.0;
            for k in 0..ip1 {
                acc += work[src + k] * work[src1 + k];
            }
            crr[dest] = acc;
            dest += 1;
        }
    }
    crr
}

fn nat_full_corr(pars: &[f64], max_c: usize) -> Vec<f64> {
    let npar = max_c * max_c.saturating_sub(1) / 2;
    let mut crr = vec![0.0; npar];
    for i in 0..npar {
        let aux = pars[i].exp();
        crr[i] = (aux - 1.0) / (aux + 1.0);
    }
    crr
}

fn pair_index(time_i: i32, time_j: i32, max_c: i32) -> Result<usize, String> {
    let n1 = time_i.min(time_j);
    let n2 = time_i + time_j - 2 * n1 - 1;
    let k = n1 * max_c - n1 * (n1 + 1) / 2 + n2;
    if k < 0 {
        return Err(format!(
            "correlation index {k} from covariate values {time_i} and {time_j}"
        ));
    }
    Ok(k as usize)
}

fn symm_mat(crr: &[f64], time: &[i32], n: usize, max_c: i32) -> Result<Vec<f64>, String> {
    let mut mat = vec![0.0; n * n];
    for i in 0..n {
        mat[i * (n + 1)] = 1.0;
        for j in (i + 1)..n {
            let k = pair_index(time[i], time[j], max_c)?;
            if k >= crr.len() {
                return Err(format!(
                    "correlation index {k} is outside the {}-vector",
                    crr.len()
                ));
            }
            let value = crr[k];
            mat[i + j * n] = value;
            mat[j + i * n] = value;
        }
    }
    Ok(mat)
}

fn symm_fact(
    crr: &[f64],
    time: &[i32],
    n: usize,
    max_c: i32,
    logdet: &mut f64,
) -> Result<Vec<f64>, String> {
    let mut mat = symm_mat(crr, time, n, max_c)?;
    let _info = chol_inplace(&mut mat, n);
    let mut inverse = vec![0.0; n * n];
    for i in 0..n {
        inverse[i * (n + 1)] = 1.0;
        let column = &mut inverse[i * n..(i + 1) * n];
        let _info = dtrsl_trans_upper(&mat, n, n, column);
        *logdet -= mat[i * (n + 1)].abs().ln();
    }
    Ok(inverse)
}

fn check_corr_inputs(
    pars: &[f64],
    time: &[i32],
    max_c: i32,
    layout: &GroupLayout,
) -> Result<usize, String> {
    if max_c < 0 {
        return Err("maxCov must be non-negative".to_string());
    }
    let max_c_usize = max_c as usize;
    let npar = max_c_usize * max_c_usize.saturating_sub(1) / 2;
    if pars.len() < npar {
        return Err(format!(
            "parameter length {} is shorter than maxCov * (maxCov - 1) / 2 = {npar}",
            pars.len()
        ));
    }
    for (start, len) in &layout.groups {
        let end = start + len;
        if end > time.len() {
            return Err(format!(
                "covariate length {} does not cover rows {start}..{end}",
                time.len()
            ));
        }
    }
    Ok(max_c_usize)
}

fn apply_corr_factor(
    xy: &mut [f64],
    layout: &GroupLayout,
    zxcol: usize,
    time: &[i32],
    crr: &[f64],
    max_c: i32,
    logdet: &mut f64,
) -> Result<(), String> {
    for &(start, len) in &layout.groups {
        let factor = symm_fact(crr, &time[start..start + len], len, max_c, logdet)?;
        apply_factor(xy, layout.n, start, len, zxcol, &factor);
    }
    Ok(())
}

/// `symm_recalc`. `pars` stay in unconstrained spherical form. Returns the updated `logdet`.
pub fn symm_recalc(
    xy: &mut [f64],
    pdims: &[i32],
    zxcol: i32,
    pars: &[f64],
    time: &[i32],
    max_c: i32,
    mut logdet: f64,
) -> Result<f64, String> {
    let layout = group_layout(pdims, xy.len(), zxcol)?;
    let max_c_usize = check_corr_inputs(pars, time, max_c, &layout)?;
    let crr = symm_full_corr(pars, max_c_usize);
    apply_corr_factor(xy, &layout, zxcol as usize, time, &crr, max_c, &mut logdet)?;
    Ok(logdet)
}

/// `nat_recalc`. `pars` stay in unconstrained natural form. Returns the updated `logdet`.
pub fn nat_recalc(
    xy: &mut [f64],
    pdims: &[i32],
    zxcol: i32,
    pars: &[f64],
    time: &[i32],
    max_c: i32,
    mut logdet: f64,
) -> Result<f64, String> {
    let layout = group_layout(pdims, xy.len(), zxcol)?;
    let max_c_usize = check_corr_inputs(pars, time, max_c, &layout)?;
    let crr = nat_full_corr(pars, max_c_usize);
    apply_corr_factor(xy, &layout, zxcol as usize, time, &crr, max_c, &mut logdet)?;
    Ok(logdet)
}

/// `(exp(x) - 1) / (exp(x) + 1)`, stable on both sides of zero (`safe_phi`).
fn safe_phi(x: f64) -> f64 {
    if x < 0.0 {
        let ex = x.exp();
        (ex - 1.0) / (ex + 1.0)
    } else {
        let ex = (-x).exp();
        (1.0 - ex) / (1.0 + ex)
    }
}

fn ar1_fact(par: f64, n: usize, logdet: &mut f64) -> Vec<f64> {
    let mut mat = vec![0.0; n * n];
    if n == 0 {
        return mat;
    }
    let aux = (1.0 - par * par).sqrt();
    let aux1 = -par / aux;
    *logdet -= (n - 1) as f64 * aux.ln();
    let diag = 1.0 / aux;
    mat[0] = 1.0;
    for i in 1..n {
        mat[i * (n + 1)] = diag;
        mat[i + n * (i - 1)] = aux1;
    }
    mat
}

/// `AR1_factList`: the group factors (column-major, concatenated) and the
/// log determinant term for the unconstrained `par`. `pdims` as in `ar1_recalc`.
pub fn ar1_fact_list(par: f64, pdims: &[i32]) -> Result<(Vec<f64>, f64), String> {
    if pdims.len() < 4 {
        return Err("pdims must hold N, M, maxLen, sumLenSq and the group lengths".to_string());
    }
    let m = usize_from_i32(pdims[1], "M")?;
    if pdims.len() < 4 + m {
        return Err("pdims is shorter than the group lengths".to_string());
    }
    let par = safe_phi(par);
    let mut logdet = 0.0;
    let mut out = Vec::new();
    for &len in &pdims[4..4 + m] {
        let len = usize_from_i32(len, "group length")?;
        out.extend(ar1_fact(par, len, &mut logdet));
    }
    Ok((out, logdet))
}

/// `AR1_recalc`. Overwrites `par` with `safe_phi(par)` and returns `(par, logdet)`.
pub fn ar1_recalc(
    xy: &mut [f64],
    pdims: &[i32],
    zxcol: i32,
    par: f64,
    mut logdet: f64,
) -> Result<(f64, f64), String> {
    let layout = group_layout(pdims, xy.len(), zxcol)?;
    let par = safe_phi(par);
    let zxcol = zxcol as usize;
    for &(start, len) in &layout.groups {
        let factor = ar1_fact(par, len, &mut logdet);
        apply_factor(xy, layout.n, start, len, zxcol, &factor);
    }
    Ok((par, logdet))
}

fn comp_symm_fact(par: f64, n: usize, logdet: &mut f64) -> Vec<f64> {
    let nsq = n * n;
    let mut work = vec![0.0; nsq];
    if n == 0 {
        return work;
    }
    let mut aux = 1.0 + (n - 1) as f64 * par;
    *logdet -= aux.ln() / 2.0;
    aux = 1.0 / (aux * n as f64).sqrt();
    let mut i = 0usize;
    while i < nsq {
        work[i] = aux;
        i += n;
    }
    aux = 1.0 - par;
    *logdet -= (n - 1) as f64 * aux.ln() / 2.0;
    for row in 1..n {
        let aux1 = -1.0 / (aux * row as f64 * (row as f64 + 1.0)).sqrt();
        for col in 0..row {
            work[row + col * n] = aux1;
        }
        work[row * (n + 1)] = -(row as f64) * aux1;
    }
    work
}

/// `compSymm_recalc`. Maps unconstrained `par` through `inf` and returns `(par, logdet)`.
pub fn comp_symm_recalc(
    xy: &mut [f64],
    pdims: &[i32],
    zxcol: i32,
    par: f64,
    inf: f64,
    mut logdet: f64,
) -> Result<(f64, f64), String> {
    let layout = group_layout(pdims, xy.len(), zxcol)?;
    let aux = par.exp();
    let par = (aux + inf) / (aux + 1.0);
    let zxcol = zxcol as usize;
    for &(start, len) in &layout.groups {
        let factor = comp_symm_fact(par, len, &mut logdet);
        apply_factor(xy, layout.n, start, len, zxcol, &factor);
    }
    Ok((par, logdet))
}

/// Milliseconds for one [`symm_recalc`] call, measured with [`std::time::Instant`].
pub fn symm_recalc_ms(
    xy: &[f64],
    pdims: &[i32],
    zxcol: i32,
    pars: &[f64],
    time: &[i32],
    max_c: i32,
    logdet: f64,
) -> Result<f64, String> {
    let mut xy = xy.to_vec();
    let started = Instant::now();
    let _logdet = symm_recalc(&mut xy, pdims, zxcol, pars, time, max_c, logdet)?;
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

/// Milliseconds for one [`nat_recalc`] call, measured with [`std::time::Instant`].
pub fn nat_recalc_ms(
    xy: &[f64],
    pdims: &[i32],
    zxcol: i32,
    pars: &[f64],
    time: &[i32],
    max_c: i32,
    logdet: f64,
) -> Result<f64, String> {
    let mut xy = xy.to_vec();
    let started = Instant::now();
    let _logdet = nat_recalc(&mut xy, pdims, zxcol, pars, time, max_c, logdet)?;
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

/// Milliseconds for one [`ar1_recalc`] call, measured with [`std::time::Instant`].
pub fn ar1_recalc_ms(
    xy: &[f64],
    pdims: &[i32],
    zxcol: i32,
    par: f64,
    logdet: f64,
) -> Result<f64, String> {
    let mut xy = xy.to_vec();
    let started = Instant::now();
    let _out = ar1_recalc(&mut xy, pdims, zxcol, par, logdet)?;
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

/// Milliseconds for one [`comp_symm_recalc`] call, measured with [`std::time::Instant`].
pub fn comp_symm_recalc_ms(
    xy: &[f64],
    pdims: &[i32],
    zxcol: i32,
    par: f64,
    inf: f64,
    logdet: f64,
) -> Result<f64, String> {
    let mut xy = xy.to_vec();
    let started = Instant::now();
    let _out = comp_symm_recalc(&mut xy, pdims, zxcol, par, inf, logdet)?;
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

/// Chol of a correlation matrix, then the inverse factor columns (`U^-T e_i`), as
/// `symm_fact`, `CAR1_fact` and `spatial_fact` do. Subtracts `log|U_ii|` from `logdet`.
fn inverse_factor(mat: &mut [f64], n: usize, logdet: &mut f64) -> Vec<f64> {
    let _info = chol_inplace(mat, n);
    let mut inverse = vec![0.0; n * n];
    for i in 0..n {
        inverse[i * (n + 1)] = 1.0;
        let column = &mut inverse[i * n..(i + 1) * n];
        let _info = dtrsl_trans_upper(mat, n, n, column);
        *logdet -= mat[i * (n + 1)].abs().ln();
    }
    inverse
}

/// `CAR1_recalc`. `par` is unconstrained; returns `(phi, logdet)` with `phi = e^par / (1 + e^par)`.
/// `time` is the concatenated covariate, indexed by the row starts in `pdims`.
pub fn car1_recalc(
    xy: &mut [f64],
    pdims: &[i32],
    zxcol: i32,
    par: f64,
    time: &[f64],
    mut logdet: f64,
) -> Result<(f64, f64), String> {
    let layout = group_layout(pdims, xy.len(), zxcol)?;
    if time.len() < layout.n {
        return Err(format!(
            "covariate length {} is shorter than N ({})",
            time.len(),
            layout.n
        ));
    }
    let aux = par.exp();
    let par = aux / (1.0 + aux);
    let zxcol = zxcol as usize;
    for &(start, len) in &layout.groups {
        let mut mat = vec![0.0; len * len];
        for i in 0..len {
            mat[i * (len + 1)] = 1.0;
            for j in (i + 1)..len {
                let value = par.powf((time[start + j] - time[start + i]).abs());
                mat[i + j * len] = value;
                mat[j + i * len] = value;
            }
        }
        let factor = inverse_factor(&mut mat, len, &mut logdet);
        apply_factor(xy, layout.n, start, len, zxcol, &factor);
    }
    Ok((par, logdet))
}

/// Spherical (1), exponential (2), Gaussian (3), linear (4) and rational (5) correlations,
/// in the order `spatial_matList` switches on.
fn spatial_corr_fn(sp_class: i32) -> Result<fn(f64) -> f64, String> {
    fn spher(val: f64) -> f64 {
        if val < 1.0 {
            1.0 - 1.5 * val + 0.5 * val.powf(3.0)
        } else {
            0.0
        }
    }
    fn expo(val: f64) -> f64 {
        (-val).exp()
    }
    fn gaus(val: f64) -> f64 {
        (-(val * val)).exp()
    }
    fn lin(val: f64) -> f64 {
        if val < 1.0 {
            1.0 - val
        } else {
            0.0
        }
    }
    fn ratio(val: f64) -> f64 {
        let val2 = val * val;
        1.0 / (1.0 + val2)
    }
    match sp_class {
        1 => Ok(spher),
        2 => Ok(expo),
        3 => Ok(gaus),
        4 => Ok(lin),
        5 => Ok(ratio),
        _ => Err("Unknown spatial correlation class".to_string()),
    }
}

/// Groups of a spatial object: `(row start, len, pair start)`. `Xy` rows advance by the
/// group length, while `pdims[4 + M + i]` (`start`) is the cumulative pair count into `dist`.
fn spatial_groups(pdims: &[i32], xy_len: usize, zxcol: i32) -> Result<(usize, Vec<(usize, usize, usize)>), String> {
    if pdims.len() < 4 {
        return Err("pdims needs N, M, spClass, and sumLenSq".to_string());
    }
    let n = usize_from_i32(pdims[0], "N")?;
    let m = usize_from_i32(pdims[1], "M")?;
    if pdims.len() < 4 + 2 * m {
        return Err("pdims is shorter than len and start".to_string());
    }
    if zxcol < 0 || (zxcol > 0 && xy_len != n * zxcol as usize) {
        return Err(format!("Xy length {xy_len} does not equal N ({n}) * ZXcol ({zxcol})"));
    }
    let mut groups = Vec::with_capacity(m);
    let mut row = 0usize;
    for i in 0..m {
        let len = usize_from_i32(pdims[4 + i], "len")?;
        let pair = usize_from_i32(pdims[4 + m + i], "start")?;
        groups.push((row, len, pair));
        row += len;
    }
    if row != n {
        return Err(format!("group lengths sum to {row}, not N ({n})"));
    }
    Ok((n, groups))
}

/// `spatial_recalc`. `par` is unconstrained: `par[0]` is the log range (shifted by `min_d` for
/// spherical and linear), and `par[1]` the logit nugget when `nugget` is set. Returns
/// `(par, logdet)` with the transformed parameters and the accumulated log determinant term.
pub fn spatial_recalc(
    xy: &mut [f64],
    pdims: &[i32],
    zxcol: i32,
    par: &[f64],
    dist: &[f64],
    min_d: f64,
    nugget: bool,
    sp_class: i32,
    mut logdet: f64,
) -> Result<(Vec<f64>, f64), String> {
    let (n, groups) = spatial_groups(pdims, xy.len(), zxcol)?;
    let corr = spatial_corr_fn(sp_class)?;
    let mut par = par.to_vec();
    if par.is_empty() || (nugget && par.len() < 2) {
        return Err("spatial parameters are shorter than the range (and nugget)".to_string());
    }
    par[0] = par[0].exp();
    if nugget {
        let aux = par[1].exp();
        par[1] = 1.0 / (1.0 + aux);
    }
    if sp_class == 1 || sp_class == 4 {
        par[0] += min_d;
    }
    let ratio = if nugget { par[1] } else { 1.0 };
    let zxcol = zxcol as usize;
    for &(row, len, pair) in &groups {
        let pairs = len * len.saturating_sub(1) / 2;
        if pair + pairs > dist.len() {
            return Err(format!(
                "distance vector of length {} does not cover pairs {pair}..{}",
                dist.len(),
                pair + pairs
            ));
        }
        let mut mat = vec![0.0; len * len];
        let mut k = pair;
        for i in 0..len {
            mat[i * (len + 1)] = 1.0;
            for j in (i + 1)..len {
                let aux = dist[k] / par[0];
                k += 1;
                let value = ratio * corr(aux);
                mat[i + j * len] = value;
                mat[j + i * len] = value;
            }
        }
        let factor = inverse_factor(&mut mat, len, &mut logdet);
        apply_factor(xy, n, row, len, zxcol, &factor);
    }
    Ok((par, logdet))
}

#[cfg(feature = "python")]
mod python {
    use super::{
        ar1_fact_list, ar1_recalc, ar1_recalc_ms, car1_recalc, comp_symm_recalc, comp_symm_recalc_ms,
        nat_recalc, nat_recalc_ms, spatial_recalc, symm_recalc, symm_recalc_ms,
    };
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "symm_recalc")]
    fn symm_recalc_py(
        mut xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        pars: Vec<f64>,
        time: Vec<i32>,
        max_c: i32,
        logdet: f64,
    ) -> PyResult<(Vec<f64>, f64)> {
        let logdet = symm_recalc(&mut xy, &pdims, zxcol, &pars, &time, max_c, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok((xy, logdet))
    }

    #[pyfunction]
    #[pyo3(name = "nat_recalc")]
    fn nat_recalc_py(
        mut xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        pars: Vec<f64>,
        time: Vec<i32>,
        max_c: i32,
        logdet: f64,
    ) -> PyResult<(Vec<f64>, f64)> {
        let logdet = nat_recalc(&mut xy, &pdims, zxcol, &pars, &time, max_c, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok((xy, logdet))
    }

    /// Returns the concatenated group factors and the log determinant term (`AR1_factList`).
    #[pyfunction]
    #[pyo3(name = "ar1_fact_list")]
    fn ar1_fact_list_py(par: f64, pdims: Vec<i32>) -> PyResult<(Vec<f64>, f64)> {
        ar1_fact_list(par, &pdims).map_err(pyo3::exceptions::PyValueError::new_err)
    }

    #[pyfunction]
    #[pyo3(name = "ar1_recalc")]
    fn ar1_recalc_py(
        mut xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        par: f64,
        logdet: f64,
    ) -> PyResult<(Vec<f64>, f64, f64)> {
        let (par, logdet) = ar1_recalc(&mut xy, &pdims, zxcol, par, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok((xy, par, logdet))
    }

    #[pyfunction]
    #[pyo3(name = "comp_symm_recalc")]
    fn comp_symm_recalc_py(
        mut xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        par: f64,
        inf: f64,
        logdet: f64,
    ) -> PyResult<(Vec<f64>, f64, f64)> {
        let (par, logdet) = comp_symm_recalc(&mut xy, &pdims, zxcol, par, inf, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok((xy, par, logdet))
    }

    /// `CAR1_recalc`: returns `(Xy, phi, logdet)`.
    #[pyfunction]
    #[pyo3(name = "car1_recalc")]
    fn car1_recalc_py(
        mut xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        par: f64,
        time: Vec<f64>,
        logdet: f64,
    ) -> PyResult<(Vec<f64>, f64, f64)> {
        let (par, logdet) = car1_recalc(&mut xy, &pdims, zxcol, par, &time, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok((xy, par, logdet))
    }

    /// `spatial_recalc`: returns `(Xy, transformed par, logdet)`. `sp_class` is 1..5 as in `Dim.corSpatial`.
    #[pyfunction]
    #[pyo3(name = "spatial_recalc")]
    fn spatial_recalc_py(
        mut xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        par: Vec<f64>,
        dist: Vec<f64>,
        min_d: f64,
        nugget: bool,
        sp_class: i32,
        logdet: f64,
    ) -> PyResult<(Vec<f64>, Vec<f64>, f64)> {
        let (par, logdet) = spatial_recalc(
            &mut xy, &pdims, zxcol, &par, &dist, min_d, nugget, sp_class, logdet,
        )
        .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok((xy, par, logdet))
    }

    #[pyfunction]
    #[pyo3(name = "symm_recalc_ms")]
    fn symm_recalc_ms_py(
        xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        pars: Vec<f64>,
        time: Vec<i32>,
        max_c: i32,
        logdet: f64,
    ) -> PyResult<f64> {
        symm_recalc_ms(&xy, &pdims, zxcol, &pars, &time, max_c, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)
    }

    #[pyfunction]
    #[pyo3(name = "nat_recalc_ms")]
    fn nat_recalc_ms_py(
        xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        pars: Vec<f64>,
        time: Vec<i32>,
        max_c: i32,
        logdet: f64,
    ) -> PyResult<f64> {
        nat_recalc_ms(&xy, &pdims, zxcol, &pars, &time, max_c, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)
    }

    #[pyfunction]
    #[pyo3(name = "ar1_recalc_ms")]
    fn ar1_recalc_ms_py(
        xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        par: f64,
        logdet: f64,
    ) -> PyResult<f64> {
        ar1_recalc_ms(&xy, &pdims, zxcol, par, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)
    }

    #[pyfunction]
    #[pyo3(name = "comp_symm_recalc_ms")]
    fn comp_symm_recalc_ms_py(
        xy: Vec<f64>,
        pdims: Vec<i32>,
        zxcol: i32,
        par: f64,
        inf: f64,
        logdet: f64,
    ) -> PyResult<f64> {
        comp_symm_recalc_ms(&xy, &pdims, zxcol, par, inf, logdet)
            .map_err(pyo3::exceptions::PyValueError::new_err)
    }

    #[pymodule]
    fn nlmerecalc(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(symm_recalc_py, m)?)?;
        m.add_function(wrap_pyfunction!(nat_recalc_py, m)?)?;
        m.add_function(wrap_pyfunction!(ar1_fact_list_py, m)?)?;
        m.add_function(wrap_pyfunction!(ar1_recalc_py, m)?)?;
        m.add_function(wrap_pyfunction!(comp_symm_recalc_py, m)?)?;
        m.add_function(wrap_pyfunction!(car1_recalc_py, m)?)?;
        m.add_function(wrap_pyfunction!(spatial_recalc_py, m)?)?;
        m.add_function(wrap_pyfunction!(symm_recalc_ms_py, m)?)?;
        m.add_function(wrap_pyfunction!(nat_recalc_ms_py, m)?)?;
        m.add_function(wrap_pyfunction!(ar1_recalc_ms_py, m)?)?;
        m.add_function(wrap_pyfunction!(comp_symm_recalc_ms_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{ar1_recalc, comp_symm_recalc, nat_recalc, symm_recalc};

    fn xy8() -> Vec<f64> {
        vec![
            0.5, -1.2, 0.3, 2.0, -0.7, 1.1, 0.0, 0.4, 1.5, 0.2, -0.4, 0.8, 3.0, -1.0, 0.6, -0.3,
        ]
    }

    fn pdims() -> Vec<i32> {
        vec![8, 3, 4, 26, 4, 1, 3, 0, 4, 5]
    }

    #[test]
    fn identity_correlations_leave_xy() {
        let original = xy8();
        let time = vec![0, 1, 2, 3, 0, 0, 1, 2];
        let mut xy = original.clone();
        let logdet = symm_recalc(&mut xy, &pdims(), 2, &[0.0; 6], &time, 4, 0.0).unwrap();
        assert!(logdet.abs() < 1e-12);
        for (got, expect) in xy.iter().zip(&original) {
            assert!((got - expect).abs() < 1e-12);
        }
        let mut xy = original.clone();
        let logdet = nat_recalc(&mut xy, &pdims(), 2, &[0.0; 6], &time, 4, 0.0).unwrap();
        assert!(logdet.abs() < 1e-12);
        for (got, expect) in xy.iter().zip(&original) {
            assert!((got - expect).abs() < 1e-12);
        }
        let mut xy = original.clone();
        let (par, logdet) = ar1_recalc(&mut xy, &pdims(), 2, 0.0, 0.0).unwrap();
        assert!(par.abs() < 1e-15);
        assert!(logdet.abs() < 1e-12);
        for (got, expect) in xy.iter().zip(&original) {
            assert!((got - expect).abs() < 1e-12);
        }
    }

    #[test]
    fn compound_symmetry_rho_half_two_by_two() {
        let mut xy = vec![1.0, 0.0];
        let (par, logdet) =
            comp_symm_recalc(&mut xy, &[2, 1, 2, 4, 2, 0], 1, 3.0_f64.ln(), -1.0, 0.0).unwrap();
        assert!((par - 0.5).abs() < 1e-12);
        let expect_log = -(1.5_f64.ln() + 0.5_f64.ln()) / 2.0;
        assert!((logdet - expect_log).abs() < 1e-12);
        let scale = 1.0 / 3.0_f64.sqrt();
        assert!((xy[0] - scale).abs() < 1e-12);
        assert!((xy[1] - (-1.0)).abs() < 1e-12);
    }
}
