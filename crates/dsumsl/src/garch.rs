//! GARCH(p, q) likelihood from tseries `src/garch.c`.
//!
//! `fit_garch` calls PORT `DSUMSL` (analytic gradient) or `DSMSNO`
//! (finite differences). The coefficient vector is 0-based here:
//! `a0, a1..aq, b1..bp`.

use crate::driver::{dsmsno, dsumsl};
use crate::work::{ddeflt, Work};

const BIG: f64 = 1.0e10;

struct Series {
    y: Vec<f64>,
    h: Vec<f64>,
    dh: Vec<f64>,
    p: usize,
    q: usize,
}

fn maxpq(p: usize, q: usize) -> usize {
    p.max(q)
}

impl Series {
    fn new(y: &[f64], p: usize, q: usize) -> Self {
        let n = y.len();
        let pq = p + q + 1;
        let mut h = vec![0.0; n];
        let mut dh = vec![0.0; n * pq];
        let mut var = 0.0;
        for value in y {
            var += value * value;
        }
        var /= n as f64;
        let warm = maxpq(p, q);
        for i in 0..warm {
            h[i] = var;
            dh[pq * i] = 1.0;
        }
        Self {
            y: y.to_vec(),
            h,
            dh,
            p,
            q,
        }
    }

    fn valid(par: &[f64]) -> bool {
        if par[0] <= 0.0 {
            return false;
        }
        par[1..].iter().all(|value| *value >= 0.0)
    }

    fn calcf(&mut self, par: &[f64]) -> f64 {
        if !Self::valid(par) {
            return BIG;
        }
        let n = self.y.len();
        let warm = maxpq(self.p, self.q);
        let mut sum = 0.0;
        for i in warm..n {
            let mut temp = par[0];
            for j in 1..=self.q {
                let yj = self.y[i - j];
                temp += par[j] * yj * yj;
            }
            for j in 1..=self.p {
                temp += par[self.q + j] * self.h[i - j];
            }
            let yi = self.y[i];
            sum += temp.ln() + yi * yi / temp;
            self.h[i] = temp;
        }
        0.5 * sum
    }

    fn calcg(&mut self, par: &[f64], grad: &mut [f64]) {
        let pq = self.p + self.q + 1;
        let n = self.y.len();
        let warm = maxpq(self.p, self.q);
        for value in grad.iter_mut() {
            *value = 0.0;
        }
        for i in warm..n {
            let mut temp1 = par[0];
            for j in 1..=self.q {
                let yj = self.y[i - j];
                temp1 += par[j] * yj * yj;
            }
            for j in 1..=self.p {
                temp1 += par[self.q + j] * self.h[i - j];
            }
            self.h[i] = temp1;
            let yi = self.y[i];
            let temp2 = 0.5 * (1.0 - yi * yi / temp1) / temp1;
            let mut temp3 = 1.0;
            for j in 1..=self.p {
                temp3 += par[self.q + j] * self.dh[pq * (i - j)];
            }
            self.dh[pq * i] = temp3;
            grad[0] += temp2 * temp3;
            for k in 1..=self.q {
                let yk = self.y[i - k];
                let mut temp3 = yk * yk;
                for j in 1..=self.p {
                    temp3 += par[self.q + j] * self.dh[pq * (i - j) + k];
                }
                self.dh[pq * i + k] = temp3;
                grad[k] += temp2 * temp3;
            }
            for k in 1..=self.p {
                let mut temp3 = self.h[i - k];
                for j in 1..=self.p {
                    temp3 += par[self.q + j] * self.dh[pq * (i - j) + self.q + k];
                }
                self.dh[pq * i + self.q + k] = temp3;
                grad[self.q + k] += temp2 * temp3;
            }
        }
    }
}

fn read_coef(w: &Work, par: &mut [f64]) {
    for (i, value) in par.iter_mut().enumerate() {
        *value = w.xg((i as i32) + 1);
    }
}

fn write_grad(w: &mut Work, grad: &[f64]) {
    let g1 = w.g1;
    for (i, value) in grad.iter().enumerate() {
        w.sv(g1, (i as i32) + 1, *value);
    }
}

