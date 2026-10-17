//! Fuzzy c-means and UFCL, ported from e1071 `src/cmeans.c`.

#[inline]
fn msub(v: &[f64], i: usize, j: usize, nr: usize) -> f64 {
    v[i + nr * j]
}

#[inline]
fn mset(v: &mut [f64], i: usize, j: usize, nr: usize, value: f64) {
    v[i + nr * j] = value;
}

fn cmeans_sign(x: f64) -> i32 {
    if x == 0.0 {
        0
    } else if x > 0.0 {
        1
    } else {
        -1
    }
}

fn cmeans_weighted_median(x: &mut [f64], w: &mut [f64]) -> f64 {
    let len = x.len();
    let mut order: Vec<usize> = (0..len).collect();
    order.sort_unstable_by(|&a, &b| x[a].total_cmp(&x[b]));
    let sorted_x: Vec<f64> = order.iter().map(|&idx| x[idx]).collect();
    x.copy_from_slice(&sorted_x);
    let permuted: Vec<f64> = order.iter().map(|&idx| w[idx]).collect();
    let sum: f64 = permuted.iter().sum();
    for (i, weight) in permuted.iter().enumerate() {
        w[i] = weight / sum;
    }

    let mut cumsum_w = 0.0;
    let mut cumsum_w_x = 0.0;
    let mut mval = f64::INFINITY;
    let mut marg = x[0];
    for i in 0..len {
        cumsum_w += w[i];
        cumsum_w_x += w[i] * x[i];
        let val = x[i] * (cumsum_w - 0.5) - cumsum_w_x;
        if val < mval {
            marg = x[i];
            mval = val;
        }
    }
    marg
}

fn ufcl_dissimilarities(
    x: &[f64],
    p: &[f64],
    nr_x: usize,
    nc: usize,
    nr_p: usize,
    dist: i32,
    ix: usize,
    d: &mut [f64],
) {
    for ip in 0..nr_p {
        let mut sum = 0.0;
        for j in 0..nc {
            let v = msub(x, ix, j, nr_x) - msub(p, ip, j, nr_p);
            if dist == 0 {
                sum += v * v;
            } else {
                sum += v.abs();
            }
        }
        mset(d, ix, ip, nr_x, sum);
    }
}

fn cmeans_dissimilarities(
    x: &[f64],
    p: &[f64],
    nr_x: usize,
    nc: usize,
    nr_p: usize,
    dist: i32,
    d: &mut [f64],
) {
    for ix in 0..nr_x {
        ufcl_dissimilarities(x, p, nr_x, nc, nr_p, dist, ix, d);
    }
}

fn ufcl_memberships(d: &[f64], nr_x: usize, nr_p: usize, exponent: f64, ix: usize, u: &mut [f64]) {
    let mut n_of_zeroes = 0usize;
    for ip in 0..nr_p {
        if msub(d, ix, ip, nr_x) == 0.0 {
            n_of_zeroes += 1;
        }
    }
    if n_of_zeroes > 0 {
        let v = 1.0 / (n_of_zeroes as f64);
        for ip in 0..nr_p {
            mset(
                u,
                ix,
                ip,
                nr_x,
                if msub(d, ix, ip, nr_x) == 0.0 {
                    v
                } else {
                    0.0
                },
            );
        }
    } else {
        let mut sum = 0.0;
        for ip in 0..nr_p {
            let v = 1.0 / msub(d, ix, ip, nr_x).powf(exponent);
            sum += v;
            mset(u, ix, ip, nr_x, v);
        }
        for ip in 0..nr_p {
            let v = msub(u, ix, ip, nr_x) / sum;
            mset(u, ix, ip, nr_x, v);
        }
    }
}

fn cmeans_memberships(d: &[f64], nr_x: usize, nr_p: usize, exponent: f64, u: &mut [f64]) {
    for ix in 0..nr_x {
        ufcl_memberships(d, nr_x, nr_p, exponent, ix, u);
    }
}

