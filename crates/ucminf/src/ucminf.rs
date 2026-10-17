//! UCMINF from ucminf 1.2.3 src/fortran.f.

use crate::blas::{daxpy, dcopy, ddot, dnrm2, dscal, dspr, dspr2, dspmv, idamax};

pub struct UcminfOut {
    pub convergence: i32,
    pub value: f64,
    pub maxgradient: f64,
    pub laststep: f64,
    pub neval: i32,
}

struct Eval<'a> {
    func: &'a mut dyn FnMut(&[f64]) -> f64,
    grad: &'a mut dyn FnMut(&[f64]) -> Vec<f64>,
    mode: i32,
    step: [f64; 2],
}

impl Eval<'_> {
    fn fdf(&mut self, x: &[f64], g: &mut [f64]) -> f64 {
        let f = (self.func)(x);
        if self.mode == 0 {
            let user = (self.grad)(x);
            g.copy_from_slice(&user[..x.len()]);
        } else {
            let forward = self.mode == 1;
            let n = x.len();
            let mut trial = vec![0.0; n];
            for i in 0..n {
                trial.copy_from_slice(x);
                let dx = trial[i].abs() * self.step[0] + self.step[1];
                trial[i] += dx;
                let f2 = (self.func)(&trial);
                if forward {
                    g[i] = (f2 - f) / dx;
                } else {
                    trial[i] -= 2.0 * dx;
                    let f3 = (self.func)(&trial);
                    g[i] = (f2 - f3) / (2.0 * dx);
                }
            }
        }
        f
    }
}

fn spchol(n: usize, a: &mut [f64]) -> i32 {
    let mut kk = 0usize;
    for k in 0..n {
        if a[kk] <= 0.0 {
            return (k + 1) as i32;
        }
        a[kk] = a[kk].sqrt();
        if k + 1 < n {
            let nk = n - k - 1;
            dscal(nk, 1.0 / a[kk], &mut a[kk + 1..]);
            let kn = kk + nk + 1;
            let column = a[kk + 1..kk + 1 + nk].to_vec();
            dspr(nk, -1.0, &column, &mut a[kn..]);
            kk = kn;
        }
    }
    0
}

fn sline(x: &[f64], f: f64, g: &mut [f64], h: &[f64], eval: &mut Eval<'_>) -> (f64, f64, [f64; 2], i32) {
    let n = x.len();
    let mut alpha = 0.0;
    let mut fn_value = f;
    let meval = 5i32;
    let mut slps = [0.0; 2];
    slps[0] = ddot(n, g, h);
    slps[1] = slps[0];
    if slps[0] >= 0.0 {
        return (alpha, fn_value, slps, 0);
    }
    let fi0 = f;
    let sl0 = 5e-2 * slps[0];
    let slthr = 0.995 * slps[0];
    let mut ok = false;
    let mut xfd = [[0.0; 3]; 3];
    xfd[0][0] = 0.0;
    xfd[1][0] = f;
    xfd[2][0] = slps[0];
    let mut nev = 0i32;
    let mut b = 1.0;
    let mut point = vec![0.0; n];
    let mut slope = vec![0.0; n];
    loop {
        xfd[0][1] = b;
        dcopy(n, x, &mut point);
        daxpy(n, b, h, &mut point);
        let value = eval.fdf(&point, &mut slope);
        nev += 1;
        xfd[1][1] = value;
        xfd[2][1] = ddot(n, &slope, h);
        if b == 1.0 {
            slps[1] = xfd[2][1];
        }
        if xfd[1][1] <= fi0 + sl0 * xfd[0][1] && xfd[2][1] <= slthr.abs() {
            ok = true;
            alpha = xfd[0][1];
            fn_value = xfd[1][1];
            slps[1] = xfd[2][1];
            dcopy(n, &slope, g);
            if b < 2.0 && xfd[2][1] < slthr {
                xfd[0][0] = xfd[0][1];
                xfd[1][0] = xfd[1][1];
                xfd[2][0] = xfd[2][1];
                b = 2.0;
                continue;
            }
        }
        let mut d = xfd[0][1] - xfd[0][0];
        loop {
            if ok || nev == meval {
                return (alpha, fn_value, slps, nev);
            }
            let c = xfd[1][1] - xfd[1][0] - d * xfd[2][0];
            let trial = if c > 1e-15 * (n as f64) * xfd[0][1] {
                let a = xfd[0][0] - 0.5 * xfd[2][0] * ((d * d) / c);
                d *= 0.1;
                (xfd[0][0] + d).max(a).min(xfd[0][1] - d)
            } else {
                0.5 * (xfd[0][0] + xfd[0][1])
            };
            xfd[0][2] = trial;
            dcopy(n, x, &mut point);
            daxpy(n, xfd[0][2], h, &mut point);
            let value = eval.fdf(&point, &mut slope);
            nev += 1;
            xfd[1][2] = value;
            xfd[2][2] = ddot(n, &slope, h);
            if xfd[1][2] < fi0 + sl0 * xfd[0][2] {
                ok = true;
                alpha = xfd[0][2];
                fn_value = xfd[1][2];
                slps[1] = xfd[2][2];
                dcopy(n, &slope, g);
                xfd[0][0] = xfd[0][2];
                xfd[1][0] = xfd[1][2];
                xfd[2][0] = xfd[2][2];
            } else {
                xfd[0][1] = xfd[0][2];
                xfd[1][1] = xfd[1][2];
                xfd[2][1] = xfd[2][2];
            }
            d = xfd[0][1] - xfd[0][0];
            ok = ok && xfd[2][2].abs() <= slthr.abs();
            ok = ok || d <= 0.0;
        }
    }
}

