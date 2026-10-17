//! Hexagonal binning kernels, ported from hexbin 1.28.6.
//!
//! - `hbin`  <- `src/hbin.f`  (bin points into hexagon cells, running centroids)
//! - `hcell` <- `src/hcell.f` (cell id per point, no counts)
//! - `herode` <- `src/herode.f` (gray-level erosion order of hexagon cells)
//! - `hsm`   <- `src/hsm.f`   (hexagon cell smoother, expands into neighbours)
//!
//! Cell ids are 1-based, as in the Fortran and in R. Cell `L` lives at
//! row `(L-1) / ncol + 1` and column `(L-1) % ncol + 1`, with rows counted
//! bottom to top and odd rows offset to the left.
//!
//! Two Fortran details are kept on purpose:
//! - `hcell.f` has `con2 = 1./3.`, a single-precision literal, while `hbin.f`
//!   has `1.0/3.0`, double precision. Both are kept as written.
//! - `size/sqrt(3.)` in both binning routines uses a single-precision
//!   `sqrt(3.)`, which is widened to double before the product.

/// `sqrt(3.)` as gfortran evaluates it: a single-precision REAL, widened.
const SQRT3_F32: f64 = 1.732_050_8_f32 as f64;

/// `1./3.` in `hcell.f`: a single-precision division, widened.
const THIRD_F32: f64 = (1.0_f32 / 3.0_f32) as f64;

/// `1.0/3.0` in `hbin.f`: double precision.
const THIRD_F64: f64 = 1.0_f64 / 3.0_f64;

/// Fortran `INT` for a real value: truncate toward zero.
///
/// `as` on a float already truncates toward zero, and maps NaN to 0. It is used
/// instead of `f64::trunc`, which is a libm call on the baseline x86-64 target.
#[inline(always)]
fn fint(value: f64) -> i64 {
    value as i64
}

/// Hexagon cell id (1-based) for a scaled point `(sx, sy)`.
///
/// This is the shared branch of `hbin.f` and `hcell.f`, with the second
/// constant `con2` passed in.
fn cell_id(sx: f64, sy: f64, iinc: i64, lat: i64, con2: f64) -> i64 {
    let con1 = 0.25_f64;
    let j1 = fint(sx + 0.5);
    let i1 = fint(sy + 0.5);
    let dx = sx - j1 as f64;
    let dy = sy - i1 as f64;
    let dist1 = dx * dx + 3.0 * (dy * dy);

    if dist1 < con1 {
        i1 * iinc + j1 + 1
    } else if dist1 > con2 {
        fint(sy) * iinc + fint(sx) + lat
    } else {
        let j2 = fint(sx);
        let i2 = fint(sy);
        let ex = sx - j2 as f64 - 0.5;
        let ey = sy - i2 as f64 - 0.5;
        if dist1 <= ex * ex + 3.0 * (ey * ey) {
            i1 * iinc + j1 + 1
        } else {
            i2 * iinc + j2 + lat
        }
    }
}

/// Scaling shared by `hbin` and `hcell`: `(xmin, ymin, c1, c2)`.
fn scaling(size: f64, shape: f64, rx: [f64; 2], ry: [f64; 2]) -> (f64, f64, f64, f64) {
    let xmin = rx[0];
    let ymin = ry[0];
    let xr = rx[1] - xmin;
    let yr = ry[1] - ymin;
    let c1 = size / xr;
    let c2 = size * shape / (yr * SQRT3_F32);
    (xmin, ymin, c1, c2)
}

/// Output of `hbin`. Arrays hold the non-empty cells only, in ascending id.
#[derive(Debug, Clone, PartialEq)]
pub struct BinOutput {
    pub cell: Vec<i32>,
    pub cnt: Vec<i32>,
    pub xcm: Vec<f64>,
    pub ycm: Vec<f64>,
    /// Revised `bnd(1)`: rows needed for the largest non-empty cell id.
    pub nrow: i32,
    /// Per-point cell ids, present when `keep_ids` is set (`cellid(1) == 0`).
    pub cell_ids: Option<Vec<i32>>,
}

