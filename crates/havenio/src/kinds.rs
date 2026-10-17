//! Date and format rules from haven `src/haven_types.cpp`.

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Vendor {
    Spss,
    Stata,
    Sas,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum VarType {
    Default,
    Date,
    Time,
    Datetime,
}

pub fn format_attribute(vendor: Vendor) -> &'static str {
    match vendor {
        Vendor::Stata => "format.stata",
        Vendor::Spss => "format.spss",
        Vendor::Sas => "format.sas",
    }
}

fn has_prefix(text: &str, prefix: &str) -> bool {
    text.starts_with(prefix)
}

pub fn num_type(vendor: Vendor, format: Option<&str>) -> VarType {
    let Some(format) = format else {
        return VarType::Default;
    };
    if format.is_empty() {
        return VarType::Default;
    }
    match vendor {
        Vendor::Sas => {
            if has_prefix(format, "DATETIME")
                || has_prefix(format, "IS8601DT")
                || has_prefix(format, "E8601DT")
                || has_prefix(format, "B8601DT")
            {
                VarType::Datetime
            } else if has_prefix(format, "IS8601DA")
                || has_prefix(format, "E8601DA")
                || has_prefix(format, "B8601DA")
                || has_prefix(format, "WEEKDATE")
                || has_prefix(format, "MMDDYY")
                || has_prefix(format, "DDMMYY")
                || has_prefix(format, "YYMMDD")
                || has_prefix(format, "DATE")
            {
                VarType::Date
            } else if has_prefix(format, "TIME")
                || has_prefix(format, "HHMM")
                || has_prefix(format, "IS8601TM")
                || has_prefix(format, "E8601TM")
                || has_prefix(format, "B8601TM")
            {
                VarType::Time
            } else {
                VarType::Default
            }
        }
        Vendor::Spss => {
            if has_prefix(format, "DATETIME") {
                VarType::Datetime
            } else if has_prefix(format, "DATE")
                || has_prefix(format, "ADATE")
                || has_prefix(format, "EDATE")
                || has_prefix(format, "JDATE")
                || has_prefix(format, "SDATE")
            {
                VarType::Date
            } else if has_prefix(format, "TIME") || has_prefix(format, "DTIME") {
                VarType::Time
            } else {
                VarType::Default
            }
        }
        Vendor::Stata => {
            if has_prefix(format, "%tC") || has_prefix(format, "%tc") {
                VarType::Datetime
            } else if has_prefix(format, "%td") || has_prefix(format, "%d") {
                VarType::Date
            } else {
                VarType::Default
            }
        }
    }
}

fn days_offset(vendor: Vendor) -> f64 {
    match vendor {
        Vendor::Sas | Vendor::Stata => 3653.0,
        Vendor::Spss => 141428.0,
    }
}

pub fn adjust_to_r(vendor: Vendor, kind: VarType, mut value: f64) -> f64 {
    if value.is_nan() {
        return value;
    }
    let offset = days_offset(vendor);
    match kind {
        VarType::Datetime => {
            if vendor == Vendor::Stata {
                value /= 1000.0;
            }
            value - offset * 86400.0
        }
        VarType::Date => {
            if vendor == Vendor::Spss {
                value /= 86400.0;
            }
            value - offset
        }
        _ => value,
    }
}

pub fn adjust_from_r(vendor: Vendor, kind: VarType, mut value: f64) -> f64 {
    if value.is_nan() {
        return value;
    }
    let offset = days_offset(vendor);
    match kind {
        VarType::Datetime => {
            value += offset * 86400.0;
            if vendor == Vendor::Stata {
                value *= 1000.0;
            }
            value
        }
        VarType::Date => {
            value += offset;
            if vendor == Vendor::Spss {
                value *= 86400.0;
            }
            value
        }
        _ => value,
    }
}

pub fn class_type(class: &[String]) -> VarType {
    if class.iter().any(|item| item == "Date") {
        VarType::Date
    } else if class.iter().any(|item| item == "POSIXct") {
        VarType::Datetime
    } else if class.iter().any(|item| item == "hms") {
        VarType::Time
    } else {
        VarType::Default
    }
}

pub fn default_format(vendor: Vendor, kind: VarType) -> Option<&'static str> {
    match kind {
        VarType::Default => None,
        VarType::Datetime => match vendor {
            Vendor::Sas | Vendor::Spss => Some("DATETIME"),
            Vendor::Stata => Some("%tc"),
        },
        VarType::Date => match vendor {
            Vendor::Sas | Vendor::Spss => Some("DATE"),
            Vendor::Stata => Some("%td"),
        },
        VarType::Time => match vendor {
            Vendor::Sas | Vendor::Spss => Some("TIME"),
            Vendor::Stata => None,
        },
    }
}
