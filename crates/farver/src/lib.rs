//! Colour conversion kernels from farver 2.1.2.
//!
//! The C++ in `vendor/` is ColorSpace, Conversion, and Comparison, plus the
//! encode and compare loops from `src/encode.cpp` and `src/farver.cpp`.

use std::os::raw::{c_char, c_int};

#[link(name = "farver_kernel", kind = "static")]
#[link(name = "stdc++")]
unsafe extern "C" {
    fn farver_convert(
        colour: *const f64,
        n: c_int,
        ncol: c_int,
        from: c_int,
        to: c_int,
        wf0: f64,
        wf1: f64,
        wf2: f64,
        wt0: f64,
        wt1: f64,
        wt2: f64,
        out: *mut f64,
        out_ncol: *mut c_int,
    ) -> c_int;
    fn farver_compare(
        from: *const f64,
        n: c_int,
        from_ncol: c_int,
        to: *const f64,
        m: c_int,
        to_ncol: c_int,
        from_space: c_int,
        to_space: c_int,
        dist: c_int,
        symmetric: c_int,
        wf0: f64,
        wf1: f64,
        wf2: f64,
        wt0: f64,
        wt1: f64,
        wt2: f64,
        lightness: f64,
        chroma: f64,
        out: *mut f64,
    ) -> c_int;
    fn farver_encode(
        colour: *const f64,
        n: c_int,
        ncol: c_int,
        from: c_int,
        alpha: *const f64,
        alpha_len: c_int,
        w0: f64,
        w1: f64,
        w2: f64,
        out_bytes: *mut c_char,
    ) -> c_int;
    fn farver_decode(
        rgb: *const f64,
        alpha: *const f64,
        missing: *const c_int,
        n: c_int,
        to: c_int,
        with_alpha: c_int,
        w0: f64,
        w1: f64,
        w2: f64,
        out: *mut f64,
        out_ncol: *mut c_int,
    ) -> c_int;
    fn farver_modify(
        r: *const c_int,
        g: *const c_int,
        b: *const c_int,
        alpha_byte: *const c_int,
        value: *const f64,
        skip: *const c_int,
        n: c_int,
        channel: c_int,
        space: c_int,
        op: c_int,
        w0: f64,
        w1: f64,
        w2: f64,
        out_bytes: *mut c_char,
    ) -> c_int;
    fn farver_get_channel(
        r: *const c_int,
        g: *const c_int,
        b: *const c_int,
        n: c_int,
        channel: c_int,
        space: c_int,
        w0: f64,
        w1: f64,
        w2: f64,
        out: *mut f64,
    ) -> c_int;
}

fn rows_from_column_major(data: &[f64], n: usize, k: usize) -> Vec<Vec<f64>> {
    let mut rows = Vec::with_capacity(n);
    for i in 0..n {
        let mut row = Vec::with_capacity(k);
        for c in 0..k {
            row.push(data[c * n + i]);
        }
        rows.push(row);
    }
    rows
}

fn read_strings(bytes: &[u8], n: usize) -> Vec<Option<String>> {
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let chunk = &bytes[i * 10..(i + 1) * 10];
        let end = chunk.iter().position(|b| *b == 0).unwrap_or(chunk.len());
        if end == 0 {
            out.push(None);
        } else {
            out.push(Some(String::from_utf8_lossy(&chunk[..end]).into_owned()));
        }
    }
    out
}

#[cfg(feature = "python")]
mod py {
    use super::{
        farver_compare, farver_convert, farver_decode, farver_encode, farver_get_channel,
        farver_modify, read_strings, rows_from_column_major,
    };
    use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use std::os::raw::{c_char, c_int};

    fn column_major(view: &numpy::ndarray::ArrayView2<f64>) -> (Vec<f64>, i32, i32) {
        let n = view.nrows();
        let k = view.ncols();
        let mut out = vec![0.0; n * k];
        for i in 0..n {
            for c in 0..k {
                out[c * n + i] = view[[i, c]];
            }
        }
        (out, n as i32, k as i32)
    }

    fn white3(white: &PyReadonlyArray1<f64>) -> PyResult<[f64; 3]> {
        let view = white.as_array();
        if view.len() != 3 {
            return Err(PyValueError::new_err(
                "white reference must have length 3",
            ));
        }
        Ok([view[0], view[1], view[2]])
    }

