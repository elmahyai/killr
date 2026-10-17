//! Fuzzy c-shell clustering, ported from e1071 `src/cshell.c`.

#[inline]
fn msub(v: &[f64], i: usize, j: usize, nr: usize) -> f64 {
    v[i + nr * j]
}

#[inline]
fn mset(v: &mut [f64], i: usize, j: usize, nr: usize, value: f64) {
    v[i + nr * j] = value;
}

fn subcshell(
    xrows: i32,
    xcols: i32,
    x: &[f64],
    ncenters: i32,
    centers: &mut [f64],
    _itermax: i32,
    iter: i32,
    verbose: i32,
    dist: i32,
    u: &mut [f64],
    uant: &mut [f64],
    f: f64,
    ermin: &mut f64,
    radius: &mut [f64],
    flag: &mut i32,
) {
    let xrows = xrows as usize;
    let xcols = xcols as usize;
    let ncenters = ncenters as usize;
    let nr = xrows;

    let mut serror;
    let epsi1 = 0.002;
    let epsi2 = 0.2;
    let mut conv = 0.0;
    let exponente = 2.0 / (f - 1.0);

    if *flag == 0 || *flag == 5 {
        for i in 0..ncenters {
            let mut sum2 = 0.0;
            for col in 0..xcols {
                mset(centers, i, col, ncenters, 0.0);
            }
            for k in 0..xrows {
                let temp = msub(u, k, i, nr).powf(f);
                sum2 += temp;
                for col in 0..xcols {
                    let cur = msub(centers, i, col, ncenters);
                    mset(
                        centers,
                        i,
                        col,
                        ncenters,
                        cur + temp * msub(x, k, col, nr),
                    );
                }
            }
            for col in 0..xcols {
                let cur = msub(centers, i, col, ncenters);
                mset(centers, i, col, ncenters, cur / sum2);
            }
        }

        for i in 0..ncenters {
            let mut sum2 = 0.0;
            radius[i] = 0.0;
            for k in 0..xrows {
                let mut distance = 0.0;
                let temp = msub(u, k, i, nr).powf(f);
                sum2 += temp;
                for col in 0..xcols {
                    if dist == 0 {
                        let d = msub(x, k, col, nr) - msub(centers, i, col, ncenters);
                        distance += d * d;
                    } else if dist == 1 {
                        distance += (msub(x, k, col, nr) - msub(centers, i, col, ncenters)).abs();
                    }
                }
                if dist == 0 {
                    radius[i] += temp * distance.sqrt();
                } else if dist == 1 {
                    radius[i] += temp * distance;
                }
            }
            radius[i] /= sum2;
        }
    }

    for i in 0..ncenters {
        for k in 0..xrows {
            mset(uant, k, i, nr, msub(u, k, i, nr));
        }
    }

    for i in 0..ncenters {
        for k in 0..xrows {
            let mut suma = 0.0;
            for j in 0..ncenters {
                let mut tempu1 = 0.0;
                let mut tempu2 = 0.0;
                for col in 0..xcols {
                    if dist == 0 {
                        let d1 = msub(x, k, col, nr) - msub(centers, i, col, ncenters);
                        let d2 = msub(x, k, col, nr) - msub(centers, j, col, ncenters);
                        tempu1 += d1 * d1;
                        tempu2 += d2 * d2;
                    } else if dist == 1 {
                        tempu1 += (msub(x, k, col, nr) - msub(centers, i, col, ncenters)).abs();
                        tempu2 += (msub(x, k, col, nr) - msub(centers, j, col, ncenters)).abs();
                    }
                }
                let tempu = if dist == 0 {
                    (tempu1.sqrt() - radius[i]).abs() / (tempu2.sqrt() - radius[j]).abs()
                } else {
                    ((tempu1 - radius[i]) / (tempu2 - radius[j])).abs()
                };
                suma += tempu.powf(exponente);
            }
            mset(u, k, i, nr, 1.0 / suma);
        }
    }

    *ermin = 0.0;
    conv = 0.0;

    for m in 0..ncenters {
        for k in 0..xrows {
            serror = 0.0;
            for n in 0..xcols {
                if dist == 0 {
                    let d = msub(x, k, n, nr) - msub(centers, m, n, ncenters);
                    serror += d * d;
                } else if dist == 1 {
                    serror += (msub(x, k, n, nr) - msub(centers, m, n, ncenters)).abs();
                }
            }
            if dist == 0 {
                serror = (serror.sqrt() - radius[m]).abs();
            } else if dist == 1 {
                serror = (serror - radius[m]).abs();
            }
            *ermin += msub(u, k, m, nr).powf(f) * serror.powi(2);
            conv += (msub(u, k, m, nr) - msub(uant, k, m, nr)).abs();
        }
    }

    if conv <= (xrows * xcols) as f64 * epsi1 {
        *flag = 2;
        if verbose != 0 {
            eprintln!(
                "Iteration: {:3}    converged, Error:   {:13.10}",
                iter, conv
            );
        }
    } else if conv <= (xrows * xcols) as f64 * epsi2 {
        if verbose != 0 {
            eprintln!("Iteration: {:3}    Epsi2:   {:13.10}", iter, conv);
        }
        if *flag == 3 {
            *flag = 4;
        } else {
            *flag = 1;
        }
    } else if *flag == 3 {
        *flag = 5;
    }

    if verbose != 0 {
        eprintln!(
            "Iteration: {:3}    Error:   {:13.10}",
            iter,
            *ermin / xrows as f64
        );
    }
}

