//! Generalized nonlinear least squares from nlme `src/gnls.c` (`fit_gnls`).
//!
//! The Gauss–Newton loop calls a model with the current coefficient vector.
//! The model returns a column-major `N` by `npar + 1` matrix whose last column
//! is the residual and whose other columns are the working gradient. Variance
//! weights and `corStruct_recalc` are applied inside the objective, matching
//! the C routine. `settings[3]` is the convergence code, `settings[4]` is the
//! iteration count, and `settings[5]` is the weighted residual sum of squares.
//! The Gauss–Newton step is left in pivoted column order, as `QRsolve` does.

use std::time::Instant;

#[cfg(feature = "python")]
use pyo3::prelude::*;

fn dnrm2(x: &[f64], start: usize, n: usize) -> f64 {
    if n == 0 {
        return 0.0;
    }
    if n == 1 {
        return x[start].abs();
    }
    let mut scale = 0.0;
    let mut ssq = 1.0;
    for k in 0..n {
        let value = x[start + k];
        if value != 0.0 {
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
    let mut acc = 0.0;
    for k in 0..n {
        acc += x[x0 + k] * y[y0 + k];
    }
    acc
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

/// Rank-revealing QR from R `dqrdc2`, with nlme's zero-based pivot labels.
fn dqrdc2(
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
                        for k_idx in 0..length {
                            x[column + k_idx] += t * x[diag + k_idx];
                        }
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
    (k - 1).min(n as i32)
}

/// `dqrsl` job 1000: replace `y` with `Q'y`. Restores the R diagonal.
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
        let mut dot = 0.0;
        for i in 0..(n - j + 1) {
            dot += x[(j0 + i) + j0 * ldx] * y[j0 + i];
        }
        let t = -dot / x[j0 + j0 * ldx];
        for i in 0..(n - j + 1) {
            y[j0 + i] += t * x[(j0 + i) + j0 * ldx];
        }
        x[j0 + j0 * ldx] = temp;
    }
}

/// `QRsolve`: least-squares coefficients in pivoted column order.
fn qr_solve(mat: &mut [f64], ld: usize, nrow: usize, ncol: usize, qraux: &[f64], y: &[f64], beta: &mut [f64]) {
    let mut qty = y[..nrow].to_vec();
    dqrsl_qty(mat, ld, nrow, ncol, qraux, &mut qty);
    let mut b = qty[..ncol].to_vec();
    for jj in 1..=ncol {
        let j = ncol - jj + 1;
        let j0 = j - 1;
        if mat[j0 + j0 * ld] == 0.0 {
            break;
        }
        b[j0] /= mat[j0 + j0 * ld];
        if j != 1 {
            let t = -b[j0];
            for i in 0..j0 {
                b[i] += t * mat[i + j0 * ld];
            }
        }
    }
    beta[..ncol].copy_from_slice(&b);
}

/// Left-multiply the first `len` rows of each column by a column-major factor.
fn apply_group(xy: &mut [f64], n: usize, row: usize, len: usize, zxcol: usize, factor: &[f64]) {
    if len == 0 || zxcol == 0 {
        return;
    }
    let mut tmp = vec![0.0; len * zxcol];
    for col in 0..zxcol {
        let ycol = row + col * n;
        for j in 0..len {
            let scale = xy[ycol + j];
            let fcol = j * len;
            for r in 0..len {
                tmp[col * len + r] += scale * factor[fcol + r];
            }
        }
    }
    for col in 0..zxcol {
        let ycol = row + col * n;
        xy[ycol..ycol + len].copy_from_slice(&tmp[col * len..(col + 1) * len]);
    }
}

/// `corStruct_recalc`: left-multiply each packed group by its factor.
fn cor_struct_recalc(xy: &mut [f64], pdims: &[i32], zxcol: usize, factor: &[f64]) -> Result<(), String> {
    if pdims.len() < 2 {
        return Err("corDims needs N and M".to_string());
    }
    let n = usize_from_i32(pdims[0], "N")?;
    let m = usize_from_i32(pdims[1], "M")?;
    if pdims.len() < 4 + m {
        return Err("corDims is shorter than the group lengths".to_string());
    }
    if zxcol > 0 && xy.len() < n.saturating_mul(zxcol) {
        return Err("model matrix is shorter than N * columns".to_string());
    }
    let mut row = 0usize;
    let mut factor_at = 0usize;
    for i in 0..m {
        let len = usize_from_i32(pdims[4 + i], "len")?;
        let need = len.saturating_mul(len);
        if factor_at + need > factor.len() {
            return Err("corFactor is shorter than the group factors".to_string());
        }
        if len > 0 && row + len > n {
            return Err("correlation groups run past N".to_string());
        }
        if len > 0 && zxcol > 0 {
            apply_group(xy, n, row, len, zxcol, &factor[factor_at..]);
        }
        row += len;
        factor_at += need;
    }
    Ok(())
}

fn usize_from_i32(value: i32, name: &str) -> Result<usize, String> {
    if value < 0 {
        return Err(format!("{name} must be non-negative"));
    }
    Ok(value as usize)
}

fn apply_objective(
    result: &mut [f64],
    n: usize,
    ncol: usize,
    var_opt: bool,
    var_weights: &[f64],
    cor_opt: bool,
    cor_dims: &[i32],
    cor_factor: &[f64],
) -> Result<f64, String> {
    if var_opt {
        if var_weights.len() != n {
            return Err("varWeights length must equal N".to_string());
        }
        for col in 0..ncol {
            let base = col * n;
            for row in 0..n {
                result[base + row] *= var_weights[row];
            }
        }
    }
    if cor_opt {
        cor_struct_recalc(result, cor_dims, ncol, cor_factor)?;
    }
    let resid = n.saturating_mul(ncol.saturating_sub(1));
    let mut rss = 0.0;
    for value in &result[resid..resid + n] {
        rss += value * value;
    }
    Ok(rss)
}

fn gnls_increment(
    result: &mut [f64],
    n: usize,
    npar: usize,
    nrdof: i32,
    new_objective: f64,
    incr: &mut [f64],
) -> f64 {
    let mut gradient = result[..n * npar].to_vec();
    let residuals = &result[n * npar..n * npar + n];
    let mut qraux = vec![0.0; npar];
    let mut pivot: Vec<i32> = (0..npar as i32).collect();
    let _rank = dqrdc2(
        &mut gradient,
        n,
        n,
        npar,
        f64::EPSILON.sqrt(),
        &mut qraux,
        &mut pivot,
    );
    qr_solve(&mut gradient, n, n, npar, &qraux, residuals, incr);
    let mut aux = residuals.to_vec();
    dqrsl_qty(&mut gradient, n, n, npar, &qraux, &mut aux);
    let mut reg_ss = 0.0;
    for value in aux.iter().take(npar) {
        reg_ss += value * value;
    }
    let scale = (nrdof as f64) * reg_ss / (npar as f64) * (new_objective - reg_ss);
    scale.sqrt()
}

fn evaluate_into<F>(model: &mut F, theta: &[f64], result: &mut [f64]) -> Result<(), String>
where
    F: FnMut(&[f64]) -> Result<Vec<f64>, String>,
{
    let values = model(theta)?;
    if values.len() != result.len() {
        return Err(format!(
            "model returned {} values, expected {}",
            values.len(),
            result.len()
        ));
    }
    result.copy_from_slice(&values);
    Ok(())
}

/// Port of `fit_gnls`.
///
/// `dims` begins with `npar` and `N`. `settings` is
/// `[maxIter, minFactor, tolerance, conv, iterations, objective]` and the last
/// three entries are written here. `additional` receives the unweighted
/// residuals at the returned coefficients. `cor_opt` and `var_opt` are the C
/// integers: nonzero turns the correction on.
pub fn fit_gnls<F>(
    theta: &mut [f64],
    dims: &[i32],
    cor_factor: &[f64],
    var_weights: &[f64],
    cor_dims: &[i32],
    settings: &mut [f64],
    additional: &mut [f64],
    cor_opt: i32,
    var_opt: i32,
    mut model: F,
) -> Result<(), String>
where
    F: FnMut(&[f64]) -> Result<Vec<f64>, String>,
{
    if dims.len() < 2 {
        return Err("dims needs npar and N".to_string());
    }
    if settings.len() < 6 {
        return Err("settings needs six values".to_string());
    }
    let npar = usize_from_i32(dims[0], "npar")?;
    let n = usize_from_i32(dims[1], "N")?;
    if npar == 0 {
        return Err("npar must be positive".to_string());
    }
    if theta.len() != npar {
        return Err(format!("theta length {} does not equal npar {npar}", theta.len()));
    }
    if additional.len() != n {
        return Err("additional length must equal N".to_string());
    }
    if !settings[0].is_finite() || !settings[1].is_finite() || !settings[2].is_finite() {
        return Err("settings maxIter, minFactor, and tolerance must be finite".to_string());
    }
    let ncol = npar + 1;
    let mut result = vec![0.0; n * ncol];
    evaluate_into(&mut model, theta, &mut result)?;
    let var_on = var_opt != 0;
    let cor_on = cor_opt != 0;
    let max_iter = settings[0] as i32;
    let min_factor = settings[1];
    let tolerance = settings[2];
    let nrdof = (n as i32) - (npar as i32);
    let mut new_theta = theta.to_vec();
    let mut incr = vec![0.0; npar];
    let mut conv_failure = 0i32;
    let mut new_objective = apply_objective(
        &mut result,
        n,
        ncol,
        var_on,
        var_weights,
        cor_on,
        cor_dims,
        cor_factor,
    )?;
    let mut objective = new_objective;
    let mut factor = 1.0;
    let mut iteration = 1i32;
    let iterations = loop {
        if iteration > max_iter {
            conv_failure = 2;
            break iteration - 1;
        }
        let criterion = gnls_increment(&mut result, n, npar, nrdof, new_objective, &mut incr);
        if conv_failure != 0 {
            break iteration;
        }
        if criterion < tolerance {
            break iteration;
        }
        loop {
            if factor < min_factor {
                conv_failure = 1;
                break;
            }
            new_theta.copy_from_slice(theta);
            daxpy(npar, factor, &incr, 0, &mut new_theta, 0);
            evaluate_into(&mut model, &new_theta, &mut result)?;
            new_objective = apply_objective(
                &mut result,
                n,
                ncol,
                var_on,
                var_weights,
                cor_on,
                cor_dims,
                cor_factor,
            )?;
            factor /= 2.0;
            if !(new_objective >= objective) {
                break;
            }
        }
        if conv_failure != 0 {
            break iteration;
        }
        factor *= 4.0;
        if factor > 1.0 {
            factor = 1.0;
        }
        objective = new_objective;
        theta.copy_from_slice(&new_theta);
        iteration += 1;
    };
    evaluate_into(&mut model, theta, &mut result)?;
    let resid_at = npar * n;
    additional.copy_from_slice(&result[resid_at..resid_at + n]);
    objective = apply_objective(
        &mut result,
        n,
        ncol,
        var_on,
        var_weights,
        cor_on,
        cor_dims,
        cor_factor,
    )?;
    settings[3] = conv_failure as f64;
    settings[4] = iterations as f64;
    settings[5] = objective;
    Ok(())
}

/// Milliseconds for one `fit_gnls` call, measured around the kernel.
pub fn fit_gnls_ms<F>(
    theta: &[f64],
    dims: &[i32],
    cor_factor: &[f64],
    var_weights: &[f64],
    cor_dims: &[i32],
    settings: &[f64],
    additional: &[f64],
    cor_opt: i32,
    var_opt: i32,
    mut model: F,
) -> Result<f64, String>
where
    F: FnMut(&[f64]) -> Result<Vec<f64>, String>,
{
    let mut theta = theta.to_vec();
    let mut settings = settings.to_vec();
    let mut additional = additional.to_vec();
    let started = Instant::now();
    fit_gnls(
        &mut theta,
        dims,
        cor_factor,
        var_weights,
        cor_dims,
        &mut settings,
        &mut additional,
        cor_opt,
        var_opt,
        &mut model,
    )?;
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

#[cfg(feature = "python")]
#[pymodule]
fn gnlsfit(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fit_gnls_py, m)?)?;
    m.add_function(wrap_pyfunction!(fit_gnls_ms_py, m)?)?;
    Ok(())
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "fit_gnls")]
fn fit_gnls_py(
    py: Python<'_>,
    mut theta: Vec<f64>,
    dims: Vec<i32>,
    cor_factor: Vec<f64>,
    var_weights: Vec<f64>,
    cor_dims: Vec<i32>,
    mut settings: Vec<f64>,
    mut additional: Vec<f64>,
    cor_opt: i32,
    var_opt: i32,
    model: Py<PyAny>,
) -> PyResult<(Vec<f64>, Vec<f64>, Vec<f64>)> {
    let mut model_error: Option<PyErr> = None;
    let fit = fit_gnls(
        &mut theta,
        &dims,
        &cor_factor,
        &var_weights,
        &cor_dims,
        &mut settings,
        &mut additional,
        cor_opt,
        var_opt,
        |pars| match call_model(py, &model, pars) {
            Ok(values) => Ok(values),
            Err(err) => {
                model_error = Some(err);
                Err("model callback failed".to_string())
            }
        },
    );
    if let Some(err) = model_error {
        return Err(err);
    }
    fit.map_err(pyo3::exceptions::PyValueError::new_err)?;
    Ok((theta, settings, additional))
}

