//! deSolve `getLagDeriv` / Hermite history derivative lookup from `src/lags.c` (method 1).

#[derive(Clone, Debug)]
pub struct HistoryState {
    pub n_eq: usize,
    pub histsize: usize,
    pub offset: usize,
    pub indexhist: i32,
    pub starthist: i32,
    pub endreached: i32,
    pub initialisehist: i32,
    pub interpol_method: i32,
    pub histtime: Vec<f64>,
    pub histvar: Vec<f64>,
    pub histdvar: Vec<f64>,
}

impl Default for HistoryState {
    fn default() -> Self {
        Self {
            n_eq: 0,
            histsize: 0,
            offset: 0,
            indexhist: -1,
            starthist: 0,
            endreached: 0,
            initialisehist: 0,
            interpol_method: 1,
            histtime: Vec::new(),
            histvar: Vec::new(),
            histdvar: Vec::new(),
        }
    }
}

impl HistoryState {
    pub fn restore(
        n_eq: usize,
        histsize: usize,
        indexhist: i32,
        starthist: i32,
        endreached: i32,
        offset: usize,
        interpol_method: i32,
        histtime: Vec<f64>,
        histvar: Vec<f64>,
        histdvar: Vec<f64>,
    ) -> Self {
        let mut state = Self::default();
        state.n_eq = n_eq;
        state.histsize = histsize;
        state.indexhist = indexhist;
        state.starthist = starthist;
        state.endreached = endreached;
        state.offset = offset;
        state.interpol_method = interpol_method;
        state.initialisehist = 1;
        state.histtime = histtime;
        state.histvar = histvar;
        state.histdvar = histdvar;
        state
    }

    fn nexthist(&mut self, i: i32) -> i32 {
        if i < self.histsize as i32 - 1 {
            i + 1
        } else {
            self.endreached = 1;
            0
        }
    }

    fn d_hermite(t0: f64, t1: f64, y0: f64, y1: f64, dy0: f64, dy1: f64, t: f64) -> f64 {
        let tt0 = t - t0;
        let tt1 = t - t1;
        let tt12 = tt1 * tt1;
        let tt02 = tt0 * tt0;
        let hh = t1 - t0;
        if hh != 0.0 {
            (dy0 * (tt12 + 2.0 * tt0 * tt1)
                + dy1 * (tt02 + 2.0 * tt0 * tt1)
                + (y0 * 2.0 * tt1 * (2.0 * tt0 + hh + tt1)
                    - y1 * 2.0 * tt0 * (2.0 * tt1 - hh + tt0))
                    / hh)
                / (hh * hh)
        } else {
            dy0
        }
    }

    fn find_hist_int(&self, t: f64) -> Result<i32, String> {
        let indexhist = self.indexhist;
        if t >= self.histtime[indexhist as usize] {
            return Ok(indexhist);
        }
        if t < self.histtime[self.starthist as usize] {
            return Err(format!(
                "illegal input in lagvalue - lag, {t}, too large, at time = {}\n",
                self.histtime[indexhist as usize]
            ));
        }
        if self.endreached == 0 {
            let mut ilo = 0;
            let mut ihi = indexhist;
            loop {
                let imid = (ilo + ihi) / 2;
                if imid == ilo {
                    return Ok(ilo);
                }
                if t >= self.histtime[imid as usize] {
                    ilo = imid;
                } else {
                    ihi = imid;
                }
            }
        }
        let n = self.histsize as i32 - 1;
        let mut ilo = 0;
        let mut ihi = n;
        loop {
            let imid = (ilo + ihi) / 2;
            let mut ii = imid + self.starthist;
            if ii > n {
                ii -= n + 1;
            }
            if imid == ilo {
                return Ok(ii);
            }
            if t >= self.histtime[ii as usize] {
                ilo = imid;
            } else {
                ihi = imid;
            }
        }
    }

