//! Data-frame reader, ported from haven `src/DfReader.cpp`.

use std::collections::{HashMap, HashSet};
use std::ffi::{CStr, CString};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::os::raw::{c_char, c_int, c_void};
use std::path::Path;

use crate::kinds::{self, VarType, Vendor};
use crate::na::{self, make_tagged_na};
use crate::sys;

const TYPE_STRING: i32 = 0;
const TYPE_INT8: i32 = 1;
const TYPE_INT16: i32 = 2;
const TYPE_INT32: i32 = 3;
const TYPE_FLOAT: i32 = 4;
const TYPE_DOUBLE: i32 = 5;
const TYPE_STRING_REF: i32 = 6;

#[derive(Clone)]
pub enum Values {
    Double(Vec<f64>),
    String(Vec<Option<String>>),
}

struct LabelSet {
    names: Vec<String>,
    strings: Vec<String>,
    doubles: Vec<f64>,
}

impl LabelSet {
    fn new() -> Self {
        Self {
            names: Vec::new(),
            strings: Vec::new(),
            doubles: Vec::new(),
        }
    }

    fn add_string(&mut self, value: &str, label: String) -> Result<(), String> {
        if !self.doubles.is_empty() {
            return Err("Can't add string to integer/double labelset".into());
        }
        self.strings.push(value.to_string());
        self.names.push(label);
        Ok(())
    }

    fn add_double(&mut self, value: f64, label: String) -> Result<(), String> {
        if !self.strings.is_empty() {
            return Err("Can't add double to integer/string labelset".into());
        }
        self.doubles.push(value);
        self.names.push(label);
        Ok(())
    }
}

pub struct Column {
    pub name: String,
    pub values: Values,
    pub label: Option<String>,
    pub label_set: Option<String>,
    pub label_names: Vec<String>,
    pub label_doubles: Vec<f64>,
    pub label_strings: Vec<String>,
    pub var_type: VarType,
    pub class: Vec<String>,
    pub format: Option<String>,
    pub format_attr: Option<String>,
    pub display_width: Option<i32>,
    pub na_values_double: Vec<f64>,
    pub na_values_string: Vec<Option<String>>,
    pub na_range_double: Option<(f64, f64)>,
    pub na_range_string: Option<(String, String)>,
    pub units: Option<String>,
    pub tzone: Option<String>,
}

pub struct Table {
    pub columns: Vec<Column>,
    pub nrows: i64,
    pub label: Option<String>,
    pub notes: Vec<String>,
}

struct Reader {
    vendor: Vendor,
    nrows: i64,
    nrows_alloc: i64,
    ncols: usize,
    user_na: bool,
    columns: Vec<Column>,
    label_sets: HashMap<String, LabelSet>,
    notes: Vec<String>,
    file_label: Option<String>,
    skip: HashSet<String>,
    error: Option<String>,
}

struct Input {
    path: Option<CString>,
    file: Option<File>,
    bytes: Option<Vec<u8>>,
    pos: usize,
    encoding: Option<CString>,
    source: String,
}

fn text(ptr: *const c_char) -> Option<String> {
    if ptr.is_null() {
        return None;
    }
    Some(unsafe { CStr::from_ptr(ptr) }.to_string_lossy().into_owned())
}

fn type_code(value: sys::readstat_value_t) -> i32 {
    unsafe { sys::readstat_value_type(value) as i32 }
}

fn is_string(code: i32) -> bool {
    code == TYPE_STRING || code == TYPE_STRING_REF
}

fn is_number(code: i32) -> bool {
    matches!(code, TYPE_INT8 | TYPE_INT16 | TYPE_INT32 | TYPE_FLOAT | TYPE_DOUBLE)
}