pub fn ucminf(
    x: &mut [f64],
    dx: &mut f64,
    eps: [f64; 2],
    maxfun: &mut i32,
    w: &mut [f64],
    icontr: &mut i32,
    grad_mode: i32,
    grstep: [f64; 2],
    func: &mut dyn FnMut(&[f64]) -> f64,
    grad: &mut dyn FnMut(&[f64]) -> Vec<f64>,
) -> UcminfOut {
    let n = x.len();
    let optim = *icontr > 0;
    let given = *icontr > 2;
    *icontr = 0;
    let nn = n * (n + 1) / 2;
    if n == 0 {
        *icontr = -2;
    } else if optim {
        if *dx <= 0.0 {
            *icontr = -4;
        } else if eps[0] <= 0.0 || eps[1] <= 0.0 {
            *icontr = -5;
        } else if *maxfun <= 0 {
            *icontr = -6;
        }
    }
    if *icontr < 0 {
        return UcminfOut { convergence: *icontr, value: 0.0, maxgradient: 0.0, laststep: 0.0, neval: 0 };
    }
    let mut eval = Eval { func, grad, mode: grad_mode, step: grstep };
    let gp = n + 1;
    let gn = gp + n;
    let hn = gn + n;
    let dn = hn + n;
    if given {
        let nn1 = nn + 1;
        let saved = w[dn - 1..dn - 1 + nn].to_vec();
        w[..nn].copy_from_slice(&saved);
        let saved = w[..nn].to_vec();
        w[nn1 - 1..nn1 - 1 + nn].copy_from_slice(&saved);
        let fail = spchol(n, &mut w[nn1 - 1..]);
        if fail != 0 {
            *icontr = -7;
            return UcminfOut { convergence: *icontr, value: 0.0, maxgradient: 0.0, laststep: 0.0, neval: 0 };
        }
        for k in (0..nn).rev() {
            w[dn - 1 + k] = w[k];
        }
    } else {
        for i in hn - 1..dn - 1 + nn {
            w[i] = 0.0;
        }
        let mut ii = dn;
        let mut diag = n;
        for _ in 0..n {
            w[ii - 1] = 1.0;
            ii += diag;
            diag -= 1;
        }
    }
    let mut g = vec![0.0; n];
    let mut fx = eval.fdf(x, &mut g);
    g_store(w, gn, &g);
    let mut neval = 1i32;
    let mut nmh = 0.0;
    let mut nmx = dnrm2(n, x);
    let mut nmg = w[gn - 1 + idamax(n, &w[gn - 1..gn - 1 + n]) - 1].abs();
    let mut used_identity = !given;
    if nmg <= eps[0] {
        *icontr = 1;
    } else {
        loop {
            dcopy(n, x, &mut w[..n]);
            let gradient = w[gn - 1..gn - 1 + n].to_vec();
            dcopy(n, &gradient, &mut w[gp - 1..gp - 1 + n]);
            {
                let (left, right) = w.split_at_mut(dn - 1);
                let gradient = left[gn - 1..gn - 1 + n].to_vec();
                let mut step = vec![0.0; n];
                dspmv(n, -1.0, &right[..nn], &gradient, 0.0, &mut step);
                left[hn - 1..hn - 1 + n].copy_from_slice(&step);
            }
            let mut reduced = false;
            nmh = dnrm2(n, &w[hn - 1..hn - 1 + n]);
            if nmh <= eps[1] * (eps[1] + nmx) {
                *icontr = 2;
                break;
            }
            if nmh > *dx || used_identity {
                reduced = true;
                dscal(n, *dx / nmh, &mut w[hn - 1..hn - 1 + n]);
                used_identity = false;
            }
            let h = w[hn - 1..hn - 1 + n].to_vec();
            g.copy_from_slice(&w[gn - 1..gn - 1 + n]);
            let (alpha, fxn, sl, meval) = sline(x, fx, &mut g, &h, &mut eval);
            if alpha == 0.0 {
                *icontr = 4;
                nmh = 0.0;
                g_store(w, gn, &g);
                break;
            }
            neval += meval;
            g_store(w, gn, &g);
            nmg = w[gn - 1 + idamax(n, &w[gn - 1..gn - 1 + n]) - 1].abs();
            fx = fxn;
            daxpy(n, alpha, &h, x);
            nmx = dnrm2(n, x);
            daxpy(n, -1.0, x, &mut w[..n]);
            nmh = dnrm2(n, &w[..n]);
            if alpha < 1.0 {
                *dx *= 0.35;
            } else if reduced && sl[1] < 0.7 * sl[0] {
                *dx *= 3.0;
            }
            dscal(n, -1.0, &mut w[..n]);
            let new_gradient = w[gn - 1..gn - 1 + n].to_vec();
            daxpy(n, -1.0, &new_gradient, &mut w[gp - 1..gp - 1 + n]);
            let yh = -ddot(n, &w[gp - 1..gp - 1 + n], &w[..n]);
            if yh > 1e-8 * nmh * dnrm2(n, &w[gp - 1..gp - 1 + n]) {
                let gp_vec = w[gp - 1..gp - 1 + n].to_vec();
                let mut hv = vec![0.0; n];
                {
                    let ap = &w[dn - 1..dn - 1 + nn];
                    dspmv(n, -1.0, ap, &gp_vec, 0.0, &mut hv);
                }
                let yv = -ddot(n, &gp_vec, &hv);
                let a = (1.0 + yv / yh) / yh;
                dscal(n, -1.0 / yh, &mut hv);
                daxpy(n, 0.5 * a, &w[..n], &mut hv);
                let s = w[..n].to_vec();
                dspr2(n, 1.0, &s, &hv, &mut w[dn - 1..dn - 1 + nn]);
            }
            let thrx = eps[1] * (eps[1] + nmx);
            *dx = dx.max(thrx);
            if neval >= *maxfun {
                *icontr = 3;
            }
            if nmh <= thrx {
                *icontr = 2;
            }
            if nmg <= eps[0] {
                *icontr = 1;
            }
            if *icontr != 0 {
                break;
            }
        }
    }
    *maxfun = neval;
    w[0] = fx;
    w[1] = nmg;
    w[2] = nmh;
    UcminfOut { convergence: *icontr, value: fx, maxgradient: nmg, laststep: nmh, neval }
}

fn g_store(w: &mut [f64], gn: usize, g: &[f64]) {
    w[gn - 1..gn - 1 + g.len()].copy_from_slice(g);
}