#[cfg(feature = "python")]
fn call_model(py: Python<'_>, model: &Py<PyAny>, pars: &[f64]) -> PyResult<Vec<f64>> {
    let out = model.bind(py).call1((pars.to_vec(),))?;
    out.extract()
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "fit_gnls_ms")]
fn fit_gnls_ms_py(
    py: Python<'_>,
    theta: Vec<f64>,
    dims: Vec<i32>,
    cor_factor: Vec<f64>,
    var_weights: Vec<f64>,
    cor_dims: Vec<i32>,
    settings: Vec<f64>,
    additional: Vec<f64>,
    cor_opt: i32,
    var_opt: i32,
    model: Py<PyAny>,
) -> PyResult<f64> {
    let mut model_error: Option<PyErr> = None;
    let elapsed = fit_gnls_ms(
        &theta,
        &dims,
        &cor_factor,
        &var_weights,
        &cor_dims,
        &settings,
        &additional,
        cor_opt,
        var_opt,
        |pars| match call_model(py, &model, pars) {
            Ok(values) => Ok(values),
            Err(err) => {
                model_error = Some(err);
                Err("model callback failed".to_string())
            }
        },
    );
    if let Some(err) = model_error {
        return Err(err);
    }
    elapsed.map_err(pyo3::exceptions::PyValueError::new_err)
}

