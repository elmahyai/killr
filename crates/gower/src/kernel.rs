//! Port of the numerical kernels in gower 1.0.2 `src/gower.c`.
//!
//! The R wrappers (`gower_dist`, `gower_topn`, `gower_work`) are not
//! translated. The caller supplies what the R wrapper computes: column
//! pairing (0-based, `-1` = skip), per-pair ranges, factor flags, weights.
//!
//! Each output row `k` pairs `x[k % nx]` with `y[k % ny]`, which is what the
//! C `recycle()` helper produces. Rows are independent, so the optional
//! rayon split over `k` does not change any summation order.

use rayon::prelude::*;
use rayon::ThreadPool;

/// R's `NA_INTEGER` (`INT_MIN`), used for logical, integer and factor NA.
pub const NA_INT: i32 = i32::MIN;

/// A column with R's storage semantics. Missing values are `NA_INT`
/// (integer storage), NaN (double) or `None` (character).
#[derive(Clone, Copy, Debug)]
pub enum Col<'a> {
    Lgl(&'a [i32]),
    Int(&'a [i32]),
    Dbl(&'a [f64]),
    Str(&'a [Option<String>]),
}

impl Col<'_> {
    pub fn len(&self) -> usize {
        match self {
            Col::Lgl(v) | Col::Int(v) => v.len(),
            Col::Dbl(v) => v.len(),
            Col::Str(v) => v.len(),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct KernelError(pub String);

fn err<T>(msg: impl Into<String>) -> Result<T, KernelError> {
    Err(KernelError(msg.into()))
}

/// Arguments the R wrapper passes to `.Call("R_gower", ...)`.
#[derive(Clone, Copy, Debug)]
pub struct Params<'a> {
    /// `ranges[j]`: range of the pair (x[j], y[pair[j]]).
    pub ranges: &'a [f64],
    /// `pair[j]`: 0-based index into `y`, or -1 to skip column `j`.
    pub pair: &'a [i64],
    /// `factor_pair[j]`: non-zero when `x[j]` is a factor.
    pub factor_pair: &'a [i32],
    /// Numerical zero (`eps` in R).
    pub eps: f64,
    /// `weights[j]` for column `j`.
    pub weights: &'a [f64],
}

/// Messages that R's `warning()` would have issued.
pub const WARN_SKIP_RANGE: &str = "skipping variable with zero or non-finite range.";

/// Run `contrib(k) -> (dijk, sijk)` for every row `k` and add
/// `weight*dijk*sijk` to `num[k]` and `weight*dijk` to `den[k]`.
fn accumulate<F>(
    pool: Option<&ThreadPool>,
    num: &mut [f64],
    den: &mut [f64],
    weight: f64,
    contrib: F,
) where
    F: Fn(usize) -> (f64, f64) + Sync,
{
    let step = |k: usize, n: &mut f64, d: &mut f64| {
        let (dijk, sijk) = contrib(k);
        *n += weight * dijk * sijk;
        *d += weight * dijk;
    };
    match pool {
        Some(p) => p.install(|| {
            num.par_iter_mut()
                .zip(den.par_iter_mut())
                .enumerate()
                .for_each(|(k, (n, d))| step(k, n, d));
        }),
        None => {
            for (k, (n, d)) in num.iter_mut().zip(den.iter_mut()).enumerate() {
                step(k, n, d);
            }
        }
    }
}

// Each kernel mirrors one `gower_*` function in gower.c.

fn gower_logi(x: &[i32], y: &[i32], w: f64, pool: Option<&ThreadPool>, num: &mut [f64], den: &mut [f64]) {
    let (nx, ny) = (x.len(), y.len());
    accumulate(pool, num, den, w, |k| {
        let (xi, yj) = (x[k % nx], y[k % ny]);
        let na = (xi == NA_INT) | (yj == NA_INT);
        let dijk = ((xi | yj) & ((!na) as i32)) as f64;
        let sijk = if dijk == 1.0 { xi.wrapping_mul(yj) as f64 } else { 0.0 };
        (dijk, sijk)
    });
}

fn gower_cat(x: &[i32], y: &[i32], w: f64, pool: Option<&ThreadPool>, num: &mut [f64], den: &mut [f64]) {
    let (nx, ny) = (x.len(), y.len());
    accumulate(pool, num, den, w, |k| {
        let (xi, yj) = (x[k % nx], y[k % ny]);
        let dijk = if xi == NA_INT || yj == NA_INT { 0.0 } else { 1.0 };
        let sijk = if dijk == 1.0 { (xi == yj) as i32 as f64 } else { 0.0 };
        (dijk, sijk)
    });
}

fn gower_str(x: &[Option<String>], y: &[Option<String>], w: f64, pool: Option<&ThreadPool>, num: &mut [f64], den: &mut [f64]) {
    let (nx, ny) = (x.len(), y.len());
    accumulate(pool, num, den, w, |k| {
        let (xi, yj) = (&x[k % nx], &y[k % ny]);
        let dijk = if xi.is_none() || yj.is_none() { 0.0 } else { 1.0 };
        let sijk = if dijk == 1.0 { (xi == yj) as i32 as f64 } else { 0.0 };
        (dijk, sijk)
    });
}

/// Returns false (and records a warning) when the range is unusable.
fn check_range_eps(r: f64, eps: f64, warnings: &mut Vec<&'static str>) -> bool {
    if !r.is_finite() || r < eps {
        warnings.push(WARN_SKIP_RANGE);
        return false;
    }
    true
}

fn gower_num(x: &[f64], y: &[f64], r: f64, eps: f64, w: f64, pool: Option<&ThreadPool>, num: &mut [f64], den: &mut [f64], warnings: &mut Vec<&'static str>) {
    if !check_range_eps(r, eps, warnings) {
        return;
    }
    let (nx, ny) = (x.len(), y.len());
    accumulate(pool, num, den, w, |k| {
        let (xi, yj) = (x[k % nx], y[k % ny]);
        let dijk = (xi.is_finite() & yj.is_finite()) as i32 as f64;
        let sijk = if dijk == 1.0 { 1.0 - (xi - yj).abs() / r } else { 0.0 };
        (dijk, sijk)
    });
}

fn gower_dbl_int(x: &[f64], y: &[i32], r: f64, eps: f64, w: f64, pool: Option<&ThreadPool>, num: &mut [f64], den: &mut [f64], warnings: &mut Vec<&'static str>) {
    if !check_range_eps(r, eps, warnings) {
        return;
    }
    let (nx, ny) = (x.len(), y.len());
    accumulate(pool, num, den, w, |k| {
        let (xi, yj) = (x[k % nx], y[k % ny]);
        let dijk = (xi.is_finite() & (yj != NA_INT)) as i32 as f64;
        let sijk = if dijk == 1.0 { 1.0 - (xi - yj as f64).abs() / r } else { 0.0 };
        (dijk, sijk)
    });
}

fn gower_int(x: &[i32], y: &[i32], r: f64, w: f64, pool: Option<&ThreadPool>, num: &mut [f64], den: &mut [f64], warnings: &mut Vec<&'static str>) {
    // gower_int tests R == 0, not R < eps.
    if !r.is_finite() || r == 0.0 {
        warnings.push(WARN_SKIP_RANGE);
        return;
    }
    let (nx, ny) = (x.len(), y.len());
    accumulate(pool, num, den, w, |k| {
        let (xi, yj) = (x[k % nx], y[k % ny]);
        let dijk = ((xi != NA_INT) & (yj != NA_INT)) as i32 as f64;
        let sijk = if dijk == 1.0 { 1.0 - (xi as f64 - yj as f64).abs() / r } else { 0.0 };
        (dijk, sijk)
    });
}

/// `do_gower`: fill `out[..nt]` with `1 - num/den` for `nt = max(nrow_x, nrow_y)`.
fn do_gower(
    x: &[Col],
    y: &[Col],
    p: &Params,
    pool: Option<&ThreadPool>,
    out: &mut [f64],
    warnings: &mut Vec<&'static str>,
) -> Result<(), KernelError> {
    if x.is_empty() || y.is_empty() {
        return err("x and y must have at least one column");
    }
    let nrow_x = x[0].len();
    let nrow_y = y[0].len();
    if nrow_x == 0 || nrow_y == 0 {
        return err("x and y must have at least one row");
    }
    let nt = nrow_x.max(nrow_y);
    if out.len() < nt {
        return err("output buffer too short");
    }
    let npair = p.pair.len();
    if p.ranges.len() < npair || p.weights.len() < npair || p.factor_pair.len() < npair {
        return err("ranges, factor_pair and weights must have one entry per column of x");
    }
    if npair > x.len() {
        return err("pair has more entries than x has columns");
    }

    let num = &mut out[..nt];
    num.fill(0.0);
    let mut den = vec![0.0f64; nt];

    for j in 0..npair {
        if p.pair[j] == -1 {
            continue;
        }
        if p.pair[j] < 0 || p.pair[j] as usize >= y.len() {
            return err(format!("pair[{}] is outside the columns of y", j + 1));
        }
        let yj = y[p.pair[j] as usize];
        let w = p.weights[j];
        let r = p.ranges[j];
        let (xj, eps) = (x[j], p.eps);
        match (xj, yj) {
            (Col::Lgl(xv), Col::Lgl(yv)) | (Col::Lgl(xv), Col::Int(yv)) => {
                gower_logi(xv, yv, w, pool, num, &mut den);
            }
            (Col::Lgl(_), _) => {
                return err(format!("column {} of x is logical but its pair in y is not integer storage", j + 1));
            }
            (Col::Dbl(xv), Col::Dbl(yv)) => {
                gower_num(xv, yv, r, eps, w, pool, num, &mut den, warnings);
            }
            (Col::Dbl(xv), Col::Int(yv)) => {
                gower_dbl_int(xv, yv, r, eps, w, pool, num, &mut den, warnings);
            }
            // gower.c: a double x with a logical or character y matches no branch.
            (Col::Dbl(_), _) => {}
            (Col::Int(xv), Col::Dbl(yv)) => {
                // gower.c calls gower_dbl_int with the y column first.
                gower_dbl_int(yv, xv, r, eps, w, pool, num, &mut den, warnings);
            }
            (Col::Int(xv), Col::Int(yv)) => {
                if p.factor_pair[j] != 0 {
                    gower_cat(xv, yv, w, pool, num, &mut den);
                } else {
                    gower_int(xv, yv, r, w, pool, num, &mut den, warnings);
                }
            }
            // gower.c: an integer x with a logical or character y matches no branch.
            (Col::Int(_), _) => {}
            (Col::Str(xv), Col::Str(yv)) => {
                gower_str(xv, yv, w, pool, num, &mut den);
            }
            (Col::Str(_), _) => {
                return err(format!("column {} of x is character but its pair in y is not", j + 1));
            }
        }
    }

    for (n, d) in num.iter_mut().zip(den.iter()) {
        *n = if *d == 0.0 { f64::NAN } else { 1.0 - *n / *d };
    }
    Ok(())
}

/// `push()` from gower.c: insert `(x, ind)` into the sorted top-n list.
fn push(x: f64, ind: i32, topn: &mut [f64], index: &mut [i32]) {
    let n = topn.len();
    for i in 0..n {
        if x < topn[i] || (x == topn[i] && i < n - 1) {
            if topn[i] == f64::INFINITY {
                topn[i] = x;
                index[i] = ind;
                break;
            }
            if n == 1 {
                // The C shift reads topn[-1] here; with one slot the new value simply replaces it.
                topn[0] = x;
                index[0] = ind;
                break;
            }
            topn[n - 1] = topn[n - 2];
            index[n - 1] = index[n - 2];
            let mut j = n - 2;
            while j > i {
                topn[j] = topn[j - 1];
                index[j] = index[j - 1];
                j -= 1;
            }
            topn[i] = x;
            index[i] = ind;
            break;
        }
    }
}

/// `R_gower`: Gower's distance of every record in `x` against `y`.
pub fn gower_dist(
    x: &[Col],
    y: &[Col],
    p: &Params,
    pool: Option<&ThreadPool>,
) -> Result<(Vec<f64>, Vec<&'static str>), KernelError> {
    let nt = x.first().map_or(0, |c| c.len()).max(y.first().map_or(0, |c| c.len()));
    let mut out = vec![0.0f64; nt];
    let mut warnings = Vec::new();
    do_gower(x, y, p, pool, &mut out, &mut warnings)?;
    Ok((out, warnings))
}

/// `R_gower_topn`: for each record of `x`, the `n` best matches in `y`.
///
/// Returns `(index, distance)` in the C layout: element `t` of record `i`
/// sits at `i * n + t`. `index` is 1-based, as in R.
///
/// Character columns are compared as the blank string, as in gower 1.0.2:
/// its `copyrec` writes the caller's column and copies nothing into the
/// one-row record, so the record keeps `""`. The caller's data is not modified.
pub fn gower_topn(
    x: &[Col],
    y: &[Col],
    p: &Params,
    n: usize,
    pool: Option<&ThreadPool>,
) -> Result<(Vec<i32>, Vec<f64>, Vec<&'static str>), KernelError> {
    if x.is_empty() || y.is_empty() {
        return err("x and y must have at least one column");
    }
    let ny = y[0].len();
    let nrowx = x[0].len();
    if ny == 0 || nrowx == 0 {
        return err("x and y must have at least one row");
    }
    let nout = nrowx * n;
    let mut value = vec![f64::INFINITY; nout];
    let mut index = vec![0i32; nout];
    let blank: Vec<Option<String>> = vec![Some(String::new())];
    let mut dist = vec![0.0f64; ny];
    let mut warnings = Vec::new();

    for i in 0..nrowx {
        let rec: Vec<Col> = x
            .iter()
            .map(|c| match c {
                Col::Lgl(v) => Col::Lgl(&v[i..i + 1]),
                Col::Int(v) => Col::Int(&v[i..i + 1]),
                Col::Dbl(v) => Col::Dbl(&v[i..i + 1]),
                Col::Str(_) => Col::Str(&blank),
            })
            .collect();
        do_gower(&rec, y, p, pool, &mut dist, &mut warnings)?;
        let (vals, idx) = (&mut value[i * n..(i + 1) * n], &mut index[i * n..(i + 1) * n]);
        for k in 0..ny {
            push(dist[k], (k + 1) as i32, vals, idx);
        }
    }
    Ok((index, value, warnings))
}

/// `get_xy_range` in gower.c: spread of the paired columns, with
/// R's rules for which values count (finite doubles, non-NA integers).
pub fn xy_range(x: Col, y: Col) -> f64 {
    let (x_min, x_max) = range_of(x);
    let (y_min, y_max) = range_of(y);

    let min = if x_min.is_finite() && y_min.is_finite() {
        x_min.min(y_min)
    } else if x_min.is_finite() {
        x_min
    } else if y_min.is_finite() {
        y_min
    } else {
        f64::NAN
    };

    // gower.c tests y_min in the first branch; kept as written.
    let max = if x_max.is_finite() && y_min.is_finite() {
        if x_max > y_max { x_max } else { y_max }
    } else if x_max.is_finite() && !y_max.is_finite() {
        x_max
    } else if !x_max.is_finite() && y_max.is_finite() {
        y_max
    } else {
        f64::NAN
    };

    max - min
}

/// `get_range`: (min, max) for double and integer columns. Other types
/// leave (-Inf, +Inf), as the C `switch` does.
fn range_of(c: Col) -> (f64, f64) {
    let mut lo = f64::NEG_INFINITY;
    let mut hi = f64::INFINITY;
    match c {
        Col::Dbl(v) => {
            if v.iter().any(|a| a.is_finite()) {
                let (mut mn, mut mx) = (f64::INFINITY, f64::NEG_INFINITY);
                for &a in v.iter().filter(|a| a.is_finite()) {
                    if a > mx {
                        mx = a;
                    }
                    if a < mn {
                        mn = a;
                    }
                }
                lo = mn;
                hi = mx;
            }
        }
        Col::Int(v) => {
            if v.iter().any(|&a| a != NA_INT) {
                let (mut mn, mut mx) = (i32::MAX, i32::MIN);
                for &a in v.iter().filter(|&&a| a != NA_INT) {
                    if a > mx {
                        mx = a;
                    }
                    if a < mn {
                        mn = a;
                    }
                }
                lo = mn as f64;
                hi = mx as f64;
            }
        }
        Col::Lgl(_) | Col::Str(_) => {}
    }
    (lo, hi)
}

/// Build a thread pool for `nthread > 1`; `None` runs the serial loop.
pub fn make_pool(nthread: usize) -> Result<Option<ThreadPool>, KernelError> {
    if nthread <= 1 {
        return Ok(None);
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(nthread)
        .build()
        .map(Some)
        .map_err(|e| KernelError(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn push_keeps_sorted_top_n() {
        let mut v = vec![f64::INFINITY; 3];
        let mut ix = vec![0i32; 3];
        for (k, d) in [0.5, 0.2, 0.9, 0.1, 0.2].iter().enumerate() {
            push(*d, (k + 1) as i32, &mut v, &mut ix);
        }
        assert_eq!(v, vec![0.1, 0.2, 0.2]);
        // A tie goes in front of the entry already there.
        assert_eq!(ix, vec![4, 5, 2]);
    }

    #[test]
    fn push_single_slot() {
        let mut v = vec![f64::INFINITY; 1];
        let mut ix = vec![0i32; 1];
        for (k, d) in [0.5, 0.2, 0.9].iter().enumerate() {
            push(*d, (k + 1) as i32, &mut v, &mut ix);
        }
        assert_eq!(v, vec![0.2]);
        assert_eq!(ix, vec![2]);
    }
}
