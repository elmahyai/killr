// Generated from isoband 0.3.0 src/isoband.cpp by transcribing the switch
// statements of isobander::calculate_contour and isoliner::calculate_contour in
// source order. The case labels, the poly/line calls, and the saddle branches are copied.

use super::grid::PointType;
use super::isobands::Marcher;

impl Marcher {
    pub(crate) fn line_cell(&mut self, cell: i32, r: i32, c: i32) {
        match cell {
            0 => {}
            1 => {
                self.line_start(r, c, PointType::VLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            }
            2 => {
                self.line_start(r, c+1, PointType::VLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            }
            3 => {
                self.line_start(r, c, PointType::VLo);
                self.line_add(r, c+1, PointType::VLo);
                self.line_merge();
            }
            4 => {
                self.line_start(r, c, PointType::HLo);
                self.line_add(r, c+1, PointType::VLo);
                self.line_merge();
            }
            5 => {
            // like case 2
                self.line_start(r, c+1, PointType::VLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            // like case 7
                self.line_start(r, c, PointType::HLo);
                self.line_add(r, c, PointType::VLo);
                self.line_merge();
            }
            6 => {
                self.line_start(r, c, PointType::HLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            }
            7 => {
                self.line_start(r, c, PointType::HLo);
                self.line_add(r, c, PointType::VLo);
                self.line_merge();
            }
            8 => {
                self.line_start(r, c, PointType::HLo);
                self.line_add(r, c, PointType::VLo);
                self.line_merge();
            }
            9 => {
                self.line_start(r, c, PointType::HLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            }
            10 => {
            // like case 1
                self.line_start(r, c, PointType::VLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            // like case 4
                self.line_start(r, c, PointType::HLo);
                self.line_add(r, c+1, PointType::VLo);
                self.line_merge();
            }
            11 => {
                self.line_start(r, c, PointType::HLo);
                self.line_add(r, c+1, PointType::VLo);
                self.line_merge();
            }
            12 => {
                self.line_start(r, c, PointType::VLo);
                self.line_add(r, c+1, PointType::VLo);
                self.line_merge();
            }
            13 => {
                self.line_start(r, c+1, PointType::VLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            }
            14 => {
                self.line_start(r, c, PointType::VLo);
                self.line_add(r+1, c, PointType::HLo);
                self.line_merge();
            }
            _ => {}
        }
    }
}
