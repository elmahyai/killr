pub fn sign(x: f64) -> f64 {
    if x > 0.0 {
        1.0
    } else if x < 0.0 {
        -1.0
    } else {
        0.0
    }
}

pub fn blas_matprod1(x: &[f64], nrx: usize, ncx: usize, y: &[f64], _nry: usize, ncy: usize, z: &mut [f64]) {
    if nrx == 0 || ncx == 0 || ncy == 0 {
        for v in z.iter_mut().take(nrx * ncy) {
            *v = 0.0;
        }
        return;
    }
    for col in 0..ncy {
        for row in 0..nrx {
            let mut sum = 0.0;
            for k in 0..ncx {
                sum += x[row + nrx * k] * y[k + ncx * col];
            }
            z[row + nrx * col] = sum;
        }
    }
}

pub fn maxerr(y0: &[f64], y1: &[f64], y2: &[f64], atol: &[f64], rtol: &[f64], n: usize) -> f64 {
    let mut serr = 0.0;
    for i in 0..n {
        let scal = atol[i] + y0[i].abs().max(y2[i].abs()) * rtol[i];
        let delta = (y2[i] - y1[i]).abs();
        if scal > 0.0 {
            serr += (delta / scal).powi(2);
        }
    }
    (serr / n as f64).sqrt()
}

pub fn denspar(
    ff: &[f64],
    y0: &[f64],
    y1: &[f64],
    dt: f64,
    d: &[f64],
    neq: usize,
    stage: usize,
    r: &mut [f64],
) {
    for i in 0..neq {
        r[i] = y0[i];
        let ydiff = y1[i] - y0[i];
        r[i + neq] = ydiff;
        let bspl = dt * ff[i] - ydiff;
        r[i + 2 * neq] = bspl;
        r[i + 3 * neq] = ydiff - dt * ff[i + (stage - 1) * neq] - bspl;
        r[i + 4 * neq] = 0.0;
        for j in 0..stage {
            r[i + 4 * neq] += d[j] * ff[i + j * neq];
        }
        r[i + 4 * neq] *= dt;
    }
}

pub fn densout(r: &[f64], t0: f64, t: f64, dt: f64, res: &mut [f64], neq: usize) {
    let s = (t - t0) / dt;
    let s1 = 1.0 - s;
    for i in 0..neq {
        res[i] = r[i]
            + s * (r[i + neq]
                + s1 * (r[i + 2 * neq] + s * (r[i + 3 * neq] + s1 * r[i + 4 * neq])));
    }
}

pub fn densoutck(t0: f64, t: f64, dt: f64, y0: &[f64], ff: &[f64], dy: &[f64], res: &mut [f64], neq: usize) {
    let s = (t - t0) / dt;
    let s2 = s * s;
    let s3 = s2 * s;
    let s4 = s3 * s;
    let b3 = 500.0 / 161.0 * s2 - 20000.0 / 4347.0 * s3 + 2750.0 / 1449.0 * s4;
    let b4 = 125.0 / 132.0 * s2 - 625.0 / 594.0 * s3 + 125.0 / 396.0 * s4;
    let b5 = 15.0 / 28.0 * s2 - 15.0 / 14.0 * s3 + 15.0 / 28.0 * s4;
    let b6 = -6144.0 / 1771.0 * s2 + 2048.0 / 253.0 * s3 - 7680.0 / 1771.0 * s4;
    let b7 = 3.0 / 2.0 * s2 - 4.0 * s3 + 5.0 / 2.0 * s4;
    let b1 = s - b3 - b4 - b5 - b6 - b7;
    for i in 0..neq {
        res[i] = y0[i]
            + b1 * dt * ff[i]
            + b3 * dt * ff[i + 2 * neq]
            + b4 * dt * ff[i + 3 * neq]
            + b5 * dt * ff[i + 4 * neq]
            + b6 * dt * ff[i + 5 * neq]
            + b7 * dt * dy[i];
    }
}

pub fn neville(xx: &[f64], y: &[f64], tnew: f64, ynew: &mut [f64], n: usize, ksig: usize) {
    let tscal = xx[n - 1] - xx[0];
    let t = tnew / tscal;
    let mut x = vec![0.0; n];
    let mut yy = vec![0.0; n * ksig];
    for i in 0..n {
        x[i] = xx[i] / tscal;
    }
    yy.clone_from_slice(y);
    for k in 0..ksig {
        for j in 1..n {
            for i in (j..n).rev() {
                yy[i + k * n] = ((t - x[i - j]) * yy[i + k * n] - (t - x[i]) * yy[i - 1 + k * n])
                    / (x[i] - x[i - j]);
            }
        }
        ynew[k] = yy[n - 1 + k * n];
    }
}

pub fn shift_buffer(x: &mut [f64], n: usize, k: usize) {
    for i in 0..(n - 1) {
        for j in 0..k {
            x[i + j * n] = x[i + 1 + j * n];
        }
    }
}

pub fn set_istate_values(
    istate: &mut [i32; 22],
    it_tot: i32,
    stage: i32,
    fsal: i32,
    qerr: i32,
    nrej: i32,
) {
    istate[11] = it_tot;
    istate[12] = it_tot * (stage - fsal) + 1;
    if fsal != 0 {
        istate[12] += nrej + 1;
    }
    istate[13] = nrej;
    istate[14] = qerr;
}
