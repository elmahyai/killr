//! Sass to CSS through libsass, as the R package sass 0.4.10 calls it.
//!
//! `compile_data` in `sass/src/compile.c` fills the same 13 options that
//! `sass_options()` builds in R, then calls `sass_compile_data_context`.
//! This crate sets those options from Rust and calls the libsass C API
//! directly, so there is no R code and no C glue here.
//!
//! Source map output is off: `source_map_file`, `source_map_root`,
//! `source_map_embed`, `source_map_contents`, and `output_path` are empty or false,
//! as in R's default `sass_options()`.

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::ptr;

#[repr(C)]
pub struct SassDataContext {
    _private: [u8; 0],
}

#[repr(C)]
pub struct SassContext {
    _private: [u8; 0],
}

#[repr(C)]
pub struct SassOptions {
    _private: [u8; 0],
}

unsafe extern "C" {
    fn malloc(size: usize) -> *mut c_void;

    fn sass_make_data_context(source_string: *mut c_char) -> *mut SassDataContext;
    fn sass_data_context_get_context(ctx: *mut SassDataContext) -> *mut SassContext;
    fn sass_context_get_options(ctx: *mut SassContext) -> *mut SassOptions;
    fn sass_compile_data_context(ctx: *mut SassDataContext) -> c_int;
    fn sass_delete_data_context(ctx: *mut SassDataContext);
    fn sass_context_get_output_string(ctx: *mut SassContext) -> *const c_char;
    fn sass_context_get_error_message(ctx: *mut SassContext) -> *const c_char;

    fn sass_option_set_precision(options: *mut SassOptions, precision: c_int);
    fn sass_option_set_output_style(options: *mut SassOptions, style: c_int);
    fn sass_option_set_source_comments(options: *mut SassOptions, value: bool);
    fn sass_option_set_source_map_embed(options: *mut SassOptions, value: bool);
    fn sass_option_set_source_map_contents(options: *mut SassOptions, value: bool);
    fn sass_option_set_omit_source_map_url(options: *mut SassOptions, value: bool);
    fn sass_option_set_is_indented_syntax_src(options: *mut SassOptions, value: bool);
    fn sass_option_set_indent(options: *mut SassOptions, indent: *const c_char);
    fn sass_option_set_linefeed(options: *mut SassOptions, linefeed: *const c_char);
    fn sass_option_set_include_path(options: *mut SassOptions, include_path: *const c_char);
    fn sass_option_set_output_path(options: *mut SassOptions, output_path: *const c_char);
    fn sass_option_set_source_map_file(options: *mut SassOptions, source_map_file: *const c_char);
    fn sass_option_set_source_map_root(options: *mut SassOptions, source_map_root: *const c_char);
}

/// The R `sass_options()` names, in `sass_options()` order.
const OUTPUT_STYLES: &[(&str, c_int)] = &[
    ("nested", 0),
    ("expanded", 1),
    ("compact", 2),
    ("compressed", 3),
];

#[cfg(windows)]
const PATH_SEP: &str = ";";
#[cfg(not(windows))]
const PATH_SEP: &str = ":";