fn haven_double(value: sys::readstat_value_t, variable: *mut sys::readstat_variable_t, user_na: bool) -> f64 {
    unsafe {
        if sys::readstat_value_is_tagged_missing(value) != 0 {
            let tag = sys::readstat_value_tag(value) as u8;
            return make_tagged_na(tag.to_ascii_lowercase());
        }
        if !user_na && sys::readstat_value_is_defined_missing(value, variable) != 0 {
            return na::na_real();
        }
        if sys::readstat_value_is_system_missing(value) != 0 {
            return na::na_real();
        }
        sys::readstat_double_value(value)
    }
}

impl Reader {
    fn new(vendor: Vendor, user_na: bool, skip: HashSet<String>) -> Self {
        Self {
            vendor,
            nrows: 0,
            nrows_alloc: 0,
            ncols: 0,
            user_na,
            columns: Vec::new(),
            label_sets: HashMap::new(),
            notes: Vec::new(),
            file_label: None,
            skip,
            error: None,
        }
    }

    fn set_info(&mut self, obs_count: i32, var_count: i32) {
        if obs_count < 0 {
            self.nrows_alloc = 100_000;
            self.nrows = 0;
        } else {
            self.nrows_alloc = obs_count as i64;
            self.nrows = obs_count as i64;
        }
        if var_count < 1 {
            return;
        }
        self.ncols = (var_count as usize).saturating_sub(self.skip.len());
        self.columns = (0..self.ncols)
            .map(|_| Column {
                name: String::new(),
                values: Values::Double(Vec::new()),
                label: None,
                label_set: None,
                label_names: Vec::new(),
                label_doubles: Vec::new(),
                label_strings: Vec::new(),
                var_type: VarType::Default,
                class: Vec::new(),
                format: None,
                format_attr: None,
                display_width: None,
                na_values_double: Vec::new(),
                na_values_string: Vec::new(),
                na_range_double: None,
                na_range_string: None,
                units: None,
                tzone: None,
            })
            .collect();
    }

    fn set_metadata(&mut self, label: *const c_char) {
        if let Some(text) = text(label) {
            if !text.is_empty() {
                self.file_label = Some(text);
            }
        }
    }

    fn set_note(&mut self, note: *const c_char) {
        if let Some(text) = text(note) {
            if !text.is_empty() {
                self.notes.push(text);
            }
        }
    }

    fn blank_double(&self) -> Vec<f64> {
        vec![na::na_real(); self.nrows_alloc.max(0) as usize]
    }

    fn blank_string(&self) -> Vec<Option<String>> {
        vec![None; self.nrows_alloc.max(0) as usize]
    }