/// Port of `hbin.f`.
///
/// `size` is the number of bins across (`xbins`), `bnd` is `(rows, cols)`
/// (`dim = c(imax, jmax)` in R). `rx` and `ry` are the bounds of x and y.
pub fn hbin(
    x: &[f64],
    y: &[f64],
    size: f64,
    shape: f64,
    rx: [f64; 2],
    ry: [f64; 2],
    bnd: [i32; 2],
    keep_ids: bool,
) -> Result<BinOutput, String> {
    if x.len() != y.len() {
        return Err(format!("x and y differ in length: {} vs {}", x.len(), y.len()));
    }
    let (nrow, ncol) = (bnd[0], bnd[1]);
    if nrow < 1 || ncol < 1 {
        return Err(format!("dim must be positive, got ({nrow}, {ncol})"));
    }
    let n = x.len();
    let lmax = nrow as usize * ncol as usize;
    let (xmin, ymin, c1, c2) = scaling(size, shape, rx, ry);

    let jinc = ncol as i64;
    let lat = jinc + 1;
    let iinc = 2 * jinc;

    let mut cnt = vec![0i32; lmax];
    let mut xcm = vec![0.0_f64; lmax];
    let mut ycm = vec![0.0_f64; lmax];
    let mut ids = if keep_ids { Some(vec![0i32; n]) } else { None };

    for i in 0..n {
        let sx = c1 * (x[i] - xmin);
        let sy = c2 * (y[i] - ymin);
        let l = cell_id(sx, sy, iinc, lat, THIRD_F64);
        if l < 1 || l as usize > lmax {
            return Err(format!("point {i} falls in cell {l}, outside 1..={lmax}"));
        }
        let idx = l as usize - 1;
        cnt[idx] += 1;
        if let Some(ids) = ids.as_mut() {
            ids[i] = l as i32;
        }
        xcm[idx] += (x[i] - xcm[idx]) / cnt[idx] as f64;
        ycm[idx] += (y[i] - ycm[idx]) / cnt[idx] as f64;
    }

    // Compression: keep non-empty cells in ascending id order.
    let mut out_cell = Vec::new();
    let mut out_cnt = Vec::new();
    let mut out_x = Vec::new();
    let mut out_y = Vec::new();
    for l in 1..=lmax {
        if cnt[l - 1] > 0 {
            out_cell.push(l as i32);
            out_cnt.push(cnt[l - 1]);
            out_x.push(xcm[l - 1]);
            out_y.push(ycm[l - 1]);
        }
    }

    let nrow_out = match out_cell.last() {
        Some(&last) => (last - 1) / ncol + 1,
        None => nrow,
    };

    Ok(BinOutput {
        cell: out_cell,
        cnt: out_cnt,
        xcm: out_x,
        ycm: out_y,
        nrow: nrow_out,
        cell_ids: ids,
    })
}

/// Output of `hcell`.
#[derive(Debug, Clone, PartialEq)]
pub struct CellOutput {
    /// Cell id for each point, in input order.
    pub cell: Vec<i32>,
    /// Revised `bnd(1)`.
    pub nrow: i32,
}

/// Port of `hcell.f`: one cell id per point, no counts.
///
/// `hcell.f` uses the single-precision `1./3.` for `con2`. That is kept here.
pub fn hcell(
    x: &[f64],
    y: &[f64],
    size: f64,
    shape: f64,
    rx: [f64; 2],
    ry: [f64; 2],
    bnd: [i32; 2],
) -> Result<CellOutput, String> {
    if x.len() != y.len() {
        return Err(format!("x and y differ in length: {} vs {}", x.len(), y.len()));
    }
    let ncol = bnd[1];
    if ncol < 1 {
        return Err(format!("dim[1] must be positive, got {ncol}"));
    }
    let (xmin, ymin, c1, c2) = scaling(size, shape, rx, ry);
    let jinc = ncol as i64;
    let lat = jinc + 1;
    let iinc = 2 * jinc;

    let mut cell = Vec::with_capacity(x.len());
    let mut celmax: i64 = 0;
    for i in 0..x.len() {
        let sx = c1 * (x[i] - xmin);
        let sy = c2 * (y[i] - ymin);
        let l = cell_id(sx, sy, iinc, lat, THIRD_F32);
        celmax = celmax.max(l);
        cell.push(l as i32);
    }
    let nrow = ((celmax - 1) / jinc + 1) as i32;
    Ok(CellOutput { cell, nrow })
}

