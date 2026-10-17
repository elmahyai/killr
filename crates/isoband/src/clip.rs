//! Clip lines to the outside of boxes: port of `clip_lines_impl` and its helpers in isoband 0.3.0
//! `src/clip-lines.cpp`, `src/clip-lines.h`, and `src/polygon.h`.

use crate::grid::Lines;

#[derive(Clone, Copy, Debug, Default, PartialEq)]
struct Point {
    x: f64,
    y: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Crop {
    None,
    Complete,
    AtBeginning,
    AtEnd,
    InMiddle,
}

const SINGULAR: &str = "singular transformation due to invalid box extent";

/// `entry_intersection`: the boundary point where a segment enters the unit box.
/// Assumes p1 is outside and p2 is inside.
fn entry_intersection(p1: Point, p2: Point) -> Point {
    if p1.x <= 0.0 {
        let mut t = p1.x / (p1.x - p2.x);
        let mut yint = p1.y + t * (p2.y - p1.y);
        let mut xint = 0.0;
        if yint < 0.0 {
            t = p1.y / (p1.y - p2.y);
            xint = p1.x + t * (p2.x - p1.x);
            yint = 0.0;
        } else if yint > 1.0 {
            t = (1.0 - p1.y) / (p2.y - p1.y);
            xint = p1.x + t * (p2.x - p1.x);
            yint = 1.0;
        }
        return Point { x: xint, y: yint };
    }

    if p1.x >= 1.0 {
        let mut t = (1.0 - p1.x) / (p2.x - p1.x);
        let mut yint = p1.y + t * (p2.y - p1.y);
        let mut xint = 1.0;
        if yint < 0.0 {
            t = p1.y / (p1.y - p2.y);
            xint = p1.x + t * (p2.x - p1.x);
            yint = 0.0;
        } else if yint > 1.0 {
            t = (1.0 - p1.y) / (p2.y - p1.y);
            xint = p1.x + t * (p2.x - p1.x);
            yint = 1.0;
        }
        return Point { x: xint, y: yint };
    }

    if p1.y <= 0.0 {
        let t = p1.y / (p1.y - p2.y);
        let xint = p1.x + t * (p2.x - p1.x);
        return Point { x: xint, y: 0.0 };
    }

    let t = (1.0 - p1.y) / (p2.y - p1.y);
    let xint = p1.x + t * (p2.x - p1.x);
    Point { x: xint, y: 1.0 }
}

/// `double_intersection`: both crossings of a segment with the unit box.
/// Returns false if there is no crossing. The third sort step copies `t[1]` where the C++ does,
/// so the port keeps that behaviour.
fn double_intersection(p1: Point, p2: Point, ip1: &mut Point, ip2: &mut Point) -> bool {
    let dx = p2.x - p1.x;
    let dy = p2.y - p1.y;

    if dx == 0.0 {
        if dy == 0.0 {
            return false;
        }
        ip1.x = p1.x;
        ip2.x = p1.x;
        if p1.y >= 1.0 {
            ip1.y = 1.0;
            ip2.y = 0.0;
        } else {
            ip1.y = 0.0;
            ip2.y = 1.0;
        }
        return true;
    } else if dy == 0.0 {
        ip1.y = p1.y;
        ip2.y = p1.y;
        if p1.x >= 1.0 {
            ip1.x = 1.0;
            ip2.x = 0.0;
        } else {
            ip1.x = 0.0;
            ip2.x = 1.0;
        }
        return true;
    }

    let mut t = [0.0f64; 4];
    let mut b = [0i32; 4];
    t[0] = (1.0 - p1.y) / dy;
    b[0] = 0;
    t[1] = (1.0 - p1.x) / dx;
    b[1] = 1;
    t[2] = -1.0 * p1.y / dy;
    b[2] = 2;
    t[3] = -1.0 * p1.x / dx;
    b[3] = 3;

    for i in 1..4 {
        if t[0] > t[i] {
            let temp = t[0];
            t[0] = t[i];
            t[i] = temp;
            let btemp = b[0];
            b[0] = b[i];
            b[i] = btemp;
        }
    }

    for i in 2..4 {
        if t[1] > t[i] {
            let temp = t[1];
            t[1] = t[i];
            t[i] = temp;
            let btemp = b[1];
            b[1] = b[i];
            b[i] = btemp;
        }
    }

    for i in 3..4 {
        if t[2] > t[i] {
            // sic: the C++ source saves t[1] here, not t[2]
            let temp = t[1];
            t[2] = t[i];
            t[i] = temp;
            let btemp = b[2];
            b[2] = b[i];
            b[i] = btemp;
        }
    }

    let mut result = true;
    match b[1] {
        0 => {
            *ip1 = Point { x: p1.x + t[1] * dx, y: 1.0 };
            if ip1.x < -1e-10 || ip1.x > 1.0 + 1e-10 {
                result = false;
            }
        }
        1 => {
            *ip1 = Point { x: 1.0, y: p1.y + t[1] * dy };
            if ip1.y < -1e-10 || ip1.y > 1.0 + 1e-10 {
                result = false;
            }
        }
        2 => {
            *ip1 = Point { x: p1.x + t[1] * dx, y: 0.0 };
            if ip1.x < -1e-10 || ip1.x > 1.0 + 1e-10 {
                result = false;
            }
        }
        3 => {
            *ip1 = Point { x: 0.0, y: p1.y + t[1] * dy };
            if ip1.y < -1e-10 || ip1.y > 1.0 + 1e-10 {
                result = false;
            }
        }
        _ => result = false,
    }

    match b[2] {
        0 => {
            *ip2 = Point { x: p1.x + t[2] * dx, y: 1.0 };
            if ip2.x < -1e-10 || ip2.x > 1.0 + 1e-10 {
                result = false;
            }
        }
        1 => {
            *ip2 = Point { x: 1.0, y: p1.y + t[2] * dy };
            if ip2.y < -1e-10 || ip2.y > 1.0 + 1e-10 {
                result = false;
            }
        }
        2 => {
            *ip2 = Point { x: p1.x + t[2] * dx, y: 0.0 };
            if ip2.x < -1e-10 || ip2.x > 1.0 + 1e-10 {
                result = false;
            }
        }
        3 => {
            *ip2 = Point { x: 0.0, y: p1.y + t[2] * dy };
            if ip2.y < -1e-10 || ip2.y > 1.0 + 1e-10 {
                result = false;
            }
        }
        _ => result = false,
    }
    result
}

/// `crop_to_unit_box`.
fn crop_to_unit_box(p1: Point, p2: Point, crop1: &mut Point, crop2: &mut Point) -> Crop {
    if (p1.x <= 0.0 && p2.x <= 0.0)
        || (p1.x >= 1.0 && p2.x >= 1.0)
        || (p1.y <= 0.0 && p2.y <= 0.0)
        || (p1.y >= 1.0 && p2.y >= 1.0)
    {
        return Crop::None;
    }

    let p1_inside = p1.x > 0.0 && p1.x < 1.0 && p1.y > 0.0 && p1.y < 1.0;
    let p2_inside = p2.x > 0.0 && p2.x < 1.0 && p2.y > 0.0 && p2.y < 1.0;

    if p1_inside {
        if p2_inside {
            return Crop::Complete;
        }
        *crop1 = entry_intersection(p2, p1);
        return Crop::AtBeginning;
    }

    if p2_inside {
        *crop1 = entry_intersection(p1, p2);
        return Crop::AtEnd;
    }

    if double_intersection(p1, p2, crop1, crop2) {
        Crop::InMiddle
    } else {
        Crop::None
    }
}

fn in_unit_box(p: Point) -> bool {
    p.x > 0.0 && p.x < 1.0 && p.y > 0.0 && p.y < 1.0
}

/// `unitbox_transformer`: maps a rotated box to the unit square.
struct UnitBox {
    m00: f64,
    m01: f64,
    m10: f64,
    m11: f64,
    mi00: f64,
    mi01: f64,
    mi10: f64,
    mi11: f64,
    base: Point,
}

impl UnitBox {
    fn new(low_left: Point, low_right: Point, up_left: Point) -> Result<Self, String> {
        let x0 = low_right.x - low_left.x;
        let y0 = low_right.y - low_left.y;
        let x1 = up_left.x - low_left.x;
        let y1 = up_left.y - low_left.y;

        if (x0 == 0.0 && y0 == 0.0) || (x1 == 0.0 && y1 == 0.0) {
            return Err(SINGULAR.into());
        }
        let denominator = y0 * x1 - y1 * x0;
        if denominator == 0.0 {
            return Err(SINGULAR.into());
        }
        Ok(Self {
            m00: -y1 / denominator,
            m01: x1 / denominator,
            m10: y0 / denominator,
            m11: -x0 / denominator,
            mi00: x0,
            mi01: x1,
            mi10: y0,
            mi11: y1,
            base: low_left,
        })
    }

