//! Data-frame writer, ported from haven `src/DfWriter.cpp`.

use std::collections::HashMap;
use std::ffi::{CString, c_void};
use std::fs::File;
use std::io::Write;
use std::os::raw::c_char;

use crate::kinds::{self, Vendor};
use crate::na::tagged_na_value;
use crate::sys;

#[derive(Clone)]
pub enum Storage {
    Double(Vec<f64>),
    Integer(Vec<i32>),
    Logical(Vec<i32>),
    String(Vec<Option<String>>),
}

pub struct WriteColumn {
    pub name: String,
    pub storage: Storage,
    pub label: Option<String>,
    pub labels_double: Vec<f64>,
    pub labels_int: Vec<i32>,
    pub labels_string: Vec<String>,
    pub label_names: Vec<String>,
    pub class: Vec<String>,
    pub format_stata: Option<String>,
    pub format_spss: Option<String>,
    pub format_sas: Option<String>,
    pub display_width: i32,
    pub width: i32,
    pub na_values_double: Vec<f64>,
    pub na_values_int: Vec<i32>,
    pub na_values_string: Vec<String>,
    pub na_range_double: Option<(f64, f64)>,
    pub na_range_string: Option<(String, String)>,
    pub levels: Vec<String>,
    pub ordered: bool,
    pub spss: bool,
    pub labelled: bool,
}

pub struct WriteTable {
    pub columns: Vec<WriteColumn>,
    pub label: Option<String>,
}

struct OutFile {
    file: File,
}

extern "C" fn data_writer(data: *const c_void, len: usize, ctx: *mut c_void) -> isize {
    let out = unsafe { &mut *(ctx as *mut OutFile) };
    let bytes = unsafe { std::slice::from_raw_parts(data as *const u8, len) };
    match out.file.write_all(bytes) {
        Ok(()) => len as isize,
        Err(_) => -1,
    }
}

fn c_string(text: &str) -> Result<CString, String> {
    CString::new(text).map_err(|_| "text contains a nul".into())
}

fn check(err: sys::readstat_error_t, message: &str) -> Result<(), String> {
    if err == 0 {
        Ok(())
    } else {
        let detail = unsafe { crate::c_text(sys::readstat_error_message(err)) };
        Err(format!("{message}: {detail}."))
    }
}

pub struct WriteOptions {
    pub kind: String,
    pub path: String,
    pub version: i32,
    pub label: Option<String>,
    pub strl_threshold: i32,
    pub compress: String,
    pub name: Option<String>,
}