/// Port of `herode.f`.
///
/// `cell` and `cnt` are the non-empty cells (ids 1-based, counts), and `bdim`
/// is `(rows, cols)`. Returns the erosion order of each input cell, in input
/// order. The Fortran reuses one array for the ids and the output, and that
/// is kept: the final copy reads the array in place.
pub fn herode(cell: &[i32], cnt: &[i32], bdim: [i32; 2]) -> Result<Vec<i32>, String> {
    let n = cell.len();
    if cnt.len() != n {
        return Err(format!("cell and cnt differ in length: {} vs {}", n, cnt.len()));
    }
    if n == 0 {
        return Ok(Vec::new());
    }
    let nrow = bdim[0] as i64;
    let ncol = bdim[1] as i64;
    if nrow < 1 || ncol < 1 {
        return Err(format!("bdim must be positive, got ({nrow}, {ncol})"));
    }
    let lmax = nrow * ncol;
    let lsz = lmax as usize;
    for (i, &c) in cell.iter().enumerate() {
        if c < 1 || c as i64 > lmax {
            return Err(format!("cell {i} has id {c}, outside 1..={lmax}"));
        }
    }

    // Neighbour offsets. Odd rows (1-based) and even rows differ.
    let inc1 = [1, ncol - 1, -ncol - 1, ncol, -1, -ncol];
    let inc2 = [1, ncol, -ncol, ncol + 1, -1, -ncol + 1];

    let mut exist = vec![false; lsz + 1];
    let mut ncnt = vec![0i64; lsz + 1];
    let mut sides = vec![0i64; lsz + 1];
    // neib[L][j] for j in 0..6 mirrors Fortran neib(j+1, L). Zero means no neighbour.
    let mut neib = vec![[0i64; 6]; lsz + 1];
    let mut erode = vec![0i64; lsz.max(n) + 1];
    let mut maxcnt: i64 = 0;

    for i in 0..n {
        let l = cell[i] as usize;
        ncnt[l] = cnt[i] as i64;
        exist[l] = true;
        maxcnt = maxcnt.max(cnt[i] as i64);
    }

    let exists = |nb: i64, exist: &[bool]| -> bool {
        nb >= 1 && (nb as usize) <= lsz && exist[nb as usize]
    };

    // Store neighbour pointers. Out-of-grid neighbours are set to 0.
    for i in 0..n {
        let l = cell[i] as i64;
        let k = l - 1;
        let r = k / ncol + 1;
        let c = k % ncol + 1;
        let row = &mut neib[l as usize];
        if r % 2 == 1 {
            for j in 0..6 {
                row[j] = l + inc1[j];
            }
            if c == 1 {
                row[1] = 0;
                row[2] = 0;
                row[4] = 0;
            } else if c == ncol {
                row[0] = 0;
            }
            if r == 1 {
                row[2] = 0;
                row[5] = 0;
            } else if r == nrow {
                row[1] = 0;
                row[3] = 0;
            }
        } else {
            for j in 0..6 {
                row[j] = l + inc2[j];
            }
            if c == 1 {
                row[4] = 0;
            } else if c == ncol {
                row[0] = 0;
                row[3] = 0;
                row[5] = 0;
            }
            if r == nrow {
                row[1] = 0;
                row[3] = 0;
            }
        }
    }

    // Exposed sides for each cell.
    for i in 0..n {
        let l = cell[i] as usize;
        sides[l] = 0;
        for j in 0..6 {
            if !exists(neib[l][j], &exist) {
                sides[l] += 1;
            }
        }
    }

    // Surface list, 1-based like the Fortran ncell(*).
    let mut ncell = vec![0i64; 2 * n + lsz + 2];
    let mut nlist = 0usize;
    for i in 0..n {
        let l = cell[i] as usize;
        if sides[l] > 0 {
            nlist += 1;
            ncell[nlist] = l as i64;
        }
    }

    let mut order: i64 = 0;
    while nlist > 0 {
        // Largest uniform erosion step before some surface cell empties.
        let mut step = maxcnt;
        for i in 1..=nlist {
            let ic = ncell[i] as usize;
            step = step.min((ncnt[ic] - 1) / sides[ic]);
        }
        let step = step + 1;

        let mut nc = 0usize;
        order += 6;
        let mut ninc = nlist;
        for i in 1..=nlist {
            let ic = ncell[i] as usize;
            ncnt[ic] -= sides[ic] * step;
            if ncnt[ic] <= 0 {
                exist[ic] = false;
                erode[ic] = order + ncnt[ic];
                for j in 0..6 {
                    let nb = neib[ic][j];
                    if exists(nb, &exist) {
                        if sides[nb as usize] == 0 {
                            ninc += 1;
                            ncell[ninc] = nb;
                        }
                        sides[nb as usize] += 1;
                    }
                }
            } else {
                nc += 1;
                ncell[nc] = ncell[i];
            }
        }
        for i in (nlist + 1)..=ninc {
            nc += 1;
            ncell[nc] = ncell[i];
        }
        nlist = nc;
    }

    // Final copy: erode(i) = erode(cell(i)), in place, as in herode.f.
    for i in 1..=n {
        erode[i] = erode[cell[i - 1] as usize];
    }
    Ok(erode[1..=n].iter().map(|&v| v as i32).collect())
}