    fn past_deriv(&mut self, i: usize, interval: i32, t: f64) -> Result<f64, String> {
        if i >= self.n_eq {
            return Err(format!(
                "illegal input in lagvalue - var nr too high, {}",
                i + 1
            ));
        }
        let offset = self.offset;
        let n_eq = self.n_eq;
        if interval == self.indexhist && t == self.histtime[interval as usize] {
            return Ok(self.histdvar[interval as usize * offset + i]);
        }
        if interval == self.indexhist && self.interpol_method == 1 {
            return Ok(self.histdvar[interval as usize * n_eq + i]);
        }
        if self.interpol_method == 1 {
            let j = interval;
            let jn = self.nexthist(j);
            let t0 = self.histtime[j as usize];
            let t1 = self.histtime[jn as usize];
            let y0 = self.histvar[j as usize * n_eq + i];
            let y1 = self.histvar[jn as usize * n_eq + i];
            let dy0 = self.histdvar[j as usize * n_eq + i];
            let dy1 = self.histdvar[jn as usize * n_eq + i];
            return Ok(Self::d_hermite(t0, t1, y0, y1, dy0, dy1, t));
        }
        Err(format!(
            "interpol_method {} not supported in lagderiv",
            self.interpol_method
        ))
    }

    pub fn get_lag_deriv(&mut self, t: f64, nr: &[i32]) -> Result<Vec<f64>, String> {
        if self.initialisehist == 0 {
            return Err(
                "pastgradient can only be called from 'func' or 'res' when triggered by appropriate integrator.".into(),
            );
        }
        let interval = self.find_hist_int(t)?;
        if nr.len() == 1 && nr[0] == 0 {
            let mut out = Vec::with_capacity(self.n_eq);
            for i in 0..self.n_eq {
                out.push(self.past_deriv(i, interval, t)?);
            }
            return Ok(out);
        }
        let mut out = Vec::with_capacity(nr.len());
        for &n in nr {
            let idx = (n - 1) as usize;
            out.push(self.past_deriv(idx, interval, t)?);
        }
        Ok(out)
    }
}

#[cfg(feature = "python")]
mod python {
    use super::HistoryState;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyList};
    use std::sync::Mutex;

    static STATE: Mutex<Option<HistoryState>> = Mutex::new(None);

    fn state_mut() -> PyResult<std::sync::MutexGuard<'static, Option<HistoryState>>> {
        STATE
            .lock()
            .map_err(|_| PyValueError::new_err("lagderiv history lock poisoned"))
    }

    #[pyfunction]
    fn restore_hist(snapshot: &Bound<'_, PyDict>) -> PyResult<()> {
        let get_i = |key: &'static str| -> PyResult<i32> {
            snapshot
                .get_item(key)?
                .ok_or_else(|| PyValueError::new_err(key))?
                .extract()
        };
        let get_vec = |key: &'static str| -> PyResult<Vec<f64>> {
            snapshot
                .get_item(key)?
                .ok_or_else(|| PyValueError::new_err(key))?
                .extract()
        };
        let state = HistoryState::restore(
            get_i("n_eq")? as usize,
            get_i("histsize")? as usize,
            get_i("indexhist")?,
            get_i("starthist")?,
            get_i("endreached")?,
            get_i("offset")? as usize,
            get_i("interpolMethod")?,
            get_vec("histtime")?,
            get_vec("histvar")?,
            get_vec("histdvar")?,
        );
        *state_mut()? = Some(state);
        Ok(())
    }

    #[pyfunction]
    fn lagderiv_kernel(t: f64, nr: Option<Bound<'_, PyList>>) -> PyResult<Vec<f64>> {
        let nr_vec: Vec<i32> = match nr {
            None => vec![0],
            Some(list) => list.extract()?,
        };
        let mut guard = state_mut()?;
        let state = guard
            .as_mut()
            .ok_or_else(|| PyValueError::new_err("history not initialised"))?;
        state
            .get_lag_deriv(t, &nr_vec)
            .map_err(PyValueError::new_err)
    }

    #[pymodule]
    fn lagderiv(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(restore_hist, m)?)?;
        m.add_function(wrap_pyfunction!(lagderiv_kernel, m)?)?;
        Ok(())
    }
}