/// Compile a SCSS (or indented Sass) string to CSS. Returns the CSS, or the libsass error text.
pub fn compile(
    source: &str,
    output_style: &str,
    include_path: &[String],
    precision: i32,
    indented_syntax: bool,
    source_comments: bool,
    indent: &str,
    linefeed: &str,
) -> Result<String, String> {
    let style = OUTPUT_STYLES
        .iter()
        .find(|(name, _)| *name == output_style)
        .map(|(_, code)| *code)
        .ok_or_else(|| "output style not supported.".to_string())?;
    if !(0..=10).contains(&precision) {
        return Err("Invalid option. Integer value is out of range.".to_string());
    }
    let linefeed = match linefeed {
        "lf" => "\n",
        "cr" => "\r",
        "crlf" => "\r\n",
        "lfcr" => "\n\r",
        _ => return Err("invalid linefeed.".to_string()),
    };
    let include_path = include_path.join(PATH_SEP);

    let indent = CString::new(indent).map_err(|e| e.to_string())?;
    let linefeed = CString::new(linefeed).map_err(|e| e.to_string())?;
    let include_path = CString::new(include_path).map_err(|e| e.to_string())?;
    let empty = CString::new("").unwrap();
    let source = CString::new(source).map_err(|_| "source contains a NUL byte".to_string())?;

    // libsass frees the input with free() in sass_delete_data_context, so copy it with malloc.
    let bytes = source.as_bytes_with_nul();
    let input = unsafe { malloc(bytes.len()) } as *mut c_char;
    if input.is_null() {
        return Err("out of memory".to_string());
    }
    unsafe { ptr::copy_nonoverlapping(bytes.as_ptr(), input as *mut u8, bytes.len()) };

    unsafe {
        let data_ctx = sass_make_data_context(input);
        let ctx = sass_data_context_get_context(data_ctx);
        let opts = sass_context_get_options(ctx);

        sass_option_set_output_path(opts, empty.as_ptr());
        sass_option_set_output_style(opts, style);
        sass_option_set_is_indented_syntax_src(opts, indented_syntax);
        sass_option_set_source_comments(opts, source_comments);
        sass_option_set_omit_source_map_url(opts, false);
        sass_option_set_source_map_embed(opts, false);
        sass_option_set_source_map_contents(opts, false);
        sass_option_set_source_map_file(opts, empty.as_ptr());
        sass_option_set_source_map_root(opts, empty.as_ptr());
        sass_option_set_include_path(opts, include_path.as_ptr());
        sass_option_set_precision(opts, precision);
        sass_option_set_indent(opts, indent.as_ptr());
        sass_option_set_linefeed(opts, linefeed.as_ptr());

        let status = sass_compile_data_context(data_ctx);
        let result = if status != 0 {
            let msg = sass_context_get_error_message(ctx);
            let text = if msg.is_null() {
                "libsass compile failed".to_string()
            } else {
                CStr::from_ptr(msg).to_string_lossy().into_owned()
            };
            Err(text)
        } else {
            let out = sass_context_get_output_string(ctx);
            Ok(if out.is_null() {
                String::new()
            } else {
                CStr::from_ptr(out).to_string_lossy().into_owned()
            })
        };
        sass_delete_data_context(data_ctx);
        result
    }
}

#[cfg(feature = "python")]
mod python {
    use super::compile;
    use pyo3::exceptions::{PyRuntimeError, PyValueError};
    use pyo3::prelude::*;

    /// Compile SCSS to CSS with libsass.
    ///
    /// Arguments follow the R `sass_options()` names. Source maps are off.
    #[pyfunction]
    #[pyo3(signature = (
        source,
        *,
        output_style = "expanded",
        include_path = None,
        precision = 5,
        indented_syntax = false,
        source_comments = false,
        indent = "  ",
        linefeed = "lf",
    ))]
    fn compile_scss(
        py: Python<'_>,
        source: &str,
        output_style: &str,
        include_path: Option<Vec<String>>,
        precision: i32,
        indented_syntax: bool,
        source_comments: bool,
        indent: &str,
        linefeed: &str,
    ) -> PyResult<String> {
        let include_path = include_path.unwrap_or_default();
        if !matches!(output_style, "nested" | "expanded" | "compact" | "compressed") {
            return Err(PyValueError::new_err("output style not supported."));
        }
        let source = source.to_string();
        let style = output_style.to_string();
        let indent = indent.to_string();
        let linefeed = linefeed.to_string();
        py.detach(move || {
            compile(
                &source,
                &style,
                &include_path,
                precision,
                indented_syntax,
                source_comments,
                &indent,
                &linefeed,
            )
        })
        .map_err(PyRuntimeError::new_err)
    }

    #[pymodule]
    fn sass_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(compile_scss, m)?)?;
        Ok(())
    }
}
