//! `penalty` from quantreg 6.1 `src/penalty.f`: the sparse total-variation
//! penalty matrix of the triogram, which R's `triogram.penalty` calls through
//! `.Fortran("penalty", ...)`.
//!
//! For every Delaunay edge (i, j) that is not a hull edge on both ends, `fadjs`
//! finds the two apexes of the adjacent triangles, `ggap` gives the four
//! gradient coefficients, and `srtpai` puts the four vertex numbers in ascending
//! order with their coefficients. Each edge writes four entries of `rax`/`jax`.
//!
//! The triangulation comes in the triSht2tri lists: `tlist`, `tlptr`, `tlend`.
//! Vertex numbers are 1-based, a negative `tlist` entry marks a hull edge, and
//! each vertex's neighbour list is circular. The values keep the Fortran 1-based
//! numbering and the slices are read at `k - 1`, so the port follows the source
//! line for line.
//!
//! `srtpai` is a Shell sort of four values. The four vertex numbers of one edge
//! are distinct, so the ascending order is unique and the sort is a plain
//! insertion sort here.

#![allow(clippy::too_many_arguments, clippy::needless_range_loop)]

#[cfg(feature = "python")]
mod python;

/// The output of `penalty`: `rax` and `jax` have length `m`, `ned` is the edge count
/// and `ierr` is 1 when `ggap` met a degenerate edge (R stops with a message then).
#[derive(Debug, Clone, PartialEq)]
pub struct Penalty {
    pub rax: Vec<f64>,
    pub jax: Vec<i64>,
    pub ned: usize,
    pub ierr: i32,
}

/// `orient(x, y)`: true when the four points of an edge pair need their two apexes swapped.
fn orient(x: &[f64; 4], y: &[f64; 4]) -> bool {
    (y[1] - y[0]) * (x[2] - x[3]) + (x[0] - x[1]) * (y[2] - y[3]) > 0.0
}

/// `ggap(x, y, g, eps, ierr)`: the four gradient coefficients of the edge, or `None`
/// when a triangle is degenerate (|d1| or |d2| below `eps`).
fn ggap(x: &[f64; 4], y: &[f64; 4], eps: f64) -> Option<[f64; 4]> {
    let d1 = -x[1] * y[0] + x[2] * y[0] + x[0] * y[1] - x[2] * y[1] - x[0] * y[2] + x[1] * y[2];
    let d2 = -x[1] * y[0] + x[3] * y[0] + x[0] * y[1] - x[3] * y[1] - x[0] * y[3] + x[1] * y[3];
    if d1.abs() < eps || d2.abs() < eps {
        return None;
    }
    let h1 = -(y[0] - y[1]);
    let h2 = x[0] - x[1];
    // w(1, i) is the y part and w(2, i) the x part of the Fortran array.
    let w1_1 = (y[1] - y[2]) / d1 - (y[1] - y[3]) / d2;
    let w2_1 = (x[2] - x[1]) / d1 - (x[3] - x[1]) / d2;
    let w1_2 = (y[2] - y[0]) / d1 - (y[3] - y[0]) / d2;
    let w2_2 = (x[0] - x[2]) / d1 - (x[0] - x[3]) / d2;
    let w1_3 = (y[0] - y[1]) / d1;
    let w2_3 = (x[1] - x[0]) / d1;
    let w1_4 = (y[1] - y[0]) / d2;
    let w2_4 = (x[0] - x[1]) / d2;
    Some([
        h1 * w1_1 + h2 * w2_1,
        h1 * w1_2 + h2 * w2_2,
        h1 * w1_3 + h2 * w2_3,
        h1 * w1_4 + h2 * w2_4,
    ])
}