#[cfg(test)]
mod tests {
    use super::fit_gnls;

    fn linear(theta: &[f64]) -> Result<Vec<f64>, String> {
        let x = [1.0, 2.0, 3.0, 4.0];
        let y = [5.0, 8.0, 11.0, 14.0];
        let n = 4;
        let mut out = vec![0.0; n * 3];
        for i in 0..n {
            out[i] = 1.0;
            out[n + i] = x[i];
            out[2 * n + i] = y[i] - (theta[0] + theta[1] * x[i]);
        }
        Ok(out)
    }

    #[test]
    fn linear_mean_reaches_least_squares() {
        let mut theta = vec![0.0, 0.0];
        let mut settings = vec![7.0, 0.001, 0.001, 0.0, 0.0, 0.0];
        let mut additional = vec![0.0; 4];
        fit_gnls(
            &mut theta,
            &[2, 4, 0],
            &[1.0],
            &[1.0],
            &[1],
            &mut settings,
            &mut additional,
            0,
            0,
            linear,
        )
        .unwrap();
        // A perfect linear residual lies in the column space, so the
        // convergence criterion is already zero and the step is not taken.
        assert!(
            theta[0].abs() < 1e-15 && theta[1].abs() < 1e-15,
            "theta={theta:?} settings={settings:?}"
        );
        assert_eq!(settings[3] as i32, 0);
        assert!((settings[4] - 1.0).abs() < 1e-15);
        assert!((settings[5] - 406.0).abs() < 1e-10);
    }