pub fn write_table(table: &WriteTable, options: &WriteOptions) -> Result<Vec<String>, String> {
    let vendor = match options.kind.as_str() {
        "sav" | "por" => Vendor::Spss,
        "dta" => Vendor::Stata,
        "sas" | "xpt" => Vendor::Sas,
        other => return Err(format!("unknown file kind {other}")),
    };
    let file = File::create(&options.path).map_err(|err| format!("Failed to open '{}' for writing: {err}", options.path))?;
    let mut out = OutFile { file };
    let writer = unsafe { sys::readstat_writer_init() };
    if writer.is_null() {
        return Err("Failed to create the ReadStat writer.".into());
    }
    let mut warnings = Vec::new();
    let mut kept: Vec<CString> = Vec::new();
    let result = (|| {
        check(
            unsafe { sys::readstat_set_data_writer(writer, Some(data_writer)) },
            "Writing failure",
        )?;
        if options.kind == "sav" {
            let compress = match options.compress.as_str() {
                "zsav" => 2,
                "none" => 0,
                _ => 1,
            };
            check(
                unsafe { sys::readstat_writer_set_compression(writer, compress) },
                "Writing failure",
            )?;
        }
        if options.kind == "dta" {
            check(
                unsafe { sys::readstat_writer_set_file_format_version(writer, options.version as u8) },
                "Writing failure",
            )?;
        }
        if options.kind == "xpt" {
            check(
                unsafe { sys::readstat_writer_set_file_format_version(writer, options.version as u8) },
                "Writing failure",
            )?;
            if let Some(name) = &options.name {
                let name = c_string(name)?;
                check(
                    unsafe { sys::readstat_writer_set_table_name(writer, name.as_ptr()) },
                    "Writing failure",
                )?;
                kept.push(name);
            }
        }
        if let Some(label) = options.label.as_deref().or(table.label.as_deref()) {
            let label = c_string(label)?;
            check(
                unsafe { sys::readstat_writer_set_file_label(writer, label.as_ptr()) },
                "Writing failure",
            )?;
            kept.push(label);
        }
        let nrow = table.columns.first().map(|column| column.len()).unwrap_or(0);
        if table.columns.is_empty() {
            return Ok(warnings);
        }
        let status = unsafe {
            match options.kind.as_str() {
                "sav" => sys::readstat_begin_writing_sav(writer, &mut out as *mut OutFile as *mut c_void, nrow as i64),
                "dta" => sys::readstat_begin_writing_dta(writer, &mut out as *mut OutFile as *mut c_void, nrow as i64),
                "sas" => sys::readstat_begin_writing_sas7bdat(writer, &mut out as *mut OutFile as *mut c_void, nrow as i64),
                "xpt" => sys::readstat_begin_writing_xport(writer, &mut out as *mut OutFile as *mut c_void, nrow as i64),
                "por" => sys::readstat_begin_writing_por(writer, &mut out as *mut OutFile as *mut c_void, nrow as i64),
                _ => 4,
            }
        };
        check(status, "Failed to create file")?;
        check(unsafe { sys::readstat_validate_metadata(writer) }, "Failed to write metadata")?;

        let mut refs: HashMap<String, *mut sys::readstat_string_ref_t> = HashMap::new();
        for column in &table.columns {
            define_column(writer, column, vendor, options, &mut kept, &mut refs, &mut warnings)?;
        }
        for row in 0..nrow {
            check(unsafe { sys::readstat_begin_row(writer) }, "Writing failure")?;
            for (j, column) in table.columns.iter().enumerate() {
                let var = unsafe { sys::readstat_get_variable(writer, j as i32) };
                let status = insert_value(writer, var, column, vendor, row, &refs)?;
                if status != 0 {
                    let detail = unsafe { crate::c_text(sys::readstat_error_message(status)) };
                    return Err(format!("Failed to insert value [{}, {}]: {detail}.", row + 1, j + 1));
                }
            }
            check(unsafe { sys::readstat_end_row(writer) }, "Writing failure")?;
        }
        check(unsafe { sys::readstat_end_writing(writer) }, "Writing failure")?;
        Ok(warnings)
    })();
    unsafe { sys::readstat_writer_free(writer) };
    result
}

impl WriteColumn {
    fn len(&self) -> usize {
        match &self.storage {
            Storage::Double(values) => values.len(),
            Storage::Integer(values) | Storage::Logical(values) => values.len(),
            Storage::String(values) => values.len(),
        }
    }
}