pub fn fit_garch(
    y: &[f64],
    start: &[f64],
    p: i32,
    q: i32,
    maxiter: i32,
    abstol: f64,
    reltol: f64,
    xtol: f64,
    falsetol: f64,
    analytical: bool,
    trace: bool,
) -> (Vec<f64>, f64) {
    let p = p as usize;
    let q = q as usize;
    let ncoef = (p + q + 1) as i32;
    let liv = 60i32;
    let lv = 77 + ncoef * (ncoef + 17) / 2;
    let mut w = Work::new(ncoef, start, liv, lv);
    ddeflt(&mut w, 2);
    w.iset(1, 12);
    w.iset(17, 2 * maxiter);
    w.iset(18, maxiter);
    w.iset(21, if trace { 6 } else { 0 });
    w.vs(31, abstol);
    w.vs(32, reltol);
    w.vs(33, xtol);
    w.vs(34, falsetol);
    let series = std::cell::RefCell::new(Series::new(y, p, q));
    let par = std::cell::RefCell::new(start.to_vec());
    if analytical {
        dsumsl(
            &mut w,
            |w, _nf| {
                let mut par = par.borrow_mut();
                read_coef(w, &mut par);
                w.fx = series.borrow_mut().calcf(&par);
            },
            |w, _nf| {
                let mut par = par.borrow_mut();
                read_coef(w, &mut par);
                let mut grad = vec![0.0; par.len()];
                series.borrow_mut().calcg(&par, &mut grad);
                write_grad(w, &grad);
            },
        );
    } else {
        dsmsno(&mut w, |w, _nf| {
            let mut par = par.borrow_mut();
            read_coef(w, &mut par);
            w.fx = series.borrow_mut().calcf(&par);
        });
    }
    let mut par = par.borrow().clone();
    read_coef(&w, &mut par);
    (par, w.vg(10))
}

pub fn pred_garch(y: &[f64], par: &[f64], p: i32, q: i32, genuine: bool) -> Vec<f64> {
    let p = p as usize;
    let q = q as usize;
    let n = y.len();
    let horizon = if genuine { n + 1 } else { n };
    let mut h = vec![0.0; horizon];
    let mut var = 0.0;
    for i in 1..=p + q {
        var += par[i];
    }
    var = par[0] / (1.0 - var);
    let warm = maxpq(p, q);
    for value in h.iter_mut().take(warm) {
        *value = var;
    }
    for i in warm..horizon {
        let mut temp = par[0];
        for j in 1..=q {
            let yj = y[i - j];
            temp += par[j] * yj * yj;
        }
        for j in 1..=p {
            temp += par[q + j] * h[i - j];
        }
        h[i] = temp;
    }
    h
}

pub fn ophess_garch(y: &[f64], par: &[f64], p: i32, q: i32) -> Vec<f64> {
    let p = p as usize;
    let q = q as usize;
    let n = y.len();
    let pq = p + q + 1;
    let mut h = vec![0.0; n];
    let mut dh = vec![0.0; n * pq];
    let mut var = 0.0;
    for value in y {
        var += value * value;
    }
    var /= n as f64;
    let warm = maxpq(p, q);
    for i in 0..warm {
        h[i] = var;
        dh[pq * i] = 1.0;
    }
    let mut he = vec![0.0; pq * pq];
    let mut dpar = vec![0.0; pq];
    for i in warm..n {
        let mut temp1 = par[0];
        for j in 1..=q {
            let yj = y[i - j];
            temp1 += par[j] * yj * yj;
        }
        for j in 1..=p {
            temp1 += par[q + j] * h[i - j];
        }
        h[i] = temp1;
        let yi = y[i];
        let temp2 = 0.5 * (1.0 - yi * yi / temp1) / temp1;
        let mut temp3 = 1.0;
        for j in 1..=p {
            temp3 += par[q + j] * dh[pq * (i - j)];
        }
        dh[pq * i] = temp3;
        dpar[0] = temp2 * temp3;
        for k in 1..=q {
            let yk = y[i - k];
            let mut temp3 = yk * yk;
            for j in 1..=p {
                temp3 += par[q + j] * dh[pq * (i - j) + k];
            }
            dh[pq * i + k] = temp3;
            dpar[k] = temp2 * temp3;
        }
        for k in 1..=p {
            let mut temp3 = h[i - k];
            for j in 1..=p {
                temp3 += par[q + j] * dh[pq * (i - j) + q + k];
            }
            dh[pq * i + q + k] = temp3;
            dpar[q + k] = temp2 * temp3;
        }
        for k in 0..pq {
            for j in 0..pq {
                he[pq * k + j] += dpar[k] * dpar[j];
            }
        }
    }
    he
}
