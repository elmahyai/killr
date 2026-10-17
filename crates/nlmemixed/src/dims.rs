//! Flat `pdims` vector produced by `unlist(MEdims(...))`.

#[derive(Clone, Debug)]
pub struct Dims {
    pub n: i32,
    pub zx_rows: i32,
    pub zx_cols: i32,
    pub q: i32,
    pub s_rows: i32,
    pub qvec: Vec<i32>,
    pub ngrp: Vec<i32>,
    pub dm_off: Vec<i32>,
    pub ncol: Vec<i32>,
    pub nrot: Vec<i32>,
    pub zx_off: Vec<i32>,
    pub zx_len: Vec<i32>,
    pub st_off: Vec<i32>,
    pub dec_off: Vec<i32>,
    pub dec_len: Vec<i32>,
    pub pos: Vec<usize>,
}

impl Dims {
    pub fn parse(p: &[i32]) -> Self {
        let q = p[3];
        let qp2 = q as usize + 2;
        let mut cursor = 5usize;
        let take = |c: &mut usize, src: &[i32]| {
            let v = src[*c..*c + qp2].to_vec();
            *c += qp2;
            v
        };
        let qvec = take(&mut cursor, p);
        let ngrp = take(&mut cursor, p);
        let dm_off = take(&mut cursor, p);
        let ncol = take(&mut cursor, p);
        let nrot = take(&mut cursor, p);
        let mut pos = vec![0usize; qp2 + 1];
        for i in 0..qp2 {
            pos[i + 1] = pos[i] + ngrp[i] as usize;
        }
        let total = pos[qp2];
        let take_flat = |c: &mut usize, src: &[i32]| {
            let v = src[*c..*c + total].to_vec();
            *c += total;
            v
        };
        let zx_off = take_flat(&mut cursor, p);
        let zx_len = take_flat(&mut cursor, p);
        let st_off = take_flat(&mut cursor, p);
        let dec_off = take_flat(&mut cursor, p);
        let dec_len = take_flat(&mut cursor, p);
        Self {
            n: p[0],
            zx_rows: p[1],
            zx_cols: p[2],
            q,
            s_rows: p[4],
            qvec,
            ngrp,
            dm_off,
            ncol,
            nrot,
            zx_off,
            zx_len,
            st_off,
            dec_off,
            dec_len,
            pos,
        }
    }

    pub fn qp2(&self) -> usize {
        self.q as usize + 2
    }

    pub fn grp(&self, flat: &[i32], level: usize, j: usize) -> i32 {
        flat[self.pos[level] + j]
    }

    pub fn set_grp(&mut self, flat: &mut Vec<i32>, level: usize, j: usize, value: i32) {
        flat[self.pos[level] + j] = value;
    }
}