    fn create_variable(&mut self, variable: *mut sys::readstat_variable_t, val_labels: *const c_char) -> i32 {
        let name = unsafe { text(sys::readstat_variable_get_name(variable)).unwrap_or_default() };
        if self.skip.contains(&name) {
            return 2;
        }
        let index = unsafe { sys::readstat_variable_get_index_after_skipping(variable) } as usize;
        if index >= self.columns.len() {
            self.error = Some(format!("column index {index} is outside the table"));
            return 1;
        }
        let code = unsafe { sys::readstat_variable_get_type(variable) as i32 };
        let values = if is_string(code) {
            Values::String(self.blank_string())
        } else {
            Values::Double(self.blank_double())
        };
        let var_label = unsafe { text(sys::readstat_variable_get_label(variable)) }
            .filter(|item| !item.is_empty());
        let format = unsafe { text(sys::readstat_variable_get_format(variable)) }
            .filter(|item| !item.is_empty());
        let var_type = kinds::num_type(self.vendor, format.as_deref());
        let mut class = Vec::new();
        let mut units = None;
        let mut tzone = None;
        match var_type {
            VarType::Date => class = vec!["Date".into()],
            VarType::Time => {
                class = vec!["hms".into(), "difftime".into()];
                units = Some("secs".into());
            }
            VarType::Datetime => {
                class = vec!["POSIXct".into(), "POSIXt".into()];
                tzone = Some("UTC".into());
            }
            VarType::Default => {}
        }
        let mut na_values_double = Vec::new();
        let mut na_values_string = Vec::new();
        let mut na_range_double = None;
        let mut na_range_string = None;
        let ranges = unsafe { sys::readstat_variable_get_missing_ranges_count(variable) };
        if self.user_na && ranges > 0 {
            if is_string(code) {
                class = vec![
                    "haven_labelled_spss".into(),
                    "haven_labelled".into(),
                    "vctrs_vctr".into(),
                    "character".into(),
                ];
                for i in 0..ranges {
                    let lo_value = unsafe { sys::readstat_variable_get_missing_range_lo(variable, i) };
                    let hi_value = unsafe { sys::readstat_variable_get_missing_range_hi(variable, i) };
                    let lo = unsafe { sys::readstat_string_value(lo_value) };
                    let hi = unsafe { sys::readstat_string_value(hi_value) };
                    if lo == hi {
                        na_values_string.push(text(lo));
                    } else {
                        na_range_string = Some((
                            text(lo).unwrap_or_default(),
                            text(hi).unwrap_or_default(),
                        ));
                    }
                }
            } else {
                class = vec![
                    "haven_labelled_spss".into(),
                    "haven_labelled".into(),
                    "vctrs_vctr".into(),
                    "double".into(),
                ];
                for i in 0..ranges {
                    let lo_value = unsafe { sys::readstat_variable_get_missing_range_lo(variable, i) };
                    let hi_value = unsafe { sys::readstat_variable_get_missing_range_hi(variable, i) };
                    let lo = unsafe { sys::readstat_double_value(lo_value) };
                    let hi = unsafe { sys::readstat_double_value(hi_value) };
                    if lo == hi {
                        na_values_double.push(lo);
                    } else {
                        na_range_double = Some((lo, hi));
                    }
                }
            }
        }
        let display_width = unsafe { sys::readstat_variable_get_display_width(variable) };
        let display_width = if self.vendor == Vendor::Spss && display_width != 8 {
            Some(display_width)
        } else {
            None
        };
        self.columns[index] = Column {
            name,
            values,
            label: var_label,
            label_set: text(val_labels).filter(|item| !item.is_empty()),
            label_names: Vec::new(),
            label_doubles: Vec::new(),
            label_strings: Vec::new(),
            var_type,
            class,
            format_attr: format.as_ref().map(|_| kinds::format_attribute(self.vendor).to_string()),
            format,
            display_width,
            na_values_double,
            na_values_string,
            na_range_double,
            na_range_string,
            units,
            tzone,
        };
        0
    }

    fn resize(&mut self, n: i64) {
        self.nrows_alloc = n;
        for column in &mut self.columns {
            match &mut column.values {
                Values::Double(values) => {
                    values.resize(n.max(0) as usize, na::na_real());
                }
                Values::String(values) => {
                    values.resize(n.max(0) as usize, None);
                }
            }
        }
    }

    fn set_value(&mut self, obs_index: i32, variable: *mut sys::readstat_variable_t, value: sys::readstat_value_t) {
        let index = unsafe { sys::readstat_variable_get_index_after_skipping(variable) } as usize;
        if index >= self.columns.len() {
            return;
        }
        let obs = obs_index as i64;
        if obs >= self.nrows_alloc {
            self.resize(self.nrows_alloc.max(1) * 2);
        }
        if obs >= self.nrows {
            self.nrows = obs + 1;
        }
        let kind = self.columns[index].var_type;
        let vendor = self.vendor;
        let user_na = self.user_na;
        let code = type_code(value);
        if is_string(code) {
            let missing = unsafe {
                sys::readstat_value_is_tagged_missing(value) != 0
                    || (!user_na && sys::readstat_value_is_defined_missing(value, variable) != 0)
                    || sys::readstat_value_is_system_missing(value) != 0
            };
            let stored = if missing {
                None
            } else {
                let ptr = unsafe { sys::readstat_string_value(value) };
                Some(text(ptr).unwrap_or_default())
            };
            if let Values::String(values) = &mut self.columns[index].values {
                values[obs as usize] = stored;
            }
        } else if is_number(code) {
            let raw = haven_double(value, variable, user_na);
            let adjusted = kinds::adjust_to_r(vendor, kind, raw);
            if let Values::Double(values) = &mut self.columns[index].values {
                values[obs as usize] = adjusted;
            }
        }
    }