fn cmeans_prototypes(
    x: &[f64],
    u: &[f64],
    w: &[f64],
    nr_x: usize,
    nc: usize,
    nr_p: usize,
    f: f64,
    dist: i32,
    p: &mut [f64],
    dwrk_x: &mut [f64],
    dwrk_w: &mut [f64],
) {
    if dist == 0 {
        for ip in 0..nr_p {
            for j in 0..nc {
                mset(p, ip, j, nr_p, 0.0);
            }
            let mut sum = 0.0;
            for ix in 0..nr_x {
                let v = w[ix] * msub(u, ix, ip, nr_x).powf(f);
                sum += v;
                for j in 0..nc {
                    let cur = msub(p, ip, j, nr_p);
                    mset(p, ip, j, nr_p, cur + v * msub(x, ix, j, nr_x));
                }
            }
            for j in 0..nc {
                let cur = msub(p, ip, j, nr_p);
                mset(p, ip, j, nr_p, cur / sum);
            }
        }
    } else {
        for ip in 0..nr_p {
            for j in 0..nc {
                for ix in 0..nr_x {
                    dwrk_x[ix] = msub(x, ix, j, nr_x);
                    dwrk_w[ix] = w[ix] * msub(u, ix, ip, nr_x).powf(f);
                }
                let med = cmeans_weighted_median(dwrk_x, dwrk_w);
                mset(p, ip, j, nr_p, med);
            }
        }
    }
}

fn cmeans_error_fn(u: &[f64], d: &[f64], w: &[f64], nr_x: usize, nr_p: usize, f: f64) -> f64 {
    let mut sum = 0.0;
    for ix in 0..nr_x {
        for ip in 0..nr_p {
            sum += w[ix] * msub(u, ix, ip, nr_x).powf(f) * msub(d, ix, ip, nr_x);
        }
    }
    sum
}

/// Fixed-point fuzzy c-means. Matrices are column-major (R `as.double` order).
pub fn run_cmeans(
    x: &[f64],
    nr_x: usize,
    nc: usize,
    p: &mut [f64],
    nr_p: usize,
    w: &[f64],
    f: f64,
    dist: i32,
    iter_max: i32,
    reltol: f64,
    u: &mut [f64],
) -> (f64, i32) {
    let exponent = 1.0 / (f - 1.0);
    let mut d = vec![0.0; nr_x * nr_p];
    let (mut dwrk_x, mut dwrk_w) = if dist == 1 {
        (vec![0.0; nr_x], vec![0.0; nr_x])
    } else {
        (Vec::new(), Vec::new())
    };

    cmeans_dissimilarities(x, p, nr_x, nc, nr_p, dist, &mut d);
    cmeans_memberships(&d, nr_x, nr_p, exponent, u);
    let mut old_value = cmeans_error_fn(u, &d, w, nr_x, nr_p, f);
    let mut new_value = old_value;

    let mut iter = 0i32;
    while {
        iter += 1;
        iter <= iter_max
    } {
        cmeans_prototypes(
            x,
            u,
            w,
            nr_x,
            nc,
            nr_p,
            f,
            dist,
            p,
            &mut dwrk_x,
            &mut dwrk_w,
        );
        cmeans_dissimilarities(x, p, nr_x, nc, nr_p, dist, &mut d);
        cmeans_memberships(&d, nr_x, nr_p, exponent, u);
        new_value = cmeans_error_fn(u, &d, w, nr_x, nr_p, f);
        if (old_value - new_value).abs() < reltol * (old_value + reltol) {
            break;
        }
        old_value = new_value;
    }
    (new_value, iter)
}

fn ufcl_prototypes(
    x: &[f64],
    u: &[f64],
    w: &[f64],
    nr_x: usize,
    nc: usize,
    nr_p: usize,
    f: f64,
    dist: i32,
    lrate: f64,
    ix: usize,
    p: &mut [f64],
) {
    for ip in 0..nr_p {
        for j in 0..nc {
            let mut grad = msub(x, ix, j, nr_x) - msub(p, ip, j, nr_p);
            if dist == 1 {
                grad = cmeans_sign(grad) as f64;
            }
            let cur = msub(p, ip, j, nr_p);
            mset(
                p,
                ip,
                j,
                nr_p,
                cur + lrate * w[ix] * msub(u, ix, ip, nr_x).powf(f) * grad,
            );
        }
    }
}

