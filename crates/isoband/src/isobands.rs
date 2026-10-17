//! Isolines and isobands on a rectangular grid: port of `isobander` and `isoliner` in
//! isoband 0.3.0 `src/isoband.cpp`. The case tables live in `band_cases.rs` and `line_cases.rs`.

use crate::grid::{GridPoint, Lines, PointConnect, PointType, NONE};
use crate::ordered_map::OrderedMap;

pub(crate) struct Marcher {
    x: Vec<f64>,
    y: Vec<f64>,
    z: Vec<f64>,
    nrow: usize,
    ncol: usize,
    pub(crate) vlo: f64,
    pub(crate) vhi: f64,
    map: OrderedMap,
    /// Current elementary polygon or line segment; never more than 8 points.
    tmp_poly: [GridPoint; 8],
    tmp_len: usize,
    error: Option<String>,
}

fn interpolate(x0: f64, x1: f64, z0: f64, z1: f64, value: f64) -> f64 {
    let d = (value - z0) / (z1 - z0);
    x0 + d * (x1 - x0)
}

impl Marcher {
    pub(crate) fn new(
        x: &[f64],
        y: &[f64],
        z: &[f64],
        nrow: usize,
        ncol: usize,
        vlo: f64,
        vhi: f64,
    ) -> Result<Self, String> {
        if x.len() != ncol {
            return Err("Number of x coordinates must match number of columns in density matrix.".into());
        }
        if y.len() != nrow {
            return Err("Number of y coordinates must match number of rows in density matrix.".into());
        }
        Ok(Self {
            x: x.to_vec(),
            y: y.to_vec(),
            z: z.to_vec(),
            nrow,
            ncol,
            vlo,
            vhi,
            map: OrderedMap::new(),
            tmp_poly: [NONE; 8],
            tmp_len: 0,
            error: None,
        })
    }

    fn fail(&mut self, msg: &str) {
        if self.error.is_none() {
            self.error = Some(msg.to_string());
        }
    }

    fn check(&self) -> Result<(), String> {
        match &self.error {
            Some(e) => Err(e.clone()),
            None => Ok(()),
        }
    }

    fn reset_grid(&mut self) {
        self.map.clear();
    }

    pub(crate) fn poly_start(&mut self, r: i32, c: i32, ty: PointType) {
        self.tmp_poly[0] = GridPoint { r, c, ty };
        self.tmp_len = 1;
    }

    pub(crate) fn poly_add(&mut self, r: i32, c: i32, ty: PointType) {
        self.tmp_poly[self.tmp_len] = GridPoint { r, c, ty };
        self.tmp_len += 1;
    }

    pub(crate) fn line_start(&mut self, r: i32, c: i32, ty: PointType) {
        self.poly_start(r, c, ty);
    }

    pub(crate) fn line_add(&mut self, r: i32, c: i32, ty: PointType) {
        self.poly_add(r, c, ty);
    }

    pub(crate) fn central_value(&self, r: i32, c: i32) -> f64 {
        let (r, c, n) = (r as usize, c as usize, self.nrow);
        (self.z[r + c * n] + self.z[r + (c + 1) * n] + self.z[r + 1 + c * n] + self.z[r + 1 + (c + 1) * n]) / 4.0
    }

    /// `calc_point_coords`.
    fn coords(&self, p: GridPoint) -> (f64, f64) {
        if p.r < 0 || p.c < 0 {
            return (0.0, 0.0);
        }
        let (r, c, n) = (p.r as usize, p.c as usize, self.nrow);
        let z = &self.z;
        match p.ty {
            PointType::Grid => (self.x[c], self.y[r]),
            PointType::HLo => (
                interpolate(self.x[c], self.x[c + 1], z[r + c * n], z[r + (c + 1) * n], self.vlo),
                self.y[r],
            ),
            PointType::HHi => (
                interpolate(self.x[c], self.x[c + 1], z[r + c * n], z[r + (c + 1) * n], self.vhi),
                self.y[r],
            ),
            PointType::VLo => (
                self.x[c],
                interpolate(self.y[r], self.y[r + 1], z[r + c * n], z[r + 1 + c * n], self.vlo),
            ),
            PointType::VHi => (
                self.x[c],
                interpolate(self.y[r], self.y[r + 1], z[r + c * n], z[r + 1 + c * n], self.vhi),
            ),
        }
    }

