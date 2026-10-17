//! Grid-space point types from isoband 0.3.0 `src/isoband.cpp` and `src/polygon.h`.

/// A point in grid space: row, column, and which edge or corner it sits on.
/// Discriminants match the C++ `point_type` enum order.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum PointType {
    Grid = 0,
    HLo = 1,
    HHi = 2,
    VLo = 3,
    VHi = 4,
}

/// `grid_point` from the C++ source. The default (-1, -1, grid) means "no point".
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct GridPoint {
    pub r: i32,
    pub c: i32,
    pub ty: PointType,
}

impl GridPoint {
    /// `grid_point_hasher`: (r << 30) ^ (c << 3) ^ type, as one 64-bit key.
    pub fn packed(&self) -> u64 {
        (((self.r as i64) << 30) ^ ((self.c as i64) << 3) ^ (self.ty as i64)) as u64
    }
}

impl std::hash::Hash for GridPoint {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        state.write_u64(self.packed());
    }
}

pub const NONE: GridPoint = GridPoint {
    r: -1,
    c: -1,
    ty: PointType::Grid,
};

/// `point_connect` from the C++ source: links to neighbours in the polygon/line graph.
#[derive(Clone, Copy, Debug)]
pub struct PointConnect {
    pub prev: GridPoint,
    pub next: GridPoint,
    pub prev2: GridPoint,
    pub next2: GridPoint,
    pub altpoint: bool,
    pub collected: bool,
    pub collected2: bool,
}

impl Default for PointConnect {
    fn default() -> Self {
        Self {
            prev: NONE,
            next: NONE,
            prev2: NONE,
            next2: NONE,
            altpoint: false,
            collected: false,
            collected2: false,
        }
    }
}

/// Output of one isoline or isoband: coordinates and ids, as R returns them.
#[derive(Clone, Debug, Default)]
pub struct Lines {
    pub x: Vec<f64>,
    pub y: Vec<f64>,
    pub id: Vec<i32>,
}