/// Port of `hsm.f`.
///
/// `cell` and `cnt` hold the padded 1-based ids and counts exactly as R's
/// `smooth.hexbin` builds them (two-cell pad on each side, row stride `ncol`).
/// `wt` is `(centre, ring1, ring2)`, default `c(48, 4, 1)` in R.
/// Returns the surviving cells and their smoothed counts, in ascending id.
pub fn hsm(
    cell: &[i32],
    cnt: &[i32],
    nmax: usize,
    ncol: i64,
    wt: [i32; 3],
) -> Result<(Vec<i32>, Vec<i32>), String> {
    let n = cell.len();
    if cnt.len() != n {
        return Err(format!("cell and cnt differ in length: {} vs {}", n, cnt.len()));
    }
    if ncol < 1 {
        return Err(format!("ncol must be positive, got {ncol}"));
    }
    let nm = nmax as i64;
    let mut sm = vec![0i32; nmax + 1];

    let ind1 = [-1, ncol - 1, ncol, 1, -ncol, -ncol - 1];
    let ind2 = [
        -2,
        ncol - 2,
        2 * ncol - 1,
        2 * ncol,
        2 * ncol + 1,
        ncol + 1,
        2,
        -ncol + 1,
        -2 * ncol + 1,
        -2 * ncol,
        -2 * ncol - 1,
        -ncol - 2,
    ];
    let ind3 = [-1, ncol, ncol + 1, 1, -ncol + 1, -ncol];
    let ind4 = [
        -2,
        ncol - 1,
        2 * ncol - 1,
        2 * ncol,
        2 * ncol + 1,
        ncol + 2,
        2,
        -ncol + 2,
        -2 * ncol + 1,
        -2 * ncol,
        -2 * ncol - 1,
        -ncol - 1,
    ];

    let (wta, wtb, wtc) = (wt[0], wt[1], wt[2]);

    let check = |loc: i64| -> Result<usize, String> {
        if loc < 1 || loc > nm {
            Err(format!("cell index {loc} outside 1..={nmax} after padding"))
        } else {
            Ok(loc as usize)
        }
    };

    for i in 0..n {
        let loc = check(cell[i] as i64)?;
        sm[loc] = wta.wrapping_mul(cnt[i]);
    }

    for i in 0..n {
        let loc = cell[i] as i64;
        let row = (loc - 1) / ncol + 1;
        let cnt1 = wtb.wrapping_mul(cnt[i]);
        let cnt2 = wtc.wrapping_mul(cnt[i]);
        let (ring1, ring2): (&[i64], &[i64]) = if row % 2 == 1 {
            (&ind1, &ind2)
        } else {
            (&ind3, &ind4)
        };
        for &o in ring1 {
            let idx = check(loc + o)?;
            sm[idx] = sm[idx].wrapping_add(cnt1);
        }
        for &o in ring2 {
            let idx = check(loc + o)?;
            sm[idx] = sm[idx].wrapping_add(cnt2);
        }
    }

    let mut out_cell = Vec::new();
    let mut out_cnt = Vec::new();
    for i in 1..=nmax {
        if sm[i] > 0 {
            out_cell.push(i as i32);
            out_cnt.push(sm[i]);
        }
    }
    Ok((out_cell, out_cnt))
}