    /// `poly_merge`: merge the current elementary polygon into the polygon grid.
    pub(crate) fn poly_merge(&mut self) {
        let poly = self.tmp_poly;
        let n = self.tmp_len;
        let mut to_delete = [false; 8];
        let mut conn = [PointConnect::default(); 8];

        for i in 0..n {
            conn[i].altpoint = false;
            conn[i].next = poly[if i + 1 < n { i + 1 } else { 0 }];
            conn[i].prev = poly[if i >= 1 { i - 1 } else { n - 1 }];

            let p = poly[i];
            if self.map.contains(p) {
                let ex = self.map.get(p);
                if !ex.altpoint {
                    let score = 2 * ((conn[i].next == ex.prev) as i32) + ((conn[i].prev == ex.next) as i32);
                    match score {
                        3 => to_delete[i] = true,
                        2 => conn[i].next = ex.next,
                        1 => conn[i].prev = ex.prev,
                        _ => {
                            conn[i].prev2 = ex.prev;
                            conn[i].next2 = ex.next;
                            conn[i].altpoint = true;
                        }
                    }
                } else {
                    let score = 8 * ((conn[i].next == ex.prev2) as i32)
                        + 4 * ((conn[i].prev == ex.next2) as i32)
                        + 2 * ((conn[i].next == ex.prev) as i32)
                        + ((conn[i].prev == ex.next) as i32);
                    match score {
                        9 => {
                            conn[i].next = ex.next2;
                            conn[i].prev = ex.prev;
                        }
                        6 => {
                            conn[i].next = ex.next;
                            conn[i].prev = ex.prev2;
                        }
                        8 => {
                            conn[i].next2 = ex.next2;
                            conn[i].prev2 = conn[i].prev;
                            conn[i].prev = ex.prev;
                            conn[i].next = ex.next;
                            conn[i].altpoint = true;
                        }
                        4 => {
                            conn[i].prev2 = ex.prev2;
                            conn[i].next2 = conn[i].next;
                            conn[i].prev = ex.prev;
                            conn[i].next = ex.next;
                            conn[i].altpoint = true;
                        }
                        2 => {
                            conn[i].next = ex.next;
                            conn[i].prev2 = ex.prev2;
                            conn[i].next2 = ex.next2;
                            conn[i].altpoint = true;
                        }
                        1 => {
                            conn[i].prev = ex.prev;
                            conn[i].prev2 = ex.prev2;
                            conn[i].next2 = ex.next2;
                            conn[i].altpoint = true;
                        }
                        _ => {
                            self.fail("undefined merging configuration");
                            return;
                        }
                    }
                }
            }
        }

        for i in 0..n {
            if to_delete[i] {
                self.map.erase(poly[i]);
            } else {
                self.map.set(poly[i], conn[i]);
            }
        }
    }

    /// `line_merge`: merge the current line segment into the line graph.
    pub(crate) fn line_merge(&mut self) {
        let p0 = self.tmp_poly[0];
        let p1 = self.tmp_poly[1];
        let score = 2 * (self.map.contains(p1) as i32) + (self.map.contains(p0) as i32);

        match score {
            0 => {
                self.map.at(p0).next = p1;
                self.map.at(p1).prev = p0;
            }
            1 => {
                if self.map.at(p0).next == NONE {
                    self.map.at(p0).next = p1;
                    self.map.at(p1).prev = p0;
                } else if self.map.at(p0).prev == NONE {
                    self.map.at(p0).prev = p1;
                    self.map.at(p1).next = p0;
                } else {
                    self.fail("cannot merge line segment at interior of existing line segment");
                }
            }
            2 => {
                if self.map.at(p1).next == NONE {
                    self.map.at(p1).next = p0;
                    self.map.at(p0).prev = p1;
                } else if self.map.at(p1).prev == NONE {
                    self.map.at(p1).prev = p0;
                    self.map.at(p0).next = p1;
                } else {
                    self.fail("cannot merge line segment at interior of existing line segment");
                }
            }
            3 => {
                let score2 = 8 * ((self.map.at(p0).next == NONE) as i32)
                    + 4 * ((self.map.at(p0).prev == NONE) as i32)
                    + 2 * ((self.map.at(p1).next == NONE) as i32)
                    + ((self.map.at(p1).prev == NONE) as i32);
                match score2 {
                    9 => {
                        self.map.at(p0).next = p1;
                        self.map.at(p1).prev = p0;
                    }
                    6 => {
                        self.map.at(p0).prev = p1;
                        self.map.at(p1).next = p0;
                    }
                    10 => {
                        self.map.at(p0).next = p1;
                        self.map.at(p1).next = p0;
                        // reverse the connections of the segment that starts at p1
                        let mut cur = p1;
                        loop {
                            let e = self.map.at(cur);
                            let tmp = e.prev;
                            e.prev = e.next;
                            e.next = tmp;
                            cur = tmp;
                            if cur == NONE {
                                break;
                            }
                        }
                    }
                    5 => {
                        self.map.at(p0).prev = p1;
                        self.map.at(p1).prev = p0;
                        // reverse the connections of the segment that starts at p0
                        let mut cur = p0;
                        loop {
                            let e = self.map.at(cur);
                            let tmp = e.next;
                            e.next = e.prev;
                            e.prev = tmp;
                            cur = tmp;
                            if cur == NONE {
                                break;
                            }
                        }
                    }
                    _ => self.fail("cannot merge line segment at interior of existing line segment"),
                }
            }
            _ => self.fail("unknown merge state"),
        }
    }