    fn set_label(&mut self, key: *const c_char, value: sys::readstat_value_t, label: *const c_char) {
        let Some(key) = text(key) else {
            return;
        };
        let label = text(label).unwrap_or_default();
        let entry = self.label_sets.entry(key).or_insert_with(LabelSet::new);
        let code = type_code(value);
        let result = if code == TYPE_STRING {
            let ptr = unsafe { sys::readstat_string_value(value) };
            entry.add_string(&text(ptr).unwrap_or_default(), label)
        } else if is_number(code) {
            let number = haven_double(value, std::ptr::null_mut(), true);
            entry.add_double(number, label)
        } else {
            eprintln!("Unsupported label type: {code}");
            Ok(())
        };
        if let Err(message) = result {
            self.error = Some(message);
        }
    }

    fn limit_rows(&mut self, n: i64) {
        if self.nrows > n {
            self.nrows = n;
        }
    }

    fn finish(mut self) -> Table {
        if self.nrows != self.nrows_alloc {
            self.resize(self.nrows);
        }
        let sets = std::mem::take(&mut self.label_sets);
        for column in &mut self.columns {
            let Some(key) = column.label_set.clone() else {
                continue;
            };
            let Some(set) = sets.get(&key) else {
                column.label_set = None;
                continue;
            };
            column.label_names = set.names.clone();
            column.label_doubles = set.doubles.clone();
            column.label_strings = set.strings.clone();
            if column.class.is_empty() {
                let storage = if matches!(column.values, Values::String(_)) {
                    "character"
                } else {
                    "double"
                };
                column.class = vec!["haven_labelled".into(), "vctrs_vctr".into(), storage.into()];
            }
        }
        self.label_sets = sets;
        Table {
            columns: self.columns,
            nrows: self.nrows,
            label: self.file_label,
            notes: self.notes,
        }
    }
}

fn reader(ctx: *mut c_void) -> &'static mut Reader {
    unsafe { &mut *(ctx as *mut Reader) }
}

extern "C" fn on_metadata(metadata: *mut sys::readstat_metadata_t, ctx: *mut c_void) -> c_int {
    let rows = unsafe { sys::readstat_get_row_count(metadata) };
    let vars = unsafe { sys::readstat_get_var_count(metadata) };
    let label = unsafe { sys::readstat_get_file_label(metadata) };
    let reader = reader(ctx);
    reader.set_info(rows, vars);
    reader.set_metadata(label);
    0
}

extern "C" fn on_note(note_index: c_int, note: *const c_char, ctx: *mut c_void) -> c_int {
    let _ = note_index;
    reader(ctx).set_note(note);
    0
}

extern "C" fn on_variable(
    index: c_int,
    variable: *mut sys::readstat_variable_t,
    val_labels: *const c_char,
    ctx: *mut c_void,
) -> c_int {
    let _ = index;
    reader(ctx).create_variable(variable, val_labels)
}

extern "C" fn on_value(
    obs_index: c_int,
    variable: *mut sys::readstat_variable_t,
    value: sys::readstat_value_t,
    ctx: *mut c_void,
) -> c_int {
    reader(ctx).set_value(obs_index, variable, value);
    0
}

extern "C" fn on_value_label(
    val_labels: *const c_char,
    value: sys::readstat_value_t,
    label: *const c_char,
    ctx: *mut c_void,
) -> c_int {
    reader(ctx).set_label(val_labels, value, label);
    0
}

extern "C" fn on_error(message: *const c_char, _ctx: *mut c_void) {
    if let Some(text) = text(message) {
        println!("{text}");
    }
}

