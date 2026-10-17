//! `convertDate` from data.table `src/idatetime.c`.
//!
//! `x` is days since 1970-01-01. Missing input is `NA_INTEGER`. `week` returns
//! the legacy numbering: `yday / 7 + 1`. `yearmon` and `yearqtr` are doubles.

pub const NA_INTEGER: i32 = i32::MIN;

const YEARS400: i32 = 146097;
const YEARS100: i32 = 36524;
const YEARS4: i32 = 1461;
const YEARS1: i32 = 365;

#[derive(Clone, Copy)]
pub enum DatePart {
    Yday,
    Wday,
    Mday,
    Week,
    Month,
    Quarter,
    Year,
    Yearmon,
    Yearqtr,
}

pub fn parse_part(name: &str) -> Option<DatePart> {
    match name {
        "yday" => Some(DatePart::Yday),
        "wday" => Some(DatePart::Wday),
        "mday" => Some(DatePart::Mday),
        "week" => Some(DatePart::Week),
        "month" => Some(DatePart::Month),
        "quarter" => Some(DatePart::Quarter),
        "year" => Some(DatePart::Year),
        "yearmon" => Some(DatePart::Yearmon),
        "yearqtr" => Some(DatePart::Yearqtr),
        _ => None,
    }
}

pub fn convert_dates(days: &[i32], part: DatePart) -> Vec<f64> {
    days.iter().map(|&day| convert_one(day, part)).collect()
}

fn convert_one(x: i32, part: DatePart) -> f64 {
    if x == NA_INTEGER {
        return f64::NAN;
    }
    if matches!(part, DatePart::Wday) {
        let mut wday = (x + 4) % 7;
        if wday < 0 {
            wday += 7;
        }
        return (wday + 1) as f64;
    }
    if matches!(part, DatePart::Week) {
        let yday = convert_one(x, DatePart::Yday) as i32;
        return ((yday / 7) + 1) as f64;
    }

    let mut days = x - 11017;
    let mut years400 = days / YEARS400;
    days %= YEARS400;
    if days < 0 {
        days += YEARS400;
        years400 -= 1;
    }
    let years100 = days / YEARS100;
    days %= YEARS100;
    let years4 = days / YEARS4;
    days %= YEARS4;
    let years1 = days / YEARS1;
    days %= YEARS1;
    let mut year = 2000 + years1 + 4 * years4 + 100 * years100 + 400 * years400;
    if days > 305 {
        year += 1;
    }
    if matches!(part, DatePart::Year) {
        return year as f64;
    }
    let leap = years1 == 0 && (years4 != 0 || years100 == 0);
    if matches!(part, DatePart::Yday) {
        let mut yday = days + 31 + 28 + i32::from(leap);
        if yday >= YEARS1 + i32::from(leap) {
            yday -= YEARS1 + i32::from(leap);
        }
        return (yday + 1) as f64;
    }
    const MONTHS: [i32; 12] = [31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 31, 29];
    if matches!(part, DatePart::Month | DatePart::Yearmon) {
        let index = if days == 0 && !leap && is_leap_year(year) {
            1
        } else {
            let mut i = 2;
            let mut left = days;
            while MONTHS[(i - 2) as usize] <= left {
                left -= MONTHS[(i - 2) as usize];
                i += 1;
            }
            i
        };
        let index = if index >= 12 { index - 12 } else { index };
        return if matches!(part, DatePart::Month) {
            (index + 1) as f64
        } else {
            year as f64 + (index as f64) / 12.0
        };
    }
    if matches!(part, DatePart::Mday) {
        if days == 0 && !leap && is_leap_year(year) {
            return 29.0;
        }
        let mut i = 0;
        let mut left = days;
        while MONTHS[i] <= left {
            left -= MONTHS[i];
            i += 1;
        }
        return (left + 1) as f64;
    }
    const QUARTER: [i32; 5] = [31, 91, 92, 92, 60];
    let mut i = 0;
    let mut left = days;
    while QUARTER[i] <= left {
        left -= QUARTER[i];
        i += 1;
    }
    if i >= 4 {
        i -= 4;
    }
    if matches!(part, DatePart::Quarter) {
        (i + 1) as f64
    } else {
        year as f64 + (i as f64) / 4.0
    }
}

fn is_leap_year(year: i32) -> bool {
    (year % 100 != 0 || year % 400 == 0) && year % 4 == 0
}