    fn need_columns(code: c_int) -> PyResult<()> {
        if code > 0 {
            return Err(PyValueError::new_err(format!(
                "colourspace requires {code} values"
            )));
        }
        Ok(())
    }

    fn matrix2(py: Python<'_>, rows: Vec<Vec<f64>>, n: usize, k: usize) -> PyResult<Py<PyArray2<f64>>> {
        if n == 0 {
            let empty: Vec<Vec<f64>> = Vec::new();
            let _ = k;
            return Ok(PyArray2::from_vec2(py, &empty)?.into());
        }
        Ok(PyArray2::from_vec2(py, &rows)?.into())
    }

    #[pyfunction]
    fn convert(
        py: Python<'_>,
        colour: PyReadonlyArray2<f64>,
        from: i32,
        to: i32,
        white_from: PyReadonlyArray1<f64>,
        white_to: PyReadonlyArray1<f64>,
    ) -> PyResult<Py<PyArray2<f64>>> {
        let wf = white3(&white_from)?;
        let wt = white3(&white_to)?;
        let (data, n, ncol) = column_major(&colour.as_array());
        let mut out = vec![0.0; n as usize * 4];
        let mut out_ncol: c_int = 0;
        let code = unsafe {
            farver_convert(
                data.as_ptr(),
                n,
                ncol,
                from,
                to,
                wf[0],
                wf[1],
                wf[2],
                wt[0],
                wt[1],
                wt[2],
                out.as_mut_ptr(),
                &mut out_ncol,
            )
        };
        need_columns(code)?;
        let k = out_ncol as usize;
        let rows = rows_from_column_major(&out, n as usize, k);
        matrix2(py, rows, n as usize, k)
    }

    #[pyfunction]
    #[pyo3(signature = (colour_from, colour_to, from_space, to_space, dist, symmetric, white_from, white_to, lightness, chroma))]
    fn compare(
        py: Python<'_>,
        colour_from: PyReadonlyArray2<f64>,
        colour_to: PyReadonlyArray2<f64>,
        from_space: i32,
        to_space: i32,
        dist: i32,
        symmetric: bool,
        white_from: PyReadonlyArray1<f64>,
        white_to: PyReadonlyArray1<f64>,
        lightness: f64,
        chroma: f64,
    ) -> PyResult<Py<PyArray2<f64>>> {
        let wf = white3(&white_from)?;
        let wt = white3(&white_to)?;
        let (from, n, from_ncol) = column_major(&colour_from.as_array());
        let (to, m, to_ncol) = column_major(&colour_to.as_array());
        let mut out = vec![0.0; n as usize * m as usize];
        let code = unsafe {
            farver_compare(
                from.as_ptr(),
                n,
                from_ncol,
                to.as_ptr(),
                m,
                to_ncol,
                from_space,
                to_space,
                dist,
                if symmetric { 1 } else { 0 },
                wf[0],
                wf[1],
                wf[2],
                wt[0],
                wt[1],
                wt[2],
                lightness,
                chroma,
                out.as_mut_ptr(),
            )
        };
        need_columns(code)?;
        let rows = rows_from_column_major(&out, n as usize, m as usize);
        matrix2(py, rows, n as usize, m as usize)
    }

    #[pyfunction]
    #[pyo3(signature = (colour, from, white, alpha=None))]
    fn encode(
        colour: PyReadonlyArray2<f64>,
        from: i32,
        white: PyReadonlyArray1<f64>,
        alpha: Option<PyReadonlyArray1<f64>>,
    ) -> PyResult<Vec<Option<String>>> {
        let w = white3(&white)?;
        let (data, n, ncol) = column_major(&colour.as_array());
        let alpha_owned = match &alpha {
            Some(alpha) => alpha.as_array().iter().copied().collect::<Vec<f64>>(),
            None => Vec::new(),
        };
        let (alpha_ptr, alpha_len) = if alpha.is_some() {
            (alpha_owned.as_ptr(), alpha_owned.len() as c_int)
        } else {
            (std::ptr::null(), 0)
        };
        let mut bytes = vec![0u8; n as usize * 10];
        let code = unsafe {
            farver_encode(
                data.as_ptr(),
                n,
                ncol,
                from,
                alpha_ptr,
                alpha_len,
                w[0],
                w[1],
                w[2],
                bytes.as_mut_ptr() as *mut c_char,
            )
        };
        need_columns(code)?;
        Ok(read_strings(&bytes, n as usize))
    }

