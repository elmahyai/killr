//! Concordance counts from survival 3.8-12 `src/concordance1.c`.
//!
//! `concordance1` is `Cconcordance1` (right-censored). `concordance2` is
//! `Cconcordance2` ((start, stop] counting process). Both return the five raw
//! sums: concordant, discordant, tied risk, tied time, and the unscaled
//! variance term. The R wrapper's `2 * sqrt` step is not part of these kernels.

/// Right-censored concordance (`Cconcordance1`).
///
/// `time` and `status` are ordered by time ascending, then by `-status`.
/// The walk starts at the last row. `indx` is a 0-based heap index.
/// `status == 1` is a death; every other value is censored.
pub fn concordance1(
    time: &[f64],
    status: &[f64],
    wt: &[f64],
    indx: &[i32],
    ntree: usize,
) -> [f64; 5] {
    let n = time.len();
    let mut count = [0.0; 5];
    if n == 0 || ntree == 0 {
        return count;
    }
    let mut twt = vec![0.0; ntree];
    let mut nwt = vec![0.0; ntree];
    let mut vss = 0.0;
    let mut i: isize = n as isize - 1;
    while i >= 0 {
        let mut ndeath = 0.0;
        let j: isize;
        if status[i as usize] == 1.0 {
            let i_time = time[i as usize];
            let mut jj = i;
            while jj >= 0 && status[jj as usize] == 1.0 && time[jj as usize] == i_time {
                let ju = jj as usize;
                ndeath += wt[ju];
                let mut index = indx[ju];
                let mut k = i;
                while k > jj {
                    count[3] += wt[ju] * wt[k as usize];
                    k -= 1;
                }
                count[2] += wt[ju] * nwt[index as usize];
                let mut child = 2 * index + 1;
                if (child as usize) < ntree {
                    count[0] += wt[ju] * twt[child as usize];
                }
                child += 1;
                if (child as usize) < ntree {
                    count[1] += wt[ju] * twt[child as usize];
                }
                while index > 0 {
                    let parent = (index - 1) / 2;
                    if index & 1 != 0 {
                        count[1] += wt[ju] * (twt[parent as usize] - twt[index as usize]);
                    } else {
                        count[0] += wt[ju] * (twt[parent as usize] - twt[index as usize]);
                    }
                    index = parent;
                }
                jj -= 1;
            }
            j = jj;
        } else {
            j = i - 1;
        }
        while i > j {
            let iu = i as usize;
            let mut wsum1 = 0.0;
            let oldmean = twt[0] / 2.0;
            let mut index = indx[iu];
            nwt[index as usize] += wt[iu];
            twt[index as usize] += wt[iu];
            let wsum2 = nwt[index as usize];
            let child = 2 * index + 1;
            if (child as usize) < ntree {
                wsum1 += twt[child as usize];
            }
            while index > 0 {
                let parent = (index - 1) / 2;
                twt[parent as usize] += wt[iu];
                if index & 1 == 0 {
                    wsum1 += twt[parent as usize] - twt[index as usize];
                }
                index = parent;
            }
            let wsum3 = twt[0] - (wsum1 + wsum2);
            let lmean = wsum1 / 2.0;
            let umean = wsum1 + wsum2 + wsum3 / 2.0;
            let newmean = twt[0] / 2.0;
            let myrank = wsum1 + wsum2 / 2.0;
            vss += wsum1 * (newmean + oldmean - 2.0 * lmean) * (newmean - oldmean);
            vss += wsum3 * (newmean + oldmean + wt[iu] - 2.0 * umean) * (oldmean - newmean);
            vss += wt[iu] * (myrank - newmean) * (myrank - newmean);
            i -= 1;
        }
        count[4] += ndeath * vss / twt[0];
    }
    count
}