    /// `isobander::calculate_contour`.
    pub(crate) fn calculate_bands(&mut self) -> Result<(), String> {
        self.reset_grid();
        let (nrow, ncol) = (self.nrow, self.ncol);
        let (vlo, vhi) = (self.vlo, self.vhi);
        let ternarized: Vec<i32> = self
            .z
            .iter()
            .map(|&v| ((v >= vlo && v < vhi) as i32) + 2 * ((v >= vhi) as i32))
            .collect();

        let cells_rows = nrow.saturating_sub(1);
        let cells_cols = ncol.saturating_sub(1);
        let mut cells = vec![0i32; cells_rows * cells_cols];
        for r in 0..cells_rows {
            for c in 0..cells_cols {
                let z = &self.z;
                let finite = z[r + c * nrow].is_finite()
                    && z[r + (c + 1) * nrow].is_finite()
                    && z[r + 1 + c * nrow].is_finite()
                    && z[r + 1 + (c + 1) * nrow].is_finite();
                let index = if !finite {
                    0
                } else {
                    27 * ternarized[r + c * nrow]
                        + 9 * ternarized[r + (c + 1) * nrow]
                        + 3 * ternarized[r + 1 + (c + 1) * nrow]
                        + ternarized[r + 1 + c * nrow]
                };
                cells[r + c * cells_rows] = index;
            }
        }

        for r in 0..cells_rows {
            for c in 0..cells_cols {
                let cell = cells[r + c * cells_rows];
                self.band_cell(cell, r as i32, c as i32);
            }
        }
        self.check()
    }

    /// `isoliner::calculate_contour`.
    pub(crate) fn calculate_lines(&mut self) -> Result<(), String> {
        self.reset_grid();
        let (nrow, ncol) = (self.nrow, self.ncol);
        let vlo = self.vlo;
        let binarized: Vec<i32> = self.z.iter().map(|&v| (v >= vlo) as i32).collect();

        let cells_rows = nrow.saturating_sub(1);
        let cells_cols = ncol.saturating_sub(1);
        let mut cells = vec![0i32; cells_rows * cells_cols];
        for r in 0..cells_rows {
            for c in 0..cells_cols {
                let z = &self.z;
                let finite = z[r + c * nrow].is_finite()
                    && z[r + (c + 1) * nrow].is_finite()
                    && z[r + 1 + c * nrow].is_finite()
                    && z[r + 1 + (c + 1) * nrow].is_finite();
                let mut index = if !finite {
                    0
                } else {
                    8 * binarized[r + c * nrow]
                        + 4 * binarized[r + (c + 1) * nrow]
                        + 2 * binarized[r + 1 + (c + 1) * nrow]
                        + binarized[r + 1 + c * nrow]
                };
                // two-segment saddles
                if index == 5 && self.central_value(r as i32, c as i32) < vlo {
                    index = 10;
                } else if index == 10 && self.central_value(r as i32, c as i32) < vlo {
                    index = 5;
                }
                cells[r + c * cells_rows] = index;
            }
        }

        for r in 0..cells_rows {
            for c in 0..cells_cols {
                let cell = cells[r + c * cells_rows];
                self.line_cell(cell, r as i32, c as i32);
            }
        }
        self.check()
    }

