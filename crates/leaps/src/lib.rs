//! Leaps-and-bounds exhaustive regression subset search, ported from leaps 3.2
//! `src/leaps.f` (Alan Miller's AS 274 routines).
//!
//! The kernel path is `MAKEQR` (with `INCLUD`), `TOLSET`, `SSLEAPS`, `SING`,
//! `INITR` and `XHAUST` (with `ADD1`, `EXADD1`, `REPORT`, `VMOVE`). The R
//! wrapper's intercept and `nvmax` bookkeeping is done by the caller, which
//! passes the augmented design matrix. Rank-deficient designs return an error.

pub mod setup;
pub mod xhaust;

/// Column-major matrix with 1-based `(row, col)` access, matching the Fortran
/// `RESS(IR, NBEST)` and `LOPT(IL, NBEST)` layout.
#[derive(Clone, Debug)]
pub struct Mat<T> {
    pub nrow: usize,
    pub ncol: usize,
    data: Vec<T>,
}

impl<T: Copy> Mat<T> {
    pub fn new(nrow: usize, ncol: usize, fill: T) -> Self {
        Mat {
            nrow,
            ncol,
            data: vec![fill; nrow * ncol],
        }
    }

    #[inline]
    pub fn get(&self, row: usize, col: usize) -> T {
        self.data[(col - 1) * self.nrow + (row - 1)]
    }

    #[inline]
    pub fn set(&mut self, row: usize, col: usize, value: T) {
        self.data[(col - 1) * self.nrow + (row - 1)] = value;
    }
}

/// Length of the packed `RBAR` array for `np` variables.
pub fn nrbar_for(np: usize) -> usize {
    if np == 0 {
        0
    } else {
        np * (np - 1) / 2
    }
}

/// Output of [`exhaustive`]. `ress` is `nvmax` x `nbest`, `lopt` is `il` x
/// `nbest` with `il = nvmax*(nvmax+1)/2`, and `rss` is indexed by position
/// (1-based, index 0 unused) before the search.
#[derive(Clone, Debug)]
pub struct Search {
    pub ress: Mat<f64>,
    pub lopt: Mat<usize>,
    pub rss: Vec<f64>,
}