    fn transform(&self, p: Point) -> Point {
        let x = p.x - self.base.x;
        let y = p.y - self.base.y;
        Point {
            x: self.m00 * x + self.m01 * y,
            y: self.m10 * x + self.m11 * y,
        }
    }

    fn inv_transform(&self, p: Point) -> Point {
        let x = self.mi00 * p.x + self.mi01 * p.y;
        let y = self.mi10 * p.x + self.mi11 * p.y;
        Point {
            x: x + self.base.x,
            y: y + self.base.y,
        }
    }
}

/// `record_points`: append the points that are not yet recorded, starting a new id when needed.
#[allow(clippy::too_many_arguments)]
fn record_points(
    out: &mut Lines,
    p1: Point,
    p2: Point,
    cur_id_out: &mut i32,
    p1_recorded: &mut bool,
    p2_recorded: &mut bool,
    new_line_segment: &mut bool,
) {
    if *new_line_segment && (!*p1_recorded || !*p2_recorded) {
        *cur_id_out += 1;
        *new_line_segment = false;
    }
    if !*p1_recorded {
        out.x.push(p1.x);
        out.y.push(p1.y);
        out.id.push(*cur_id_out);
        *p1_recorded = true;
    }
    if !*p2_recorded {
        out.x.push(p2.x);
        out.y.push(p2.y);
        out.id.push(*cur_id_out);
        *p2_recorded = true;
    }
}

/// `clip_lines_impl` for one box.
#[allow(clippy::too_many_arguments)]
fn clip_one(
    x: &[f64],
    y: &[f64],
    id: &[i32],
    p_mid_x: f64,
    p_mid_y: f64,
    width: f64,
    height: f64,
    theta: f64,
    asp: f64,
) -> Result<Lines, String> {
    let n = x.len();
    if n != y.len() {
        return Err("Number of x and y coordinates must match.".into());
    }
    if n != id.len() {
        return Err("Number of x coordinates and id values must match.".into());
    }
    let mut out = Lines::default();
    if n == 0 {
        return Ok(out);
    }

    let ll = Point {
        x: p_mid_x - width * theta.cos() / 2.0 + (height / asp) * theta.sin() / 2.0,
        y: p_mid_y - asp * width * theta.sin() / 2.0 - height * theta.cos() / 2.0,
    };
    let lr = Point {
        x: ll.x + width * theta.cos(),
        y: ll.y + asp * width * theta.sin(),
    };
    let ul = Point {
        x: ll.x - (height / asp) * theta.sin(),
        y: ll.y + height * theta.cos(),
    };

    let t = UnitBox::new(ll, lr, ul)?;

    let mut cur_id = id[0];
    let mut cur_id_out: i32 = 0;
    let mut p1 = Point { x: x[0], y: y[0] };
    let mut p1t = t.transform(p1);
    let mut p2 = Point::default();
    let mut p2t: Point;
    let mut crop1 = Point::default();
    let mut crop2 = Point::default();

    let mut p1_recorded = in_unit_box(p1t);
    let mut p2_recorded = true;
    let mut new_line_segment = true;

    let mut i = 1usize;
    while i < n {
        if cur_id != id[i] {
            record_points(
                &mut out,
                p1,
                p2,
                &mut cur_id_out,
                &mut p1_recorded,
                &mut p2_recorded,
                &mut new_line_segment,
            );
            p1 = Point { x: x[i], y: y[i] };
            p1t = t.transform(p1);
            cur_id = id[i];
            p1_recorded = in_unit_box(p1t);
            new_line_segment = true;
            i += 1;
            continue;
        }

        p2 = Point { x: x[i], y: y[i] };
        p2t = t.transform(p2);
        p2_recorded = false;
        match crop_to_unit_box(p1t, p2t, &mut crop1, &mut crop2) {
            Crop::Complete => {
                p1_recorded = true;
                p2_recorded = true;
                new_line_segment = true;
            }
            Crop::AtBeginning => {
                p1t = crop1;
                p1 = t.inv_transform(p1t);
                p1_recorded = false;
                new_line_segment = true;
            }
            Crop::AtEnd => {
                p2_recorded = false;
                record_points(
                    &mut out,
                    p1,
                    t.inv_transform(crop1),
                    &mut cur_id_out,
                    &mut p1_recorded,
                    &mut p2_recorded,
                    &mut new_line_segment,
                );
                new_line_segment = true;
            }
            Crop::InMiddle => {
                p2_recorded = false;
                record_points(
                    &mut out,
                    p1,
                    t.inv_transform(crop1),
                    &mut cur_id_out,
                    &mut p1_recorded,
                    &mut p2_recorded,
                    &mut new_line_segment,
                );
                p1t = crop2;
                p1 = t.inv_transform(p1t);
                p1_recorded = false;
                p2_recorded = false;
                new_line_segment = true;
            }
            Crop::None => {}
        }

        record_points(
            &mut out,
            p1,
            p2,
            &mut cur_id_out,
            &mut p1_recorded,
            &mut p2_recorded,
            &mut new_line_segment,
        );
        p1 = p2;
        p1t = p2t;
        i += 1;
    }

    record_points(
        &mut out,
        p1,
        p2,
        &mut cur_id_out,
        &mut p1_recorded,
        &mut p2_recorded,
        &mut new_line_segment,
    );
    Ok(out)
}

/// `clip_lines`: clip the lines against each box in turn. `boxes` rows are (x, y, width, height, theta).
pub fn clip_lines(
    x: &[f64],
    y: &[f64],
    id: &[i32],
    boxes: &[[f64; 5]],
    asp: f64,
) -> Result<Lines, String> {
    let mut cur = Lines {
        x: x.to_vec(),
        y: y.to_vec(),
        id: id.to_vec(),
    };
    for b in boxes {
        cur = clip_one(&cur.x, &cur.y, &cur.id, b[0], b[1], b[2], b[3], b[4], asp)?;
    }
    Ok(cur)
}