fn define_column(
    writer: *mut sys::readstat_writer_t,
    column: &WriteColumn,
    vendor: Vendor,
    options: &WriteOptions,
    kept: &mut Vec<CString>,
    refs: &mut HashMap<String, *mut sys::readstat_string_ref_t>,
    warnings: &mut Vec<String>,
) -> Result<(), String> {
    let name = c_string(&column.name)?;
    let kind = kinds::class_type(&column.class);
    let format_owned = match vendor {
        Vendor::Stata => column.format_stata.clone(),
        Vendor::Spss => column.format_spss.clone(),
        Vendor::Sas => column.format_sas.clone(),
    };
    let format_static = if format_owned.is_some() {
        None
    } else {
        kinds::default_format(vendor, kind)
    };
    let format_ptr = if let Some(format) = &format_owned {
        let format = c_string(format)?;
        let ptr = format.as_ptr();
        kept.push(format);
        ptr
    } else if let Some(format) = format_static {
        let format = c_string(format)?;
        let ptr = format.as_ptr();
        kept.push(format);
        ptr
    } else {
        std::ptr::null()
    };
    let label_ptr = if let Some(label) = &column.label {
        let label = c_string(label)?;
        let ptr = label.as_ptr();
        kept.push(label);
        ptr
    } else {
        std::ptr::null()
    };

    let (type_code, storage_width, _string_ref): (u32, usize, bool) = match &column.storage {
        Storage::String(values) => {
            let mut width = column.width.max(0) as usize;
            let mut max_length = 1usize;
            for value in values {
                let length = value.as_ref().map(|item| item.len()).unwrap_or(0);
                max_length = max_length.max(length);
            }
            if max_length > width {
                if width > 0 {
                    warnings.push(format!(
                        "Column `{}` contains string values longer than user width {width}. Width set to {max_length} to accommodate.",
                        column.name
                    ));
                }
                width = max_length;
            }
            let use_ref = options.kind == "dta" && options.version >= 117 && width as i32 > options.strl_threshold;
            if use_ref {
                for value in values.iter().flatten() {
                    if !refs.contains_key(value) {
                        let text = c_string(value)?;
                        let reference = unsafe { sys::readstat_add_string_ref(writer, text.as_ptr()) };
                        kept.push(text);
                        refs.insert(value.clone(), reference);
                    }
                }
                (6, width, true)
            } else {
                (0, width, false)
            }
        }
        Storage::Double(_) => (5, column.width.max(0) as usize, false),
        Storage::Integer(_) | Storage::Logical(_) => (3, column.width.max(0) as usize, false),
    };
    let variable = unsafe {
        sys::readstat_add_variable(writer, name.as_ptr(), type_code, storage_width)
    };
    kept.push(name);
    if variable.is_null() {
        return Err(format!("Failed to create column `{}`.", column.name));
    }
    unsafe {
        sys::readstat_variable_set_format(variable, format_ptr);
        sys::readstat_variable_set_label(variable, label_ptr);
        sys::readstat_variable_set_measure(variable, measure(column));
        sys::readstat_variable_set_display_width(variable, column.display_width);
    }
    attach_labels(writer, variable, column, type_code, kept)?;
    attach_missing(variable, column)?;
    check(
        unsafe { sys::readstat_validate_variable(writer, variable) },
        &format!("Failed to create column `{}`", column.name),
    )
}

fn measure(column: &WriteColumn) -> u32 {
    if column.ordered {
        3
    } else if !column.levels.is_empty() {
        2
    } else {
        match column.storage {
            Storage::Integer(_) | Storage::Double(_) => 4,
            Storage::Logical(_) | Storage::String(_) => 2,
        }
    }
}

fn attach_labels(
    writer: *mut sys::readstat_writer_t,
    variable: *mut sys::readstat_variable_t,
    column: &WriteColumn,
    type_code: u32,
    kept: &mut Vec<CString>,
) -> Result<(), String> {
    if !column.levels.is_empty() {
        let set_name = c_string(&column.name)?;
        let set = unsafe { sys::readstat_add_label_set(writer, 3, set_name.as_ptr()) };
        kept.push(set_name);
        for (i, level) in column.levels.iter().enumerate() {
            let level = c_string(level)?;
            unsafe { sys::readstat_label_int32_value(set, (i as i32) + 1, level.as_ptr()) };
            kept.push(level);
        }
        unsafe { sys::readstat_variable_set_label_set(variable, set) };
        return Ok(());
    }
    if !column.labelled || column.label_names.is_empty() {
        return Ok(());
    }
    let set_name = c_string(&column.name)?;
    let set = unsafe { sys::readstat_add_label_set(writer, type_code, set_name.as_ptr()) };
    kept.push(set_name);
    if !column.labels_int.is_empty() {
        for (value, name) in column.labels_int.iter().zip(&column.label_names) {
            let name = c_string(name)?;
            unsafe { sys::readstat_label_int32_value(set, *value, name.as_ptr()) };
            kept.push(name);
        }
    } else if !column.labels_double.is_empty() {
        for (value, name) in column.labels_double.iter().zip(&column.label_names) {
            let name = c_string(name)?;
            if !value.is_nan() || tagged_na_value(*value) == 0 {
                unsafe { sys::readstat_label_double_value(set, *value, name.as_ptr()) };
            } else {
                unsafe { sys::readstat_label_tagged_value(set, tagged_na_value(*value) as c_char, name.as_ptr()) };
            }
            kept.push(name);
        }
    } else {
        for (value, name) in column.labels_string.iter().zip(&column.label_names) {
            let value = c_string(value)?;
            let name = c_string(name)?;
            unsafe { sys::readstat_label_string_value(set, value.as_ptr(), name.as_ptr()) };
            kept.push(value);
            kept.push(name);
        }
    }
    unsafe { sys::readstat_variable_set_label_set(variable, set) };
    Ok(())
}