/// Run the exhaustive leaps-and-bounds search on a design matrix.
///
/// `x` is row-major, `nn` x `np`, and should already contain the intercept
/// column when wanted. `first` is the first searchable position (2 with a
/// forced intercept, otherwise 1). `nvmax` is the largest subset size in
/// positions, and `nbest` is the number of subsets kept per size.
pub fn exhaustive(
    x: &[f64],
    nn: usize,
    np: usize,
    y: &[f64],
    wt: &[f64],
    first: usize,
    nvmax: usize,
    nbest: usize,
) -> Result<Search, String> {
    if np < 1 || nn < 1 {
        return Err("design must have at least one row and one column".into());
    }
    if x.len() != nn * np || y.len() != nn || wt.len() != nn {
        return Err("x, y and wt lengths disagree with the design shape".into());
    }
    if nbest == 0 || nvmax == 0 || nvmax > np {
        return Err("nbest and nvmax must be positive and nvmax <= ncol".into());
    }
    let nrbar = nrbar_for(np);

    let mut d = vec![0.0; np + 1];
    let mut rbar = vec![0.0; nrbar + 1];
    let mut thetab = vec![0.0; np + 1];
    let mut sserr = 0.0;
    let ier = setup::makeqr(np, x, y, wt, &mut d, &mut rbar, &mut thetab, &mut sserr);
    if ier != 0 {
        return Err(format!("MAKEQR returned error code {ier}"));
    }

    let mut tol = vec![0.0; np + 1];
    let ier = setup::tolset(np, nrbar, &d, &rbar, &mut tol);
    if ier != 0 {
        return Err(format!("TOLSET returned error code {ier}"));
    }

    let mut rss = vec![0.0; np + 1];
    let ier = setup::ssleaps(np, &d, &thetab, sserr, &mut rss);
    if ier != 0 {
        return Err(format!("SSLEAPS returned error code {ier}"));
    }
    let rss_initial = rss.clone();

    let mut lindep = vec![false; np + 1];
    let ier = setup::sing(
        np,
        nrbar,
        &mut d,
        &mut rbar,
        &mut thetab,
        &mut sserr,
        &tol,
        &mut lindep,
    );
    if ier > 0 {
        return Err(format!("SING returned error code {ier}"));
    }
    if lindep.iter().skip(1).any(|&flag| flag) {
        return Err(
            "rank-deficient design: leaps.setup reordering and nvmax reduction are not ported"
                .into(),
        );
    }

    let il = nvmax * (nvmax + 1) / 2;
    let mut bound = vec![0.0; np + 1];
    let mut ress = Mat::new(nvmax, nbest, 0.0);
    let mut lopt = Mat::new(il, nbest, 0usize);
    let mut vorder: Vec<usize> = (0..=np).collect();

    let ier = setup::initr(np, nvmax, &mut bound, &mut ress, &mut lopt, &vorder, &rss_initial);
    if ier != 0 {
        return Err(format!("INITR returned error code {ier}"));
    }

    let last = np;
    let ier = xhaust::xhaust(
        np,
        nrbar,
        &mut d,
        &mut rbar,
        &mut thetab,
        first,
        last,
        &mut vorder,
        &mut tol,
        &mut rss,
        &mut bound,
        nvmax,
        &mut ress,
        &mut lopt,
    );
    if ier != 0 {
        return Err(format!("XHAUST returned error code {ier}"));
    }

    Ok(Search {
        ress,
        lopt,
        rss: rss_initial,
    })
}

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::Array2;
    use numpy::{
        IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2, PyUntypedArrayMethods,
    };
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "exhaustive")]
    fn exhaustive_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray2<'py, f64>,
        y: PyReadonlyArray1<'py, f64>,
        wt: PyReadonlyArray1<'py, f64>,
        first: usize,
        nvmax: usize,
        nbest: usize,
    ) -> PyResult<(
        Bound<'py, PyArray2<f64>>,
        Bound<'py, PyArray2<i64>>,
        Bound<'py, PyArray1<f64>>,
    )> {
        let shape = x.shape().to_vec();
        let (nn, np) = (shape[0], shape[1]);
        let xs: Vec<f64> = x.as_array().iter().copied().collect();
        let ys: Vec<f64> = y.as_array().iter().copied().collect();
        let ws: Vec<f64> = wt.as_array().iter().copied().collect();

        let search = crate::exhaustive(&xs, nn, np, &ys, &ws, first, nvmax, nbest)
            .map_err(PyValueError::new_err)?;

        let ress = Array2::from_shape_fn((search.ress.nrow, search.ress.ncol), |(r, c)| {
            search.ress.get(r + 1, c + 1)
        });
        let lopt = Array2::from_shape_fn((search.lopt.nrow, search.lopt.ncol), |(r, c)| {
            search.lopt.get(r + 1, c + 1) as i64
        });
        let rss: Vec<f64> = search.rss[1..].to_vec();
        Ok((
            ress.into_pyarray(py),
            lopt.into_pyarray(py),
            rss.into_pyarray(py),
        ))
    }

    #[pymodule]
    fn leaps(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(exhaustive_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Deterministic pseudo-random values in (-1, 1).
    fn lcg(state: &mut u64) -> f64 {
        *state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        ((*state >> 11) as f64) / ((1u64 << 53) as f64) * 2.0 - 1.0
    }

    /// RSS of the least-squares fit on `[1, x[:, cols]]`, by normal equations.
    fn rss_for(x: &[Vec<f64>], y: &[f64], cols: &[usize]) -> f64 {
        let k = cols.len() + 1;
        let mut a = vec![vec![0.0; k]; k];
        let mut b = vec![0.0; k];
        let rows: Vec<Vec<f64>> = x
            .iter()
            .map(|r| {
                let mut v = vec![1.0];
                v.extend(cols.iter().map(|&c| r[c]));
                v
            })
            .collect();
        for (row, yi) in rows.iter().zip(y) {
            for p in 0..k {
                b[p] += row[p] * yi;
                for q in 0..k {
                    a[p][q] += row[p] * row[q];
                }
            }
        }
        // Gaussian elimination with partial pivoting.
        for col in 0..k {
            let piv = (col..k)
                .max_by(|&i, &j| a[i][col].abs().total_cmp(&a[j][col].abs()))
                .unwrap();
            a.swap(col, piv);
            b.swap(col, piv);
            for r in (col + 1)..k {
                let f = a[r][col] / a[col][col];
                for c in col..k {
                    a[r][c] -= f * a[col][c];
                }
                b[r] -= f * b[col];
            }
        }
        let mut beta = vec![0.0; k];
        for r in (0..k).rev() {
            let s: f64 = ((r + 1)..k).map(|c| a[r][c] * beta[c]).sum();
            beta[r] = (b[r] - s) / a[r][r];
        }
        rows.iter()
            .zip(y)
            .map(|(row, yi)| {
                let fit: f64 = row.iter().zip(&beta).map(|(v, b)| v * b).sum();
                (yi - fit) * (yi - fit)
            })
            .sum()
    }

    /// All subsets of `0..p` of size `k`.
    fn combos(p: usize, k: usize) -> Vec<Vec<usize>> {
        let mut out = Vec::new();
        for mask in 0u32..(1u32 << p) {
            if mask.count_ones() as usize == k {
                out.push((0..p).filter(|&i| mask & (1 << i) != 0).collect());
            }
        }
        out
    }

    #[test]
    fn best_subsets_match_brute_force() {
        let (n, p) = (30usize, 5usize);
        let mut state = 20261017u64;
        let x: Vec<Vec<f64>> = (0..n)
            .map(|_| (0..p).map(|_| lcg(&mut state)).collect())
            .collect();
        let y: Vec<f64> = x
            .iter()
            .map(|r| 1.0 + 2.0 * r[0] - r[2] + 0.3 * lcg(&mut state))
            .collect();

        let flat: Vec<f64> = x
            .iter()
            .flat_map(|r| std::iter::once(1.0).chain(r.iter().copied()))
            .collect();
        let np = p + 1;
        let wt = vec![1.0; n];
        let nbest = 3;
        let search = exhaustive(&flat, n, np, &y, &wt, 2, np, nbest).unwrap();

        for k in 1..=p {
            let mut rss: Vec<f64> = combos(p, k)
                .iter()
                .map(|c| {
                    let cols: Vec<usize> = c.clone();
                    rss_for(&x, &y, &cols)
                })
                .collect();
            rss.sort_by(|a, b| a.total_cmp(b));
            for rank in 1..=nbest.min(rss.len()) {
                let got = search.ress.get(k + 1, rank);
                let want = rss[rank - 1];
                assert!(
                    (got - want).abs() <= 1e-8 * want.max(1.0),
                    "size {k} rank {rank}: got {got}, want {want}"
                );
            }
        }
    }
}
