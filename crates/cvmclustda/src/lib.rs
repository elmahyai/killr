//! Fortran kernels from mclust for Gaussian EEE (mseee, eseee, uncholf).

#[cfg(feature = "python")]
mod python {
    use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::prelude::*;

    unsafe extern "C" {
        fn mseee_(
            x: *mut f64,
            z: *mut f64,
            n: *mut i32,
            p: *mut i32,
            g: *mut i32,
            w: *mut f64,
            mu: *mut f64,
            u: *mut f64,
            pro: *mut f64,
        );
        fn eseee_(
            chol: *mut i32,
            x: *mut f64,
            mu: *mut f64,
            sigma: *mut f64,
            pro: *mut f64,
            n: *mut i32,
            p: *mut i32,
            g: *mut i32,
            vinv: *mut f64,
            w: *mut f64,
            hood: *mut f64,
            z: *mut f64,
        );
        fn uncholf_(
            upper: *mut i32,
            x: *mut f64,
            nrow: *mut i32,
            ncol: *mut i32,
            info: *mut i32,
        );
    }

    #[pyfunction]
    #[pyo3(name = "mseee")]
    fn mseee_py(
        x: PyReadonlyArray2<f64>,
        z: PyReadonlyArray2<f64>,
    ) -> PyResult<(Py<PyArray1<f64>>, Py<PyArray1<f64>>, Py<PyArray1<f64>>, i32, i32, i32)> {
        let x = x.as_array().to_owned();
        let z = z.as_array().to_owned();
        let n = x.nrows() as i32;
        let p = x.ncols() as i32;
        let g = z.ncols() as i32;
        let mut x_vec = x.into_raw_vec();
        let mut z_vec = z.into_raw_vec();
        let mut w = vec![0.0_f64; p as usize];
        let mut mu = vec![0.0_f64; (p * g) as usize];
        let mut u = vec![0.0_f64; (p * p) as usize];
        let mut pro = vec![0.0_f64; g as usize];
        let mut n_i = n;
        let mut p_i = p;
        let mut g_i = g;
        unsafe {
            mseee_(
                x_vec.as_mut_ptr(),
                z_vec.as_mut_ptr(),
                &mut n_i,
                &mut p_i,
                &mut g_i,
                w.as_mut_ptr(),
                mu.as_mut_ptr(),
                u.as_mut_ptr(),
                pro.as_mut_ptr(),
            );
        }
        Python::attach(|py| {
            Ok((
                PyArray1::from_vec(py, mu).into(),
                PyArray1::from_vec(py, u).into(),
                PyArray1::from_vec(py, pro).into(),
                p,
                g,
                n,
            ))
        })
    }

    #[pyfunction]
    #[pyo3(name = "eseee")]
    fn eseee_py(
        chol: bool,
        x: PyReadonlyArray2<f64>,
        mu: PyReadonlyArray2<f64>,
        sigma: PyReadonlyArray2<f64>,
        pro: PyReadonlyArray1<f64>,
        vinv: f64,
    ) -> PyResult<(f64, f64, Py<PyArray1<f64>>, i32, i32)> {
        let x = x.as_array().to_owned();
        let mu = mu.as_array().to_owned();
        let sigma = sigma.as_array().to_owned();
        let pro = pro.as_array();
        let n = x.nrows() as i32;
        let p = x.ncols() as i32;
        let g = mu.ncols() as i32;
        let k = pro.len() as i32;
        let mut x_vec = x.into_raw_vec();
        let mut mu_vec = mu.into_raw_vec();
        let mut sigma_vec = sigma.into_raw_vec();
        let mut pro_vec = pro.to_owned().into_raw_vec();
        let mut w = vec![0.0_f64; p as usize];
        let mut hood = 0.0_f64;
        let mut z = vec![0.0_f64; (n * k) as usize];
        let mut chol_i = if chol { 1_i32 } else { 0_i32 };
        let mut vinv_v = vinv;
        let mut n_i = n;
        let mut p_i = p;
        let mut g_i = g;
        unsafe {
            eseee_(
                &mut chol_i,
                x_vec.as_mut_ptr(),
                mu_vec.as_mut_ptr(),
                sigma_vec.as_mut_ptr(),
                pro_vec.as_mut_ptr(),
                &mut n_i,
                &mut p_i,
                &mut g_i,
                &mut vinv_v,
                w.as_mut_ptr(),
                &mut hood,
                z.as_mut_ptr(),
            );
        }
        Python::attach(|py| Ok((w[0], hood, PyArray1::from_vec(py, z).into(), n, k)))
    }

    #[pyfunction]
    #[pyo3(name = "uncholf")]
    fn uncholf_py(upper: bool, x: PyReadonlyArray2<f64>) -> PyResult<Py<PyArray2<f64>>> {
        let x = x.as_array();
        let mut mat = x.to_owned().into_raw_vec();
        let nrow = x.nrows() as i32;
        let ncol = x.ncols() as i32;
        let mut upper_i = if upper { 1_i32 } else { 0_i32 };
        let mut info = 0_i32;
        let mut nrow_i = nrow;
        let mut ncol_i = ncol;
        unsafe {
            uncholf_(
                &mut upper_i,
                mat.as_mut_ptr(),
                &mut nrow_i,
                &mut ncol_i,
                &mut info,
            );
        }
        Python::attach(|py| {
            Ok(PyArray2::from_vec2(py, &(0..nrow as usize)
                .map(|i| mat[i * ncol as usize..(i + 1) * ncol as usize].to_vec())
                .collect::<Vec<_>>())?
            .into())
        })
    }

    #[pymodule]
    fn cvmclustda(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(mseee_py, m)?)?;
        m.add_function(wrap_pyfunction!(eseee_py, m)?)?;
        m.add_function(wrap_pyfunction!(uncholf_py, m)?)?;
        Ok(())
    }
}