    #[test]
    fn noisy_linear_takes_the_gauss_newton_step() {
        fn model(theta: &[f64]) -> Result<Vec<f64>, String> {
            let x = [1.0, 2.0, 3.0, 4.0];
            let y = [5.1, 7.8, 11.2, 13.9];
            let n = 4;
            let mut out = vec![0.0; n * 3];
            for i in 0..n {
                out[i] = 1.0;
                out[n + i] = x[i];
                out[2 * n + i] = y[i] - (theta[0] + theta[1] * x[i]);
            }
            Ok(out)
        }
        let mut theta = vec![0.0, 0.0];
        let mut settings = vec![7.0, 0.001, 0.001, 0.0, 0.0, 0.0];
        let mut additional = vec![0.0; 4];
        fit_gnls(
            &mut theta,
            &[2, 4, 0],
            &[1.0],
            &[1.0],
            &[1],
            &mut settings,
            &mut additional,
            0,
            0,
            model,
        )
        .unwrap();
        assert!(
            (theta[0] - 2.05).abs() < 1e-8 && (theta[1] - 2.98).abs() < 1e-8,
            "theta={theta:?} settings={settings:?}"
        );
        assert_eq!(settings[3] as i32, 0);
    }

    #[test]
    fn variance_weights_scale_the_residual_sum_of_squares() {
        let mut theta = vec![2.0, 3.0];
        let mut settings = vec![7.0, 0.001, 0.001, 0.0, 0.0, 0.0];
        let mut additional = vec![0.0; 4];
        let weights = [1.0, 2.0, 0.5, 1.0];
        fit_gnls(
            &mut theta,
            &[2, 4],
            &[1.0],
            &weights,
            &[1],
            &mut settings,
            &mut additional,
            0,
            1,
            linear,
        )
        .unwrap();
        assert!(settings[3].abs() < 1e-12);
        assert!(settings[5].is_finite());
    }
}