fn input(ctx: *mut c_void) -> &'static mut Input {
    unsafe { &mut *(ctx as *mut Input) }
}

extern "C" fn on_open(_path: *const c_char, ctx: *mut c_void) -> c_int {
    let input = input(ctx);
    if let Some(path) = &input.path {
        match File::open(path.to_string_lossy().as_ref()) {
            Ok(file) => {
                input.file = Some(file);
                0
            }
            Err(_) => -1,
        }
    } else {
        input.pos = 0;
        0
    }
}

extern "C" fn on_close(ctx: *mut c_void) -> c_int {
    let input = input(ctx);
    input.file = None;
    0
}

extern "C" fn on_seek(offset: i64, whence: sys::readstat_io_flags_t, ctx: *mut c_void) -> i64 {
    let input = input(ctx);
    let whence = whence as i32;
    if let Some(file) = input.file.as_mut() {
        let from = if whence == 0 {
            SeekFrom::Start(offset as u64)
        } else if whence == 1 {
            SeekFrom::Current(offset)
        } else {
            SeekFrom::End(offset)
        };
        return file.seek(from).map(|pos| pos as i64).unwrap_or(-1);
    }
    let Some(bytes) = input.bytes.as_ref() else {
        return -1;
    };
    let len = bytes.len() as i64;
    let next = if whence == 0 {
        offset
    } else if whence == 1 {
        input.pos as i64 + offset
    } else {
        len + offset
    };
    if next < 0 || next > len {
        return -1;
    }
    input.pos = next as usize;
    next
}

extern "C" fn on_read(buf: *mut c_void, nbyte: usize, ctx: *mut c_void) -> isize {
    let input = input(ctx);
    if let Some(file) = input.file.as_mut() {
        let slice = unsafe { std::slice::from_raw_parts_mut(buf as *mut u8, nbyte) };
        return match file.read(slice) {
            Ok(n) => n as isize,
            Err(_) => -1,
        };
    }
    let Some(bytes) = input.bytes.as_ref() else {
        return -1;
    };
    let available = bytes.len().saturating_sub(input.pos);
    let n = nbyte.min(available);
    unsafe {
        std::ptr::copy_nonoverlapping(bytes.as_ptr().add(input.pos), buf as *mut u8, n);
    }
    input.pos += n;
    n as isize
}

extern "C" fn on_update(
    _file_size: i64,
    _progress: sys::readstat_progress_handler,
    _user_ctx: *mut c_void,
    _io_ctx: *mut c_void,
) -> sys::readstat_error_t {
    0
}

fn parse_one(parser: *mut sys::readstat_parser_t, input: &mut Input, reader: &mut Reader, kind: &str) -> Result<(), String> {
    unsafe {
        sys::readstat_set_open_handler(parser, Some(on_open));
        sys::readstat_set_close_handler(parser, Some(on_close));
        sys::readstat_set_seek_handler(parser, Some(on_seek));
        sys::readstat_set_read_handler(parser, Some(on_read));
        sys::readstat_set_update_handler(parser, Some(on_update));
        sys::readstat_set_io_ctx(parser, input as *mut Input as *mut c_void);
        if let Some(encoding) = &input.encoding {
            sys::readstat_set_file_character_encoding(parser, encoding.as_ptr());
        }
        let empty = CString::new("").unwrap();
        let result = match kind {
            "sas" => sys::readstat_parse_sas7bdat(parser, empty.as_ptr(), reader as *mut Reader as *mut c_void),
            "catalog" => sys::readstat_parse_sas7bcat(parser, empty.as_ptr(), reader as *mut Reader as *mut c_void),
            "xpt" => sys::readstat_parse_xport(parser, empty.as_ptr(), reader as *mut Reader as *mut c_void),
            "dta" => sys::readstat_parse_dta(parser, empty.as_ptr(), reader as *mut Reader as *mut c_void),
            "sav" => sys::readstat_parse_sav(parser, empty.as_ptr(), reader as *mut Reader as *mut c_void),
            "por" => sys::readstat_parse_por(parser, empty.as_ptr(), reader as *mut Reader as *mut c_void),
            _ => 4,
        };
        if result != 0 {
            let message = text(sys::readstat_error_message(result)).unwrap_or_else(|| "parse error".into());
            return Err(format!("Failed to parse {}: {message}.", input.source));
        }
    }
    if let Some(message) = reader.error.clone() {
        return Err(message);
    }
    Ok(())
}