    #[pyfunction]
    #[pyo3(signature = (rgb, alpha, missing, to, white, with_alpha))]
    fn decode(
        py: Python<'_>,
        rgb: PyReadonlyArray2<f64>,
        alpha: PyReadonlyArray1<f64>,
        missing: PyReadonlyArray1<i32>,
        to: i32,
        white: PyReadonlyArray1<f64>,
        with_alpha: bool,
    ) -> PyResult<Py<PyArray2<f64>>> {
        let w = white3(&white)?;
        let (data, n, ncol) = column_major(&rgb.as_array());
        if ncol != 3 {
            return Err(PyValueError::new_err("rgb must have 3 columns"));
        }
        let alpha_v: Vec<f64> = alpha.as_array().iter().copied().collect();
        let missing_v: Vec<i32> = missing.as_array().iter().copied().collect();
        let mut out = vec![0.0; n as usize * 5];
        let mut out_ncol: c_int = 0;
        let code = unsafe {
            farver_decode(
                data.as_ptr(),
                alpha_v.as_ptr(),
                missing_v.as_ptr(),
                n,
                to,
                if with_alpha { 1 } else { 0 },
                w[0],
                w[1],
                w[2],
                out.as_mut_ptr(),
                &mut out_ncol,
            )
        };
        need_columns(code)?;
        let k = out_ncol as usize;
        let rows = rows_from_column_major(&out, n as usize, k);
        matrix2(py, rows, n as usize, k)
    }

    #[pyfunction]
    fn modify(
        r: PyReadonlyArray1<i32>,
        g: PyReadonlyArray1<i32>,
        b: PyReadonlyArray1<i32>,
        alpha_byte: PyReadonlyArray1<i32>,
        value: PyReadonlyArray1<f64>,
        skip: PyReadonlyArray1<i32>,
        channel: i32,
        space: i32,
        op: i32,
        white: PyReadonlyArray1<f64>,
    ) -> PyResult<Vec<Option<String>>> {
        let w = white3(&white)?;
        let rv: Vec<i32> = r.as_array().iter().copied().collect();
        let gv: Vec<i32> = g.as_array().iter().copied().collect();
        let bv: Vec<i32> = b.as_array().iter().copied().collect();
        let av: Vec<i32> = alpha_byte.as_array().iter().copied().collect();
        let vv: Vec<f64> = value.as_array().iter().copied().collect();
        let sv: Vec<i32> = skip.as_array().iter().copied().collect();
        let n = rv.len();
        let mut bytes = vec![0u8; n * 10];
        let code = unsafe {
            farver_modify(
                rv.as_ptr(),
                gv.as_ptr(),
                bv.as_ptr(),
                av.as_ptr(),
                vv.as_ptr(),
                sv.as_ptr(),
                n as c_int,
                channel,
                space,
                op,
                w[0],
                w[1],
                w[2],
                bytes.as_mut_ptr() as *mut c_char,
            )
        };
        need_columns(code)?;
        Ok(read_strings(&bytes, n))
    }

    #[pyfunction]
    fn get_channel(
        py: Python<'_>,
        r: PyReadonlyArray1<i32>,
        g: PyReadonlyArray1<i32>,
        b: PyReadonlyArray1<i32>,
        channel: i32,
        space: i32,
        white: PyReadonlyArray1<f64>,
    ) -> PyResult<Py<PyArray1<f64>>> {
        let w = white3(&white)?;
        let rv: Vec<i32> = r.as_array().iter().copied().collect();
        let gv: Vec<i32> = g.as_array().iter().copied().collect();
        let bv: Vec<i32> = b.as_array().iter().copied().collect();
        let n = rv.len();
        let mut out = vec![0.0; n];
        unsafe {
            farver_get_channel(
                rv.as_ptr(),
                gv.as_ptr(),
                bv.as_ptr(),
                n as c_int,
                channel,
                space,
                w[0],
                w[1],
                w[2],
                out.as_mut_ptr(),
            );
        }
        Ok(PyArray1::from_vec(py, out).into())
    }

    #[pymodule]
    fn farver_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(convert, m)?)?;
        m.add_function(wrap_pyfunction!(compare, m)?)?;
        m.add_function(wrap_pyfunction!(encode, m)?)?;
        m.add_function(wrap_pyfunction!(decode, m)?)?;
        m.add_function(wrap_pyfunction!(modify, m)?)?;
        m.add_function(wrap_pyfunction!(get_channel, m)?)?;
        Ok(())
    }
}
