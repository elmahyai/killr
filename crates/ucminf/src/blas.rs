//! Packed BLAS operations in the order of the reference kernels ucminf calls.

pub fn dcopy(n: usize, x: &[f64], y: &mut [f64]) {
    y[..n].copy_from_slice(&x[..n]);
}

pub fn daxpy(n: usize, a: f64, x: &[f64], y: &mut [f64]) {
    for i in 0..n {
        y[i] += a * x[i];
    }
}

pub fn dscal(n: usize, a: f64, x: &mut [f64]) {
    for i in 0..n {
        x[i] *= a;
    }
}

pub fn ddot(n: usize, x: &[f64], y: &[f64]) -> f64 {
    let mut sum = 0.0;
    for i in 0..n {
        sum += x[i] * y[i];
    }
    sum
}

/// Reference DNORM2: scale the sum of squares, then multiply by the scale.
pub fn dnrm2(n: usize, x: &[f64]) -> f64 {
    let mut scale = 0.0;
    let mut sum = 0.0;
    for i in 0..n {
        if x[i] != 0.0 {
            let absxi = x[i].abs();
            if scale < absxi {
                let ratio = scale / absxi;
                sum = 1.0 + sum * (ratio * ratio);
                scale = absxi;
            } else {
                let ratio = absxi / scale;
                sum += ratio * ratio;
            }
        }
    }
    scale * sum.sqrt()
}

/// 1-based index of the first largest absolute entry.
pub fn idamax(n: usize, x: &[f64]) -> usize {
    let mut best = 0;
    let mut max = 0.0;
    for i in 0..n {
        let abs = x[i].abs();
        if abs > max {
            max = abs;
            best = i;
        }
    }
    best + 1
}

/// y := alpha * A * x + beta * y, A symmetric and stored as a lower triangle.
pub fn dspmv(n: usize, alpha: f64, ap: &[f64], x: &[f64], beta: f64, y: &mut [f64]) {
    if beta == 0.0 {
        for value in y.iter_mut().take(n) {
            *value = 0.0;
        }
    } else if beta != 1.0 {
        for value in y.iter_mut().take(n) {
            *value *= beta;
        }
    }
    let mut k = 0;
    for j in 0..n {
        let temp1 = alpha * x[j];
        let mut temp2 = 0.0;
        for i in 0..j {
            y[i] += temp1 * ap[k];
            temp2 += ap[k] * x[i];
            k += 1;
        }
        y[j] += temp1 * ap[k] + alpha * temp2;
        k += 1;
    }
}

/// A := A + alpha * x * x', lower packed triangle.
pub fn dspr(n: usize, alpha: f64, x: &[f64], ap: &mut [f64]) {
    let mut kk = 0;
    for j in 0..n {
        if x[j] != 0.0 {
            let temp = alpha * x[j];
            for i in j..n {
                ap[kk + (i - j)] += x[i] * temp;
            }
        }
        kk += n - j;
    }
}

/// A := A + alpha * x * y' + alpha * y * x', lower packed triangle.
pub fn dspr2(n: usize, alpha: f64, x: &[f64], y: &[f64], ap: &mut [f64]) {
    let mut kk = 0;
    for j in 0..n {
        if x[j] != 0.0 || y[j] != 0.0 {
            let temp1 = alpha * y[j];
            let temp2 = alpha * x[j];
            for i in j..n {
                ap[kk + (i - j)] += x[i] * temp1 + y[i] * temp2;
            }
        }
        kk += n - j;
    }
}