/// Counting-process concordance (`Cconcordance2`).
///
/// Rows stay in original order. `sort_stop` is `order(-stop, status) - 1` and
/// `sort_start` is `order(-start) - 1`. A censored stop adds only that row
/// (`i < j` with `j = i + 1`). Before a death at time `d`, rows with
/// `start >= d` are removed from the tree.
pub fn concordance2(
    start: &[f64],
    stop: &[f64],
    status: &[f64],
    wt: &[f64],
    indx: &[i32],
    ntree: usize,
    sort_stop: &[i32],
    sort_start: &[i32],
) -> [f64; 5] {
    let n = start.len();
    let mut count = [0.0; 5];
    if n == 0 || ntree == 0 {
        return count;
    }
    let mut twt = vec![0.0; ntree];
    let mut nwt = vec![0.0; ntree];
    let mut vss = 0.0;
    let mut istart: usize = 0;
    let mut i: usize = 0;
    while i < n {
        let iptr = sort_stop[i] as usize;
        let mut ndeath = 0.0;
        let j: usize;
        if status[iptr] == 1.0 {
            let dtime = stop[iptr];
            while istart < n && start[sort_start[istart] as usize] >= dtime {
                let jptr = sort_start[istart] as usize;
                let mut wsum1 = 0.0;
                let mut oldmean = twt[0] / 2.0;
                let mut index = indx[jptr];
                nwt[index as usize] -= wt[jptr];
                twt[index as usize] -= wt[jptr];
                let wsum2 = nwt[index as usize];
                let child = 2 * index + 1;
                if (child as usize) < ntree {
                    wsum1 += twt[child as usize];
                }
                while index > 0 {
                    let parent = (index - 1) / 2;
                    twt[parent as usize] -= wt[jptr];
                    if index & 1 == 0 {
                        wsum1 += twt[parent as usize] - twt[index as usize];
                    }
                    index = parent;
                }
                let wsum3 = twt[0] - (wsum1 + wsum2);
                let lmean = wsum1 / 2.0;
                let umean = wsum1 + wsum2 + wsum3 / 2.0;
                let newmean = twt[0] / 2.0;
                let myrank = wsum1 + wsum2 / 2.0;
                vss += wsum1 * (newmean + oldmean - 2.0 * lmean) * (newmean - oldmean);
                oldmean -= wt[jptr];
                vss += wsum3 * (newmean + oldmean - 2.0 * umean) * (newmean - oldmean);
                vss -= wt[jptr] * (myrank - newmean) * (myrank - newmean);
                istart += 1;
            }
            let mut jj = i;
            while jj < n {
                let jptr = sort_stop[jj] as usize;
                if status[jptr] != 1.0 || stop[jptr] != dtime {
                    break;
                }
                ndeath += wt[jptr];
                let mut index = indx[jptr];
                for k in i..jj {
                    count[3] += wt[jptr] * wt[sort_stop[k] as usize];
                }
                count[2] += wt[jptr] * nwt[index as usize];
                let mut child = 2 * index + 1;
                if (child as usize) < ntree {
                    count[0] += wt[jptr] * twt[child as usize];
                }
                child += 1;
                if (child as usize) < ntree {
                    count[1] += wt[jptr] * twt[child as usize];
                }
                while index > 0 {
                    let parent = (index - 1) / 2;
                    if index & 1 != 0 {
                        count[1] += wt[jptr] * (twt[parent as usize] - twt[index as usize]);
                    } else {
                        count[0] += wt[jptr] * (twt[parent as usize] - twt[index as usize]);
                    }
                    index = parent;
                }
                jj += 1;
            }
            j = jj;
        } else {
            j = i + 1;
        }
        while i < j {
            let ip = sort_stop[i] as usize;
            let mut wsum1 = 0.0;
            let oldmean = twt[0] / 2.0;
            let mut index = indx[ip];
            nwt[index as usize] += wt[ip];
            twt[index as usize] += wt[ip];
            let wsum2 = nwt[index as usize];
            let child = 2 * index + 1;
            if (child as usize) < ntree {
                wsum1 += twt[child as usize];
            }
            while index > 0 {
                let parent = (index - 1) / 2;
                twt[parent as usize] += wt[ip];
                if index & 1 == 0 {
                    wsum1 += twt[parent as usize] - twt[index as usize];
                }
                index = parent;
            }
            let wsum3 = twt[0] - (wsum1 + wsum2);
            let lmean = wsum1 / 2.0;
            let umean = wsum1 + wsum2 + wsum3 / 2.0;
            let newmean = twt[0] / 2.0;
            let myrank = wsum1 + wsum2 / 2.0;
            vss += wsum1 * (newmean + oldmean - 2.0 * lmean) * (newmean - oldmean);
            vss += wsum3 * (newmean + oldmean + wt[ip] - 2.0 * umean) * (oldmean - newmean);
            vss += wt[ip] * (myrank - newmean) * (myrank - newmean);
            i += 1;
        }
        count[4] += ndeath * vss / twt[0];
    }
    count
}

