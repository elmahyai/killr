//! Roman numeral conversion, ported from gtools `src/roman2int.c`.
//!
//! `C_convert` maps each letter to a value and errors on an invalid character.
//! `C_roman2int` subtracts when a digit is smaller than the next, then adds
//! the last digit. An empty string returns R's `NA_integer_`.

/// R's integer NA (`NA_integer_`).
pub const NA_INTEGER: i32 = i32::MIN;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RomanError {
    InvalidCharacter,
}

fn digit_value(ch: char) -> Result<i32, RomanError> {
    match ch {
        'I' => Ok(1),
        'V' => Ok(5),
        'X' => Ok(10),
        'L' => Ok(50),
        'C' => Ok(100),
        'D' => Ok(500),
        'M' => Ok(1000),
        _ => Err(RomanError::InvalidCharacter),
    }
}

/// `C_convert`: one value per character, upper-case letters only.
pub fn convert_roman_digits(roman: &str) -> Result<Vec<i32>, RomanError> {
    if roman.is_empty() {
        return Ok(Vec::new());
    }
    roman.chars().map(digit_value).collect()
}

/// `C_roman2int` on a string already trimmed and upper-cased.
pub fn roman2int_inner(roman: &str) -> Result<i32, RomanError> {
    let n = roman.len();
    if n < 1 {
        return Ok(NA_INTEGER);
    }
    let values = convert_roman_digits(roman)?;
    let mut total = 0;
    if n > 1 {
        for index in 0..n - 1 {
            if values[index] < values[index + 1] {
                total -= values[index];
            } else {
                total += values[index];
            }
        }
    }
    total += values[n - 1];
    Ok(total)
}

#[cfg(feature = "python")]
mod python {
    use super::{RomanError, roman2int_inner};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    fn inner(roman: &str) -> PyResult<i32> {
        roman2int_inner(roman).map_err(|error| match error {
            RomanError::InvalidCharacter => {
                PyValueError::new_err("Invalid roman numeral in string")
            }
        })
    }

    #[pymodule]
    fn roman2int(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(inner, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{NA_INTEGER, roman2int_inner};

    #[test]
    fn basic_numerals() {
        assert_eq!(roman2int_inner("I").unwrap(), 1);
        assert_eq!(roman2int_inner("IV").unwrap(), 4);
        assert_eq!(roman2int_inner("MMXVI").unwrap(), 2016);
        assert_eq!(roman2int_inner("MMMDCCCXCIX").unwrap(), 3899);
        assert_eq!(roman2int_inner("MMMCM").unwrap(), 3900);
        assert_eq!(roman2int_inner("MMMM").unwrap(), 4000);
    }

    #[test]
    fn empty_is_na() {
        assert_eq!(roman2int_inner("").unwrap(), NA_INTEGER);
    }

    #[test]
    fn invalid_char_errors() {
        assert!(roman2int_inner("X1").is_err());
    }
}
