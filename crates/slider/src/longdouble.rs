//! x87 80-bit float, the `long double` that R's slider accumulates in.
//!
//! `sum`, `prod`, and `mean` build their segment-tree nodes in `long double`
//! and only round to double when the window is finalized, so a double
//! accumulator drifts. Rust has no 80-bit type, so the arithmetic runs on the
//! x87 stack through inline assembly: `fld`/`faddp`/`fmulp` round once per
//! operation to 64-bit mantissa, exactly as the C does on this target.
//!
//! An `F80` is the 10-byte x87 image zero-extended to 16 bytes, the same
//! layout `sizeof(long double) == 16` gives on x86-64.

/// x87 extended precision value in its in-memory form.
///
/// Opaque: build it with [`F80::from_f64`], combine
/// with the arithmetic methods, and read it back with [`F80::to_f64`].
#[derive(Clone, Copy)]
#[repr(C, align(16))]
pub struct F80([u8; 16]);

impl F80 {
    /// One, the state `prod_state_reset` and every interior product node use.
    pub fn one() -> F80 {
        F80::from_f64(1.0)
    }

    /// Widen a double without changing its value.
    pub fn from_f64(value: f64) -> F80 {
        let mut out = F80([0; 16]);
        unsafe {
            core::arch::asm!(
                "fld qword ptr [{src}]",
                "fstp tbyte ptr [{dst}]",
                src = in(reg) &value,
                dst = in(reg) out.0.as_mut_ptr(),
                options(nostack),
            );
        }
        out
    }

    /// Narrow to double. The x87 unit rounds to nearest-even, as the C cast.
    pub fn to_f64(self) -> f64 {
        let mut out = 0.0f64;
        unsafe {
            core::arch::asm!(
                "fld tbyte ptr [{src}]",
                "fstp qword ptr [{dst}]",
                src = in(reg) self.0.as_ptr(),
                dst = in(reg) &mut out,
                options(nostack),
            );
        }
        out
    }

    /// `self + other` in 80-bit, rounding once.
    pub fn add(self, other: F80) -> F80 {
        let mut out = F80([0; 16]);
        unsafe {
            core::arch::asm!(
                "fld tbyte ptr [{a}]",
                "fld tbyte ptr [{b}]",
                "faddp st(1), st(0)",
                "fstp tbyte ptr [{dst}]",
                a = in(reg) self.0.as_ptr(),
                b = in(reg) other.0.as_ptr(),
                dst = in(reg) out.0.as_mut_ptr(),
                options(nostack),
            );
        }
        out
    }

    /// `self * other` in 80-bit, rounding once.
    pub fn mul(self, other: F80) -> F80 {
        let mut out = F80([0; 16]);
        unsafe {
            core::arch::asm!(
                "fld tbyte ptr [{a}]",
                "fld tbyte ptr [{b}]",
                "fmulp st(1), st(0)",
                "fstp tbyte ptr [{dst}]",
                a = in(reg) self.0.as_ptr(),
                b = in(reg) other.0.as_ptr(),
                dst = in(reg) out.0.as_mut_ptr(),
                options(nostack),
            );
        }
        out
    }

    /// `self / other` in 80-bit, rounding once.
    pub fn div(self, other: F80) -> F80 {
        let mut out = F80([0; 16]);
        unsafe {
            core::arch::asm!(
                "fld tbyte ptr [{a}]",
                "fld tbyte ptr [{b}]",
                "fdivp st(1), st(0)",
                "fstp tbyte ptr [{dst}]",
                a = in(reg) self.0.as_ptr(),
                b = in(reg) other.0.as_ptr(),
                dst = in(reg) out.0.as_mut_ptr(),
                options(nostack),
            );
        }
        out
    }

    /// True when the 80-bit value is any NaN. `isnan()` in the C.
    pub fn is_nan(self) -> bool {
        self.to_f64().is_nan()
    }

    /// Compare with `>` at 80-bit precision. R's `state > DBL_MAX` guards.
    pub fn gt(self, other: F80) -> bool {
        let out: u8 = 0;
        unsafe {
            core::arch::asm!(
                "fld tbyte ptr [{b}]",
                "fld tbyte ptr [{a}]",
                "fucomip st, st(1)",
                "fstp st(0)",
                "seta {dst}",
                a = in(reg) self.0.as_ptr(),
                b = in(reg) other.0.as_ptr(),
                dst = in(reg_byte) out,
                options(nostack),
            );
        }
        out != 0
    }