/// Milliseconds for one [`concordance1`] call, measured with [`std::time::Instant`].
pub fn concordance1_ms(
    time: &[f64],
    status: &[f64],
    wt: &[f64],
    indx: &[i32],
    ntree: usize,
) -> ([f64; 5], f64) {
    let started = std::time::Instant::now();
    let count = concordance1(time, status, wt, indx, ntree);
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    (count, ms)
}

/// Milliseconds for one [`concordance2`] call, measured with [`std::time::Instant`].
pub fn concordance2_ms(
    start: &[f64],
    stop: &[f64],
    status: &[f64],
    wt: &[f64],
    indx: &[i32],
    ntree: usize,
    sort_stop: &[i32],
    sort_start: &[i32],
) -> ([f64; 5], f64) {
    let started = std::time::Instant::now();
    let count = concordance2(start, stop, status, wt, indx, ntree, sort_stop, sort_start);
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    (count, ms)
}

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::ArrayView2;
    use numpy::{PyArray1, PyReadonlyArray1, PyReadonlyArray2};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{concordance1_ms, concordance2_ms};

    fn f64_col(y: &ArrayView2<'_, f64>, col: usize) -> Vec<f64> {
        (0..y.nrows()).map(|i| y[[i, col]]).collect()
    }

    fn owned_f64(array: &PyReadonlyArray1<'_, f64>) -> PyResult<Vec<f64>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    fn owned_i32(array: &PyReadonlyArray1<'_, i32>) -> PyResult<Vec<i32>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    fn check_index(indx: &[i32], ntree: usize, what: &str) -> PyResult<()> {
        for &index in indx {
            if index < 0 || index as usize >= ntree {
                return Err(PyValueError::new_err(format!(
                    "{what} index {index} is outside 0..{ntree}"
                )));
            }
        }
        Ok(())
    }

    fn check_sort(sort: &[i32], n: usize, what: &str) -> PyResult<()> {
        if sort.len() != n {
            return Err(PyValueError::new_err(format!(
                "{what} length {} != {n}",
                sort.len()
            )));
        }
        for &index in sort {
            if index < 0 || index as usize >= n {
                return Err(PyValueError::new_err(format!(
                    "{what} index {index} is outside 0..{n}"
                )));
            }
        }
        Ok(())
    }

    #[pyfunction]
    #[pyo3(name = "concordance1")]
    fn concordance1_py<'py>(
        py: Python<'py>,
        y: PyReadonlyArray2<'py, f64>,
        wt: PyReadonlyArray1<'py, f64>,
        indx: PyReadonlyArray1<'py, i32>,
        ntree: usize,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let (count, _) = concordance1_checked(y, wt, indx, ntree)?;
        Ok(PyArray1::from_vec(py, count.to_vec()))
    }

    #[pyfunction]
    #[pyo3(name = "concordance1_ms")]
    fn concordance1_ms_py<'py>(
        py: Python<'py>,
        y: PyReadonlyArray2<'py, f64>,
        wt: PyReadonlyArray1<'py, f64>,
        indx: PyReadonlyArray1<'py, i32>,
        ntree: usize,
    ) -> PyResult<(Bound<'py, PyArray1<f64>>, f64)> {
        let (count, ms) = concordance1_checked(y, wt, indx, ntree)?;
        Ok((PyArray1::from_vec(py, count.to_vec()), ms))
    }

    fn concordance1_checked(
        y: PyReadonlyArray2<'_, f64>,
        wt: PyReadonlyArray1<'_, f64>,
        indx: PyReadonlyArray1<'_, i32>,
        ntree: usize,
    ) -> PyResult<([f64; 5], f64)> {
        let y = y.as_array();
        if y.ncols() != 2 {
            return Err(PyValueError::new_err("concordance1 y must have 2 columns"));
        }
        let n = y.nrows();
        let wt = owned_f64(&wt)?;
        let indx = owned_i32(&indx)?;
        if wt.len() != n || indx.len() != n {
            return Err(PyValueError::new_err(
                "concordance1 lengths must match nrow(y)",
            ));
        }
        if ntree == 0 && n > 0 {
            return Err(PyValueError::new_err("concordance1 ntree must be positive"));
        }
        check_index(&indx, ntree.max(1), "concordance1")?;
        let time = f64_col(&y, 0);
        let status = f64_col(&y, 1);
        Ok(concordance1_ms(&time, &status, &wt, &indx, ntree))
    }

    #[pyfunction]
    #[pyo3(name = "concordance2")]
    fn concordance2_py<'py>(
        py: Python<'py>,
        y: PyReadonlyArray2<'py, f64>,
        wt: PyReadonlyArray1<'py, f64>,
        indx: PyReadonlyArray1<'py, i32>,
        ntree: usize,
        sort_stop: PyReadonlyArray1<'py, i32>,
        sort_start: PyReadonlyArray1<'py, i32>,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let (count, _) = concordance2_checked(y, wt, indx, ntree, sort_stop, sort_start)?;
        Ok(PyArray1::from_vec(py, count.to_vec()))
    }

    #[pyfunction]
    #[pyo3(name = "concordance2_ms")]
    fn concordance2_ms_py<'py>(
        py: Python<'py>,
        y: PyReadonlyArray2<'py, f64>,
        wt: PyReadonlyArray1<'py, f64>,
        indx: PyReadonlyArray1<'py, i32>,
        ntree: usize,
        sort_stop: PyReadonlyArray1<'py, i32>,
        sort_start: PyReadonlyArray1<'py, i32>,
    ) -> PyResult<(Bound<'py, PyArray1<f64>>, f64)> {
        let (count, ms) = concordance2_checked(y, wt, indx, ntree, sort_stop, sort_start)?;
        Ok((PyArray1::from_vec(py, count.to_vec()), ms))
    }

    fn concordance2_checked(
        y: PyReadonlyArray2<'_, f64>,
        wt: PyReadonlyArray1<'_, f64>,
        indx: PyReadonlyArray1<'_, i32>,
        ntree: usize,
        sort_stop: PyReadonlyArray1<'_, i32>,
        sort_start: PyReadonlyArray1<'_, i32>,
    ) -> PyResult<([f64; 5], f64)> {
        let y = y.as_array();
        if y.ncols() != 3 {
            return Err(PyValueError::new_err(
                "concordance2 y must have 3 columns (start, stop, status)",
            ));
        }
        let n = y.nrows();
        let wt = owned_f64(&wt)?;
        let indx = owned_i32(&indx)?;
        let sort_stop = owned_i32(&sort_stop)?;
        let sort_start = owned_i32(&sort_start)?;
        if wt.len() != n || indx.len() != n {
            return Err(PyValueError::new_err(
                "concordance2 lengths must match nrow(y)",
            ));
        }
        if ntree == 0 && n > 0 {
            return Err(PyValueError::new_err("concordance2 ntree must be positive"));
        }
        check_index(&indx, ntree.max(1), "concordance2")?;
        check_sort(&sort_stop, n, "sort_stop")?;
        check_sort(&sort_start, n, "sort_start")?;
        let start = f64_col(&y, 0);
        let stop = f64_col(&y, 1);
        let status = f64_col(&y, 2);
        Ok(concordance2_ms(
            &start,
            &stop,
            &status,
            &wt,
            &indx,
            ntree,
            &sort_stop,
            &sort_start,
        ))
    }

    #[pymodule]
    fn survconc(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(concordance1_py, m)?)?;
        m.add_function(wrap_pyfunction!(concordance2_py, m)?)?;
        m.add_function(wrap_pyfunction!(concordance1_ms_py, m)?)?;
        m.add_function(wrap_pyfunction!(concordance2_ms_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn concordance1_three_rows() {
        let time = [1.0, 2.0, 3.0];
        let status = [1.0, 0.0, 1.0];
        let wt = [1.0, 1.0, 1.0];
        let indx = [0, 1, 0];
        let count = concordance1(&time, &status, &wt, &indx, 2);
        assert_eq!(count, [1.0, 0.0, 1.0, 0.0, 0.5]);
    }

    #[test]
    fn concordance2_censored_does_not_walk_past_end() {
        let start = [0.0];
        let stop = [1.0];
        let status = [0.0];
        let wt = [1.0];
        let indx = [0];
        let count = concordance2(&start, &stop, &status, &wt, &indx, 1, &[0], &[0]);
        assert_eq!(count, [0.0, 0.0, 0.0, 0.0, 0.0]);
    }
}
