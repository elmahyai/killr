// Generated from isoband 0.3.0 src/isoband.cpp by transcribing the switch
// statements of isobander::calculate_contour and isoliner::calculate_contour in
// source order. The case labels, the poly/line calls, and the saddle branches are copied.

use super::grid::PointType;
use super::isobands::Marcher;

impl Marcher {
    pub(crate) fn band_cell(&mut self, cell: i32, r: i32, c: i32) {
        match cell {
            // doing cases out of order, sorted by type, is easier to keep track of
            // no contour
            0 => {}
            80 => {}
            // single triangle
            1 => { // 0001
                self.poly_start(r, c, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            3 => { // 0010
                self.poly_start(r, c+1, PointType::VLo);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_merge();
            }
            9 => { // 0100
                self.poly_start(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_merge();
            }
            27 => { // 1000
                self.poly_start(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HLo);
                self.poly_merge();
            }
            79 => { // 2221
                self.poly_start(r, c, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            77 => { // 2212
                self.poly_start(r, c+1, PointType::VHi);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_merge();
            }
            71 => { // 2122
                self.poly_start(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_merge();
            }
            53 => { // 1222
                self.poly_start(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HHi);
                self.poly_merge();
            // single trapezoid
            }
            78 => { // 2220
                self.poly_start(r, c, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            74 => { // 2202
                self.poly_start(r+1, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_merge();
            }
            62 => { // 2022
                self.poly_start(r, c+1, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_merge();
            }
            26 => { // 0222
                self.poly_start(r, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_merge();
            }
            2 => { // 0002
                self.poly_start(r, c, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            6 => { // 0020
                self.poly_start(r+1, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_merge();
            }
            18 => { // 0200
                self.poly_start(r, c+1, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_merge();
            }
            54 => { // 2000
                self.poly_start(r, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_merge();
            // single rectangle
            }
            4 => { // 0011
                self.poly_start(r, c, PointType::VLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            12 => { // 0110
                self.poly_start(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_merge();
            }
            36 => { // 1100
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            28 => { // 1001
                self.poly_start(r, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::Grid);
                self.poly_merge();
            }
            76 => { // 2211
                self.poly_start(r, c, PointType::VHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            68 => { // 2112
                self.poly_start(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_merge();
            }
            44 => { // 1122
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            52 => { // 1221
                self.poly_start(r, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::Grid);
                self.poly_merge();
            }
            72 => { // 2200
                self.poly_start(r, c, PointType::VHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            56 => { // 2002
                self.poly_start(r, c, PointType::HHi);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_merge();
            }
            8 => { // 0022
                self.poly_start(r, c, PointType::VLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            24 => { // 0220
                self.poly_start(r, c, PointType::HLo);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_merge();
            // single square
            }
            40 => { // 1111
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            // single pentagon
            }
            49 => { // 1211
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            67 => { // 2111
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_merge();
            }
            41 => { // 1112
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            43 => { // 1121
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            31 => { // 1011
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            13 => { // 0111
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_merge();
            }
            39 => { // 1110
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            37 => { // 1101
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            45 => { // 1200
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            15 => { // 0120
                self.poly_start(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_merge();
            }
            5 => { // 0012
                self.poly_start(r, c, PointType::VLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            55 => { // 2001
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_merge();
            }
            35 => { // 1022
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            65 => { // 2102
                self.poly_start(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_merge();
            }
            75 => { // 2210
                self.poly_start(r, c, PointType::VHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            25 => { // 0221
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_merge();
            }
            29 => { // 1002
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            63 => { // 2100
                self.poly_start(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_merge();
            }
            21 => { // 0210
                self.poly_start(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_merge();
            }
            7 => { // 0021
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_merge();
            }
            51 => { // 1220
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            17 => { // 0122
                self.poly_start(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_merge();
            }
            59 => { // 2012
                self.poly_start(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_merge();
            }
            73 => { // 2201
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_merge();
            // single hexagon
            }
            22 => { // 0211
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_merge();
            }
            66 => { // 2110
                self.poly_start(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_merge();
            }
            38 => { // 1102
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            34 => { // 1021
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            58 => { // 2011
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_merge();
            }
            14 => { // 0112
                self.poly_start(r, c+1, PointType::Grid);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_merge();
            }
            42 => { // 1120
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            }
            46 => { // 1201
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_merge();
            }
            64 => { // 2101
                self.poly_start(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VHi);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_merge();
            }
            16 => { // 0121
                self.poly_start(r, c+1, PointType::Grid);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r+1, c, PointType::Grid);
                self.poly_add(r, c, PointType::VLo);
                self.poly_add(r, c, PointType::HLo);
                self.poly_merge();
            }
            32 => { // 1012
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HLo);
                self.poly_add(r, c+1, PointType::VLo);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HHi);
                self.poly_add(r, c, PointType::VHi);
                self.poly_merge();
            }
            48 => { // 1210
                self.poly_start(r, c, PointType::Grid);
                self.poly_add(r, c, PointType::HHi);
                self.poly_add(r, c+1, PointType::VHi);
                self.poly_add(r+1, c+1, PointType::Grid);
                self.poly_add(r+1, c, PointType::HLo);
                self.poly_add(r, c, PointType::VLo);
                self.poly_merge();
            // 6-sided saddle
            }
            10 => { // 0101
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_merge();
                        } else {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_merge();
                        }
                    }
            }
            30 => { // 1010
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        self.poly_start(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        }
                    }
            }
            70 => { // 2121
                {
                    let vc = self.central_value(r, c);
                    if vc >= self.vhi {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_merge();
                        } else {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_merge();
                        }
                    }
            }
            50 => { // 1212
                {
                    let vc = self.central_value(r, c);
                    if vc >= self.vhi {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        self.poly_start(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        }
                    }
            // 7-sided saddle
            }
            69 => { // 2120
                {
                    let vc = self.central_value(r, c);
                    if vc >= self.vhi {
                        self.poly_start(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_merge();
                        self.poly_start(r, c, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_merge();
                        }
                    }
            }
            61 => { // 2021
                {
                    let vc = self.central_value(r, c);
                    if vc >= self.vhi {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_merge();
                        } else {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_merge();
                        }
                    }
            }
            47 => { // 1202
                {
                    let vc = self.central_value(r, c);
                    if vc >= self.vhi {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        self.poly_start(r+1, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        }
                    }
            }
            23 => { // 0212
                {
                    let vc = self.central_value(r, c);
                    if vc >= self.vhi {
                        self.poly_start(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_merge();
                        self.poly_start(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_merge();
                        } else {
                        self.poly_start(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_merge();
                        }
                    }
            }
            11 => { // 0102
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_merge();
                        self.poly_start(r, c, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c+1, PointType::Grid);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_merge();
                        }
                    }
            }
            19 => { // 0201
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_merge();
                        } else {
                        self.poly_start(r+1, c, PointType::Grid);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_merge();
                        }
                    }
            }
            33 => { // 1020
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        self.poly_start(r+1, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c, PointType::Grid);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        }
                    }
            }
            57 => { // 2010
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_merge();
                        self.poly_start(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_merge();
                        } else {
                        self.poly_start(r+1, c+1, PointType::Grid);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_merge();
                        }
                    }
            // 8-sided saddle
            }
            60 => { // 2020
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_merge();
                        } else if vc >= self.vhi {
                        self.poly_start(r, c, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c, PointType::VHi);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r, c, PointType::VLo);
                        self.poly_merge();
                        }
                    }
            }
            20 => { // 0202
                {
                    let vc = self.central_value(r, c);
                    if vc < self.vlo {
                        self.poly_start(r, c, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_merge();
                        } else if vc >= self.vhi {
                        self.poly_start(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        self.poly_start(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_merge();
                        } else {
                        self.poly_start(r, c, PointType::VLo);
                        self.poly_add(r, c, PointType::HLo);
                        self.poly_add(r, c, PointType::HHi);
                        self.poly_add(r, c+1, PointType::VHi);
                        self.poly_add(r, c+1, PointType::VLo);
                        self.poly_add(r+1, c, PointType::HLo);
                        self.poly_add(r+1, c, PointType::HHi);
                        self.poly_add(r, c, PointType::VHi);
                        self.poly_merge();
                        }
                    }
            }
            _ => {}
        }
    }
}