fn attach_missing(variable: *mut sys::readstat_variable_t, column: &WriteColumn) -> Result<(), String> {
    if !column.spss {
        return Ok(());
    }
    unsafe {
        if let Some((lo, hi)) = column.na_range_double {
            sys::readstat_variable_add_missing_double_range(variable, lo, hi);
        }
        for value in &column.na_values_double {
            sys::readstat_variable_add_missing_double_value(variable, *value);
        }
        for value in &column.na_values_int {
            sys::readstat_variable_add_missing_double_value(variable, *value as f64);
        }
        if let Some((lo, hi)) = &column.na_range_string {
            let lo = c_string(lo)?;
            let hi = c_string(hi)?;
            sys::readstat_variable_add_missing_string_range(variable, lo.as_ptr(), hi.as_ptr());
        }
        for value in &column.na_values_string {
            let value = c_string(value)?;
            sys::readstat_variable_add_missing_string_value(variable, value.as_ptr());
        }
    }
    Ok(())
}

fn insert_value(
    writer: *mut sys::readstat_writer_t,
    variable: *mut sys::readstat_variable_t,
    column: &WriteColumn,
    vendor: Vendor,
    row: usize,
    refs: &HashMap<String, *mut sys::readstat_string_ref_t>,
) -> Result<sys::readstat_error_t, String> {
    let kind = kinds::class_type(&column.class);
    Ok(match &column.storage {
        Storage::Logical(values) => {
            let value = values[row];
            if value == i32::MIN {
                unsafe { sys::readstat_insert_missing_value(writer, variable) }
            } else {
                unsafe { sys::readstat_insert_int32_value(writer, variable, value) }
            }
        }
        Storage::Integer(values) => {
            let value = values[row];
            if value == i32::MIN {
                unsafe { sys::readstat_insert_missing_value(writer, variable) }
            } else {
                let adjusted = kinds::adjust_from_r(vendor, kind, value as f64) as i32;
                unsafe { sys::readstat_insert_int32_value(writer, variable, adjusted) }
            }
        }
        Storage::Double(values) => {
            let value = values[row];
            let adjusted = kinds::adjust_from_r(vendor, kind, value);
            if !adjusted.is_finite() {
                let tag = tagged_na_value(value);
                if tag == 0 {
                    unsafe { sys::readstat_insert_missing_value(writer, variable) }
                } else {
                    unsafe { sys::readstat_insert_tagged_missing_value(writer, variable, tag as c_char) }
                }
            } else {
                unsafe { sys::readstat_insert_double_value(writer, variable, adjusted) }
            }
        }
        Storage::String(values) => {
            if values[row].is_none() {
                unsafe { sys::readstat_insert_missing_value(writer, variable) }
            } else {
                let text = values[row].as_deref().unwrap_or("");
                let code = unsafe { sys::readstat_variable_get_type(variable) as u32 };
                if code == 6 {
                    let reference = refs.get(text).copied().unwrap_or(std::ptr::null_mut());
                    unsafe { sys::readstat_insert_string_ref(writer, variable, reference) }
                } else {
                    let text = c_string(text)?;
                    let status = unsafe { sys::readstat_insert_string_value(writer, variable, text.as_ptr()) };
                    status
                }
            }
        }
    })
}