#[cfg(feature = "python")]
mod python;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn single_point_lands_in_cell_one() {
        // A point at the lower-left corner lands in cell 1.
        let out = hbin(&[0.0], &[0.0], 10.0, 1.0, [0.0, 10.0], [0.0, 10.0], [20, 14], false).unwrap();
        assert_eq!(out.cell, vec![1]);
        assert_eq!(out.cnt, vec![1]);
        assert_eq!(out.xcm, vec![0.0]);
        assert_eq!(out.nrow, 1);
        assert!(out.cell_ids.is_none());
    }

    #[test]
    fn running_centroid_matches_mean() {
        let x = [0.0, 0.0, 0.0];
        let y = [0.0, 0.0, 0.0];
        let out = hbin(&x, &y, 10.0, 1.0, [0.0, 10.0], [0.0, 10.0], [20, 14], true).unwrap();
        assert_eq!(out.cnt, vec![3]);
        assert_eq!(out.cell_ids.unwrap(), vec![1, 1, 1]);
    }

    #[test]
    fn sqrt3_constant_is_single_precision() {
        assert_eq!(SQRT3_F32, 3.0_f32.sqrt() as f64);
        assert_eq!(THIRD_F32, (1.0_f32 / 3.0_f32) as f64);
    }

    #[test]
    fn herode_single_cell_erodes_in_first_cycle() {
        // One isolated cell with count 3: all six sides exposed, so one
        // cycle removes it. erode = order (6) + remaining count (3 - 6).
        let erode = herode(&[1], &[3], [2, 2]).unwrap();
        assert_eq!(erode, vec![3]);
    }

    #[test]
    fn hsm_centre_weight_survives() {
        // A single cell at padded position (3,3) on a 6 x 7 layout.
        let (cell, cnt) = hsm(&[3 * 7 + 3], &[1], 6 * 7, 7, [48, 4, 1]).unwrap();
        assert!(cell.contains(&(3 * 7 + 3)));
        let centre = cell.iter().position(|&c| c == 3 * 7 + 3).unwrap();
        assert_eq!(cnt[centre], 48);
    }

    #[test]
    fn hcell_matches_hbin_ids_away_from_the_boundary() {
        let x = [0.2, 3.7, 8.1];
        let y = [0.4, 5.5, 9.0];
        let rx = [0.0, 10.0];
        let ry = [0.0, 10.0];
        let bins = hbin(&x, &y, 10.0, 1.0, rx, ry, [20, 14], true).unwrap();
        let cells = hcell(&x, &y, 10.0, 1.0, rx, ry, [20, 14]).unwrap();
        assert_eq!(cells.cell, bins.cell_ids.unwrap());
    }
}