/// `fadjs(n4, n, q, tlist, tlptr, tlend)`: given n4[0] (vertex i) and n4[1] (vertex j),
/// walks the neighbour list of i and fills n4[2] and n4[3], the apexes on either side of j.
fn fadjs(n4: &mut [i64; 4], tlist: &[i64], tlptr: &[i64], tlend: &[i64]) -> Result<(), String> {
    let vpl = tlend[(n4[0] - 1) as usize];
    let mut vp = vpl;
    let mut k: usize = 0;
    let mut matched = false;
    let mut v0: i64 = 0;
    // The list is circular, so a match is found within two laps of the list.
    let limit = 2 * tlist.len() + 4;
    loop {
        k += 1;
        if k > limit {
            return Err("penalty: neighbour list of an edge vertex has no match".to_string());
        }
        vp = tlptr[(vp - 1) as usize];
        let v = tlist[(vp - 1) as usize];
        if k > 1 && v.abs() == n4[1] {
            n4[2] = v0.abs();
            matched = true;
            continue;
        }
        if matched {
            n4[3] = v.abs();
            return Ok(());
        }
        v0 = v;
    }
}

/// `penalty(n, m, q, x, y, bnd, tlist, tlptr, tlend, rax, jax, ned, eps, ierr)`:
/// the penalty entries of the triogram on the n points (x, y).
///
/// `bnd` is 1 for a point on the convex hull and 0 otherwise. `m` is the capacity of
/// `rax` and `jax` (R passes 13 * n). The result is `ierr = 1` with the partial
/// entries when a degenerate edge is found, as the Fortran returns.
pub fn penalty(
    n: usize,
    m: usize,
    x: &[f64],
    y: &[f64],
    bnd: &[i64],
    tlist: &[i64],
    tlptr: &[i64],
    tlend: &[i64],
    eps: f64,
) -> Result<Penalty, String> {
    if x.len() != n || y.len() != n || bnd.len() != n || tlend.len() != n {
        return Err("penalty: x, y, bnd and tlend need n entries".to_string());
    }
    if tlist.len() != tlptr.len() {
        return Err("penalty: tlist and tlptr need the same length".to_string());
    }
    let mut rax = vec![0.0f64; m];
    let mut jax = vec![0i64; m];
    let mut ned: usize = 0;
    for i in 1..=n {
        let lpl = tlend[i - 1];
        let mut lp = lpl;
        loop {
            lp = tlptr[(lp - 1) as usize];
            let j = tlist[(lp - 1) as usize].abs();
            if j > i as i64 {
                let mut n4 = [i as i64, j, 0, 0];
                fadjs(&mut n4, tlist, tlptr, tlend)?;
                let (bi, bj) = (bnd[i - 1], bnd[(j - 1) as usize]);
                if bi * bj == 0 {
                    ned += 1;
                    let mut x4 = [0.0f64; 4];
                    let mut y4 = [0.0f64; 4];
                    for k in 0..4 {
                        x4[k] = x[(n4[k] - 1) as usize];
                        y4[k] = y[(n4[k] - 1) as usize];
                    }
                    if orient(&x4, &y4) {
                        n4.swap(2, 3);
                        x4.swap(2, 3);
                        y4.swap(2, 3);
                    }
                    let g4 = match ggap(&x4, &y4, eps) {
                        Some(g) => g,
                        None => {
                            return Ok(Penalty { rax, jax, ned, ierr: 1 });
                        }
                    };
                    // srtpai(n4, 1, p4, 1, 4): p4 orders the vertex numbers ascending.
                    let mut p4 = [0usize, 1, 2, 3];
                    for a in 1..4 {
                        let mut b = a;
                        while b > 0 && n4[p4[b - 1]] > n4[p4[b]] {
                            p4.swap(b - 1, b);
                            b -= 1;
                        }
                    }
                    for k in 0..4 {
                        let pos = (ned - 1) * 4 + k;
                        if pos < m {
                            rax[pos] = g4[p4[k]];
                            jax[pos] = n4[p4[k]];
                        }
                    }
                    if ned * 4 > m {
                        return Ok(Penalty { rax, jax, ned, ierr: 0 });
                    }
                }
            }
            if lp == lpl {
                break;
            }
        }
    }
    Ok(Penalty { rax, jax, ned, ierr: 0 })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ggap_rejects_degenerate_edge() {
        let x = [0.0, 1.0, 2.0, 3.0];
        let y = [0.0, 0.0, 0.0, 0.0];
        assert!(ggap(&x, &y, f64::EPSILON).is_none());
    }
}