/// On-line fuzzy competitive learning (UFCL).
pub fn run_ufcl(
    x: &[f64],
    nr_x: usize,
    nc: usize,
    p: &mut [f64],
    nr_p: usize,
    w: &[f64],
    f: f64,
    dist: i32,
    iter_max: i32,
    reltol: f64,
    rate_par: f64,
    u: &mut [f64],
) -> (f64, i32) {
    let exponent = 1.0 / (f - 1.0);
    let mut d = vec![0.0; nr_x * nr_p];

    cmeans_dissimilarities(x, p, nr_x, nc, nr_p, dist, &mut d);
    cmeans_memberships(&d, nr_x, nr_p, exponent, u);
    let mut old_value = cmeans_error_fn(u, &d, w, nr_x, nr_p, f);
    let mut new_value = old_value;

    let mut iter = 0i32;
    while {
        iter += 1;
        iter <= iter_max
    } {
        let lrate = rate_par * (1.0 - (iter as f64) / (iter_max as f64));
        for ix in 0..nr_x {
            ufcl_dissimilarities(x, p, nr_x, nc, nr_p, dist, ix, &mut d);
            ufcl_memberships(&d, nr_x, nr_p, exponent, ix, u);
            ufcl_prototypes(x, u, w, nr_x, nc, nr_p, f, dist, lrate, ix, p);
        }
        new_value = cmeans_error_fn(u, &d, w, nr_x, nr_p, f);
        if (old_value - new_value).abs() < reltol * (old_value + reltol) {
            break;
        }
        old_value = new_value;
    }
    (new_value, iter)
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{run_cmeans, run_ufcl};

    fn owned_f64(array: &PyReadonlyArray1<'_, f64>) -> PyResult<Vec<f64>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    #[pyfunction]
    #[pyo3(name = "cmeans", signature = (x, centers, weights, m=2.0, dist=0, iter_max=100, reltol=1.49e-8, ufcl=false, rate_par=0.3))]
    fn cmeans_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        centers: PyReadonlyArray1<'py, f64>,
        weights: PyReadonlyArray1<'py, f64>,
        m: f64,
        dist: i32,
        iter_max: i32,
        reltol: f64,
        ufcl: bool,
        rate_par: f64,
    ) -> PyResult<(
        Bound<'py, numpy::PyArray1<f64>>,
        Bound<'py, numpy::PyArray1<f64>>,
        f64,
        i32,
    )> {
        let x = owned_f64(&x)?;
        let mut p = owned_f64(&centers)?;
        let w = owned_f64(&weights)?;
        let nr_x = w.len();
        if x.len() % nr_x != 0 {
            return Err(PyValueError::new_err(
                "length of 'x' must be a multiple of length of 'weights'",
            ));
        }
        let nc = x.len() / nr_x;
        let nr_p = if p.len() % nc != 0 {
            return Err(PyValueError::new_err(
                "length of 'centers' must be a multiple of ncol(x)",
            ));
        } else {
            p.len() / nc
        };
        let mut u = vec![0.0; nr_x * nr_p];
        let (ermin, iter) = if ufcl {
            run_ufcl(
                &x, nr_x, nc, &mut p, nr_p, &w, m, dist, iter_max, reltol, rate_par, &mut u,
            )
        } else {
            run_cmeans(
                &x, nr_x, nc, &mut p, nr_p, &w, m, dist, iter_max, reltol, &mut u,
            )
        };
        Ok((
            p.into_pyarray(py),
            u.into_pyarray(py),
            ermin,
            iter,
        ))
    }

    #[pymodule]
    fn cmeans(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(cmeans_py, m)?)?;
        Ok(())
    }
}