pub struct Request {
    pub kind: String,
    pub path: Option<String>,
    pub bytes: Option<Vec<u8>>,
    pub encoding: String,
    pub user_na: bool,
    pub skip: Vec<String>,
    pub n_max: i64,
    pub rows_skip: i64,
    pub catalog_path: Option<String>,
    pub catalog_bytes: Option<Vec<u8>>,
    pub catalog_encoding: String,
}

fn input_for(path: Option<&str>, bytes: Option<Vec<u8>>, encoding: &str, source: String) -> Result<Input, String> {
    let encoding = if encoding.is_empty() {
        None
    } else {
        Some(CString::new(encoding).map_err(|_| "encoding contains a nul")?)
    };
    if let Some(path) = path {
        Ok(Input {
            path: Some(CString::new(path).map_err(|_| "path contains a nul")?),
            file: None,
            bytes: None,
            pos: 0,
            encoding,
            source,
        })
    } else {
        Ok(Input {
            path: None,
            file: None,
            bytes,
            pos: 0,
            encoding,
            source,
        })
    }
}

pub fn read_table(request: Request) -> Result<Table, String> {
    let vendor = match request.kind.as_str() {
        "sav" | "por" => Vendor::Spss,
        "dta" => Vendor::Stata,
        "sas" | "xpt" => Vendor::Sas,
        other => return Err(format!("unknown file kind {other}")),
    };
    let mut reader = Reader::new(vendor, request.user_na, request.skip.into_iter().collect());
    let parser = unsafe { sys::readstat_parser_init() };
    if parser.is_null() {
        return Err("Failed to create the ReadStat parser.".into());
    }
    unsafe {
        sys::readstat_set_metadata_handler(parser, Some(on_metadata));
        sys::readstat_set_note_handler(parser, Some(on_note));
        sys::readstat_set_variable_handler(parser, Some(on_variable));
        sys::readstat_set_value_handler(parser, Some(on_value));
        sys::readstat_set_value_label_handler(parser, Some(on_value_label));
        sys::readstat_set_error_handler(parser, Some(on_error));
        let limit = if request.n_max == 0 { 1 } else { request.n_max };
        sys::readstat_set_row_limit(parser, limit);
        sys::readstat_set_row_offset(parser, request.rows_skip);
    }
    let result = (|| {
        if request.kind == "sas" && (request.catalog_path.is_some() || request.catalog_bytes.is_some()) {
            let source = request.catalog_path.clone().unwrap_or_else(|| "file".into());
            let mut catalog = input_for(
                request.catalog_path.as_deref(),
                request.catalog_bytes,
                &request.catalog_encoding,
                source,
            )?;
            parse_one(parser, &mut catalog, &mut reader, "catalog")?;
        }
        let source = request
            .path
            .clone()
            .unwrap_or_else(|| "file".into());
        if request.path.is_none() && request.bytes.is_none() {
            return Err("a path or a byte string is required".into());
        }
        if let Some(path) = request.path.as_deref() {
            if !Path::new(path).exists() && request.bytes.is_none() {
                // ReadStat reports the open failure itself.
            }
        }
        let mut input = input_for(request.path.as_deref(), request.bytes, &request.encoding, source)?;
        parse_one(parser, &mut input, &mut reader, &request.kind)?;
        if request.n_max >= 0 {
            reader.limit_rows(request.n_max);
        }
        Ok(reader.finish())
    })();
    unsafe { sys::readstat_parser_free(parser) };
    result
}