    /// Compare with `<` at 80-bit precision. R's `state < -DBL_MAX` guard.
    pub fn lt(self, other: F80) -> bool {
        let out: u8 = 0;
        unsafe {
            core::arch::asm!(
                "fld tbyte ptr [{b}]",
                "fld tbyte ptr [{a}]",
                "fucomip st, st(1)",
                "fstp st(0)",
                "setb {dst}",
                a = in(reg) self.0.as_ptr(),
                b = in(reg) other.0.as_ptr(),
                dst = in(reg_byte) out,
                options(nostack),
            );
        }
        out != 0
    }
}

impl Default for F80 {
    fn default() -> Self {
        F80::from_f64(0.0)
    }
}

/// `long double` -> double with R's `sum_state_finalize` clamp: a state past
/// `DBL_MAX` becomes an infinity rather than the double it would round to.
pub fn finalize(state: F80) -> f64 {
    let limit = F80::from_f64(f64::MAX);
    if state.gt(limit) {
        f64::INFINITY
    } else if state.lt(limit.neg()) {
        f64::NEG_INFINITY
    } else {
        state.to_f64()
    }
}

impl F80 {
    /// `-self` in 80-bit, used to test `state < -DBL_MAX`.
    pub fn neg(self) -> F80 {
        let mut out = self.0;
        out[9] ^= 0x80;
        F80(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trips_doubles() {
        for value in [0.0, 1.0, -2.5, 1e300, 1e-300, f64::INFINITY] {
            assert_eq!(F80::from_f64(value).to_f64(), value);
        }
    }

    #[test]
    fn keeps_precision_a_double_would_lose() {
        // 1e16 + 1 is exactly 1e16 in double; the 80-bit accumulator keeps it.
        // slider's slide_sum(c(1e16, 1e16, 1, 1, 4), before = Inf) ends on
        // 20000000000000008, which a double accumulator cannot reach.
        let mut sum = F80::from_f64(0.0);
        for value in [1e16, 1e16, 1.0, 1.0, 4.0] {
            sum = sum.add(F80::from_f64(value));
        }
        assert_eq!(sum.to_f64(), 20000000000000008.0);
    }

    #[test]
    fn zero_plus_negates_back_to_zero() {
        let sum = F80::from_f64(1e16)
            .add(F80::from_f64(1.0))
            .add(F80::from_f64(-1e16))
            .add(F80::from_f64(1e16))
            .add(F80::from_f64(3.0));
        assert_eq!(finalize(sum), 10000000000000004.0);
    }

    #[test]
    fn na_real_entering_the_x87_unit_is_quieted_like_r() {
        // `slide_sum(c(1, NA), before = 1)[2]` is 0x7ff80000000007a2 in R: the
        // NA payload survives but the quiet bit is raised. That is what the
        // double -> long double conversion gives, so sum and mean match. Min
        // and max never enter this unit and keep 0x7ff00000000007a2.
        let na = F80::from_f64(f64::from_bits(0x7ff0_0000_0000_07a2));
        assert!(na.is_nan());
        assert_eq!(na.to_f64().to_bits(), 0x7ff8_0000_0000_07a2);
    }

    #[test]
    fn adding_na_quiets_the_payload_as_r_does() {
        // R's slide_sum(c(1, NA), before = 1)[2] is 0x7ff80000000007a2: the
        // x87 add raises the quiet bit but keeps the NA payload.
        let sum = F80::from_f64(1.0).add(F80::from_f64(f64::from_bits(0x7ff0_0000_0000_07a2)));
        assert_eq!(sum.to_f64().to_bits(), 0x7ff8_0000_0000_07a2);
    }

    #[test]
    fn inf_minus_inf_makes_nan() {
        let inf = F80::from_f64(f64::INFINITY);
        assert!(inf.neg().add(inf).is_nan());
    }

    #[test]
    fn clamps_past_double_max() {
        let big = F80::from_f64(1e308).mul(F80::from_f64(10.0));
        assert_eq!(finalize(big), f64::INFINITY);
        assert_eq!(finalize(big.neg()), f64::NEG_INFINITY);
    }
}
