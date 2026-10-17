//! Scaled eigen pseudo-inverse, ported from locfit `m_eigen.c` (`eig_dec`,
//! `eig_solve`, `eig_qf`, `e_tol`) and `m_jacob.c` (`jacob_dec` with
//! `JAC_EIGD`, `jacob_solve`, `jacob_qf`).
//!
//! Matrices are row-major: element `(r, c)` is `m[r * p + c]`.

const E_MAXIT: usize = 20;
const E_TOL: f64 = 1.0e-8;

fn e_tol(diag_mat: &[f64], p: usize) -> f64 {
    let mut mx = diag_mat[0];
    for i in 1..p {
        if diag_mat[i * (p + 1)] > mx {
            mx = diag_mat[i * (p + 1)];
        }
    }
    E_TOL * mx
}

/// Jacobi eigen-decomposition: on return `x` is (near) diagonal with the
/// eigenvalues, and `pm` holds the eigenvectors as columns.
fn eig_dec(x: &mut [f64], pm: &mut [f64], d: usize) {
    for i in 0..d {
        for j in 0..d {
            pm[i * d + j] = if i == j { 1.0 } else { 0.0 };
        }
    }
    for _ in 0..E_MAXIT {
        let mut rotated = false;
        for i in 0..d {
            for j in (i + 1)..d {
                if x[i * d + j] * x[i * d + j] > 1.0e-15 * (x[i * d + i] * x[j * d + j]).abs() {
                    let mut c = (x[j * d + j] - x[i * d + i]) / 2.0;
                    let mut s = -x[i * d + j];
                    let r = (c * c + s * s).sqrt();
                    c /= r;
                    s = ((1.0 - c) / 2.0).sqrt() * (if s > 0.0 { 1.0 } else { -1.0 });
                    c = ((1.0 + c) / 2.0).sqrt();
                    for k in 0..d {
                        let u = x[i * d + k];
                        let v = x[j * d + k];
                        x[i * d + k] = u * c + v * s;
                        x[j * d + k] = v * c - u * s;
                    }
                    for k in 0..d {
                        let u = x[k * d + i];
                        let v = x[k * d + j];
                        x[k * d + i] = u * c + v * s;
                        x[k * d + j] = v * c - u * s;
                    }
                    x[i * d + j] = 0.0;
                    x[j * d + i] = 0.0;
                    for k in 0..d {
                        let u = pm[k * d + i];
                        let v = pm[k * d + j];
                        pm[k * d + i] = u * c + v * s;
                        pm[k * d + j] = v * c - u * s;
                    }
                    rotated = true;
                }
            }
        }
        if !rotated {
            return;
        }
    }
}

/// Decomposition of a symmetric positive semi-definite `p x p` matrix in the
/// form locfit uses for `(X^T W X)^{-1}`: scale to a correlation-like matrix,
/// eigen-decompose, and apply the pseudo-inverse with a relative tolerance.
#[derive(Clone, Debug)]
pub struct Jac {
    pub p: usize,
    z: Vec<f64>,
    q: Vec<f64>,
    dg: Vec<f64>,
}

impl Jac {
    pub fn new(a: &[f64], p: usize) -> Jac {
        let mut z = a.to_vec();
        let mut dg = vec![0.0; p];
        for i in 0..p {
            let zii = z[i * (p + 1)];
            dg[i] = if zii <= 0.0 { 0.0 } else { 1.0 / zii.sqrt() };
        }
        for i in 0..p {
            for j in 0..p {
                z[i * p + j] *= dg[i] * dg[j];
            }
        }
        let mut q = vec![0.0; p * p];
        eig_dec(&mut z, &mut q, p);
        Jac { p, z, q, dg }
    }

    fn eig_solve(&self, x: &mut [f64]) -> usize {
        let d = self.p;
        let tol = e_tol(&self.z, d);
        let mut w = vec![0.0; d];
        for i in 0..d {
            let mut s = 0.0;
            for j in 0..d {
                s += self.q[j * d + i] * x[j];
            }
            w[i] = s;
        }
        let mut rank = 0;
        for i in 0..d {
            // Components with a tiny eigenvalue are left unscaled, as in locfit.
            if self.z[i * d + i] > tol {
                w[i] /= self.z[i * (d + 1)];
                rank += 1;
            }
        }
        for i in 0..d {
            let mut s = 0.0;
            for j in 0..d {
                s += self.q[i * d + j] * w[j];
            }
            x[i] = s;
        }
        rank
    }

    /// `v <- (X^T W X)^{-1} v` (pseudo-inverse). Returns the rank.
    pub fn solve(&self, v: &mut [f64]) -> usize {
        for i in 0..self.p {
            v[i] *= self.dg[i];
        }
        let rank = self.eig_solve(v);
        for i in 0..self.p {
            v[i] *= self.dg[i];
        }
        rank
    }

    /// `v^T (X^T W X)^{-1} v`.
    pub fn qf(&self, v: &[f64]) -> f64 {
        let p = self.p;
        let mut vv = v.to_vec();
        for i in 0..p {
            vv[i] *= self.dg[i];
        }
        let tol = e_tol(&self.z, p);
        let mut sum = 0.0;
        for i in 0..p {
            if self.z[i * p + i] > tol {
                let mut wi = 0.0;
                for j in 0..p {
                    wi += self.q[j * p + i] * vv[j];
                }
                sum += wi * wi / self.z[i * p + i];
            }
        }
        sum
    }

    /// Full `p x p` pseudo-inverse, row-major.
    pub fn inverse(&self) -> Vec<f64> {
        let p = self.p;
        let mut inv = vec![0.0; p * p];
        for k in 0..p {
            let mut e = vec![0.0; p];
            e[k] = 1.0;
            self.solve(&mut e);
            for r in 0..p {
                inv[r * p + k] = e[r];
            }
        }
        inv
    }
}