    /// `isobander::collect`: polygon rings in map iteration order.
    pub(crate) fn collect_bands(&mut self) -> Result<Lines, String> {
        self.check()?;
        let mut out = Lines::default();
        let order = self.map.order();
        let mut cur_id: i32 = 0;
        let limit = 64 * (order.len() + 16);
        for idx in order {
            let v = self.map.val(idx);
            if (v.collected && !v.altpoint) || (v.collected && v.collected2 && v.altpoint) {
                continue;
            }
            cur_id += 1;

            let start = self.map.key(idx);
            let mut cur = start;
            let mut prev = v.prev;
            if v.altpoint && !v.collected2 {
                prev = v.prev2;
            }
            let mut steps = 0usize;
            loop {
                let (px, py) = self.coords(cur);
                out.x.push(px);
                out.y.push(py);
                out.id.push(cur_id);

                let pc = self.map.at(cur);
                if pc.altpoint && pc.prev2 == prev {
                    pc.collected2 = true;
                    let newcur = pc.next2;
                    prev = cur;
                    cur = newcur;
                } else {
                    pc.collected = true;
                    let newcur = pc.next;
                    prev = cur;
                    cur = newcur;
                }
                steps += 1;
                if cur == start {
                    break;
                }
                if steps > limit {
                    return Err("isobands: polygon walk did not close".into());
                }
            }
        }
        Ok(out)
    }

    /// `isoliner::collect`: line segments in map iteration order.
    pub(crate) fn collect_lines(&mut self) -> Result<Lines, String> {
        self.check()?;
        let mut out = Lines::default();
        let order = self.map.order();
        let mut cur_id: i32 = 0;
        let limit = 64 * (order.len() + 16);
        for idx in order {
            let v = self.map.val(idx);
            if v.collected {
                continue;
            }
            cur_id += 1;

            let start0 = self.map.key(idx);
            let mut cur = start0;
            let mut steps = 0usize;
            // back-track until we find the beginning of the line or circle around once
            if self.map.at(cur).prev != NONE {
                loop {
                    cur = self.map.at(cur).prev;
                    steps += 1;
                    if cur == start0 || self.map.at(cur).prev == NONE {
                        break;
                    }
                    if steps > limit {
                        return Err("isolines: back-track did not terminate".into());
                    }
                }
            }

            let start = cur;
            steps = 0;
            loop {
                let (px, py) = self.coords(cur);
                out.x.push(px);
                out.y.push(py);
                out.id.push(cur_id);

                let pc = self.map.at(cur);
                pc.collected = true;
                cur = pc.next;
                steps += 1;
                if cur == start || cur == NONE {
                    break;
                }
                if steps > limit {
                    return Err("isolines: line walk did not terminate".into());
                }
            }
            // if we're back to start, the start point is output one more time
            if cur == start {
                let (px, py) = self.coords(cur);
                out.x.push(px);
                out.y.push(py);
                out.id.push(cur_id);
            }
        }
        Ok(out)
    }
}

/// `isolines_impl`. `z` is the column-major nrow x ncol matrix, as in R.
pub fn isolines(
    x: &[f64],
    y: &[f64],
    z: &[f64],
    nrow: usize,
    ncol: usize,
    levels: &[f64],
) -> Result<Vec<Lines>, String> {
    let mut il = Marcher::new(x, y, z, nrow, ncol, 0.0, 0.0)?;
    let mut out = Vec::with_capacity(levels.len());
    for &v in levels {
        il.vlo = v;
        il.calculate_lines()?;
        out.push(il.collect_lines()?);
    }
    Ok(out)
}

/// `isobands_impl`. Bands are [low, high), as in R. `z` is column-major nrow x ncol.
pub fn isobands(
    x: &[f64],
    y: &[f64],
    z: &[f64],
    nrow: usize,
    ncol: usize,
    low: &[f64],
    high: &[f64],
) -> Result<Vec<Lines>, String> {
    let mut ib = Marcher::new(x, y, z, nrow, ncol, 0.0, 0.0)?;
    // the C++ kernel runs one contour pass with the default (0, 0) before the loop;
    // that pass sets the hash-table size, which changes the output order
    ib.calculate_bands()?;
    if low.len() != high.len() {
        return Err("Vectors of low and high values must have the same number of elements.".into());
    }
    let mut out = Vec::with_capacity(low.len());
    for i in 0..low.len() {
        ib.vlo = low[i];
        ib.vhi = high[i];
        ib.calculate_bands()?;
        out.push(ib.collect_bands()?);
    }
    Ok(out)
}