pub fn run_cshell(
    x: &[f64],
    xrows: i32,
    xcols: i32,
    centers: &mut [f64],
    ncenters: i32,
    iter_max: i32,
    iter: &mut i32,
    verbose: i32,
    dist: i32,
    u: &mut [f64],
    uant: &mut [f64],
    f: f64,
    ermin: &mut f64,
    radius: &mut [f64],
    flag: &mut i32,
) {
    let exponente = 2.0 / (f - 1.0);
    let xrows_usize = xrows as usize;
    let xcols_usize = xcols as usize;
    let ncenters_usize = ncenters as usize;
    let nr = xrows_usize;

    if *flag == 0 {
        *iter = 0;
        for i in 0..ncenters_usize {
            for k in 0..xrows_usize {
                let mut suma = 0.0;
                for j in 0..ncenters_usize {
                    let mut tempu1 = 0.0;
                    let mut tempu2 = 0.0;
                    for col in 0..xcols_usize {
                        if dist == 0 {
                            let d1 = msub(x, k, col, nr) - msub(centers, i, col, ncenters_usize);
                            let d2 = msub(x, k, col, nr) - msub(centers, j, col, ncenters_usize);
                            tempu1 += d1 * d1;
                            tempu2 += d2 * d2;
                        } else if dist == 1 {
                            tempu1 +=
                                (msub(x, k, col, nr) - msub(centers, i, col, ncenters_usize)).abs();
                            tempu2 +=
                                (msub(x, k, col, nr) - msub(centers, j, col, ncenters_usize)).abs();
                        }
                    }
                    let tempu = if dist == 0 {
                        (tempu1.sqrt() - radius[i]).abs() / (tempu2.sqrt() - radius[j]).abs()
                    } else {
                        ((tempu1 - radius[i]) / (tempu2 - radius[j])).abs()
                    };
                    suma += tempu.powf(exponente);
                }
                mset(uant, k, i, nr, 1.0 / suma);
            }
        }
        for i in 0..ncenters_usize {
            for j in 0..xrows_usize {
                mset(u, j, i, nr, msub(uant, j, i, nr));
            }
        }
    }

    while {
        let prev = *iter;
        *iter = prev + 1;
        prev < iter_max && *flag != 1 && *flag != 2 && *flag != 4
    } {
        *ermin = 0.0;
        subcshell(
            xrows,
            xcols,
            x,
            ncenters,
            centers,
            iter_max,
            *iter,
            verbose,
            dist,
            u,
            uant,
            f,
            ermin,
            radius,
            flag,
        );
    }
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::run_cshell;

    fn owned_f64(array: &PyReadonlyArray1<'_, f64>) -> PyResult<Vec<f64>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    #[pyfunction]
    #[pyo3(name = "cshell_kernel", signature = (x, centers, radius, u, uant, xrows, xcols, ncenters, m=2.0, dist=0, iter_max=100, iter=0, verbose=0, flag=0))]
    fn cshell_kernel_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        mut centers: PyReadonlyArray1<'py, f64>,
        mut radius: PyReadonlyArray1<'py, f64>,
        mut u: PyReadonlyArray1<'py, f64>,
        mut uant: PyReadonlyArray1<'py, f64>,
        xrows: i32,
        xcols: i32,
        ncenters: i32,
        m: f64,
        dist: i32,
        iter_max: i32,
        mut iter: i32,
        verbose: i32,
        mut flag: i32,
    ) -> PyResult<(
        Bound<'py, numpy::PyArray1<f64>>,
        Bound<'py, numpy::PyArray1<f64>>,
        Bound<'py, numpy::PyArray1<f64>>,
        Bound<'py, numpy::PyArray1<f64>>,
        f64,
        i32,
        i32,
    )> {
        let x = owned_f64(&x)?;
        let mut center_vec = owned_f64(&mut centers)?;
        let mut radius_vec = owned_f64(&mut radius)?;
        let mut u_vec = owned_f64(&mut u)?;
        let mut uant_vec = owned_f64(&mut uant)?;
        let expected_x = (xrows * xcols) as usize;
        let expected_u = (xrows * ncenters) as usize;
        if x.len() != expected_x {
            return Err(PyValueError::new_err("length of 'x' does not match dimensions"));
        }
        if center_vec.len() != (ncenters * xcols) as usize {
            return Err(PyValueError::new_err(
                "length of 'centers' does not match dimensions",
            ));
        }
        if radius_vec.len() != ncenters as usize {
            return Err(PyValueError::new_err(
                "length of 'radius' must equal number of centers",
            ));
        }
        if u_vec.len() != expected_u || uant_vec.len() != expected_u {
            return Err(PyValueError::new_err(
                "length of 'u' and 'uant' must be xrows * ncenters",
            ));
        }
        let mut ermin = 0.0;
        run_cshell(
            &x,
            xrows,
            xcols,
            &mut center_vec,
            ncenters,
            iter_max,
            &mut iter,
            verbose,
            dist,
            &mut u_vec,
            &mut uant_vec,
            m,
            &mut ermin,
            &mut radius_vec,
            &mut flag,
        );
        Ok((
            center_vec.into_pyarray(py),
            radius_vec.into_pyarray(py),
            u_vec.into_pyarray(py),
            uant_vec.into_pyarray(py),
            ermin,
            iter,
            flag,
        ))
    }

    #[pymodule]
    fn cshell(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(cshell_kernel_py, m)?)?;
        Ok(())
    }
}
