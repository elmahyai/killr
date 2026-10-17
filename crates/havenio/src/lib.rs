//! ReadStat readers and writers from haven 2.5.5.

mod kinds;
mod na;
mod reader;
mod writer;

#[allow(non_upper_case_globals, non_camel_case_types, non_snake_case, dead_code, improper_ctypes)]
mod sys {
    include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
}

use std::ffi::CStr;
use std::os::raw::c_char;

pub fn c_text(ptr: *const c_char) -> String {
    if ptr.is_null() {
        return String::new();
    }
    unsafe { CStr::from_ptr(ptr) }.to_string_lossy().into_owned()
}

#[cfg(feature = "python")]
mod python {
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyList};

    use crate::reader::{self, Column, Request, Values};
    use crate::writer::{self, Storage, WriteColumn, WriteOptions, WriteTable};

    fn py_err(message: String) -> PyErr {
        pyo3::exceptions::PyRuntimeError::new_err(message)
    }

    fn string_list(values: Option<&Bound<'_, PyAny>>) -> PyResult<Vec<String>> {
        let Some(values) = values else {
            return Ok(Vec::new());
        };
        if values.is_none() {
            return Ok(Vec::new());
        }
        let mut out = Vec::new();
        for item in values.try_iter()? {
            out.push(item?.extract::<String>()?);
        }
        Ok(out)
    }

    fn optional_string(value: Option<&Bound<'_, PyAny>>) -> PyResult<Option<String>> {
        let Some(value) = value else {
            return Ok(None);
        };
        if value.is_none() {
            Ok(None)
        } else {
            Ok(Some(value.extract()?))
        }
    }

    #[pyfunction]
    #[pyo3(signature = (kind, path=None, data=None, encoding=None, user_na=false, cols_skip=None, n_max=-1, rows_skip=0, catalog_path=None, catalog_data=None, catalog_encoding=None))]
    fn read_table(
        py: Python<'_>,
        kind: String,
        path: Option<String>,
        data: Option<Vec<u8>>,
        encoding: Option<String>,
        user_na: bool,
        cols_skip: Option<Vec<String>>,
        n_max: i64,
        rows_skip: i64,
        catalog_path: Option<String>,
        catalog_data: Option<Vec<u8>>,
        catalog_encoding: Option<String>,
    ) -> PyResult<Py<PyAny>> {
        let table = reader::read_table(Request {
            kind,
            path,
            bytes: data,
            encoding: encoding.unwrap_or_default(),
            user_na,
            skip: cols_skip.unwrap_or_default(),
            n_max,
            rows_skip,
            catalog_path,
            catalog_bytes: catalog_data,
            catalog_encoding: catalog_encoding.unwrap_or_default(),
        })
        .map_err(py_err)?;
        table_to_py(py, table)
    }

    fn table_to_py(py: Python<'_>, table: reader::Table) -> PyResult<Py<PyAny>> {
        let columns = PyList::empty(py);
        for column in table.columns {
            columns.append(column_to_py(py, column)?)?;
        }
        let out = PyDict::new(py);
        out.set_item("nrows", table.nrows)?;
        out.set_item("label", table.label)?;
        out.set_item("notes", table.notes)?;
        out.set_item("columns", columns)?;
        Ok(out.into_any().unbind())
    }

    fn column_to_py(py: Python<'_>, column: Column) -> PyResult<Py<PyAny>> {
        let dict = PyDict::new(py);
        dict.set_item("name", column.name)?;
        match column.values {
            Values::Double(values) => {
                dict.set_item("storage", "double")?;
                dict.set_item("values", values)?;
            }
            Values::String(values) => {
                dict.set_item("storage", "string")?;
                let items = PyList::empty(py);
                for value in values {
                    match value {
                        Some(text) => items.append(text)?,
                        None => items.append(py.None())?,
                    }
                }
                dict.set_item("values", items)?;
            }
        }
        dict.set_item("label", column.label)?;
        dict.set_item("class", column.class)?;
        dict.set_item("format", column.format)?;
        dict.set_item("format_attr", column.format_attr)?;
        dict.set_item("display_width", column.display_width)?;
        dict.set_item("units", column.units)?;
        dict.set_item("tzone", column.tzone)?;
        dict.set_item("label_names", column.label_names)?;
        if !column.label_doubles.is_empty() {
            dict.set_item("label_values", column.label_doubles)?;
            dict.set_item("label_storage", "double")?;
        } else if !column.label_strings.is_empty() {
            dict.set_item("label_values", column.label_strings)?;
            dict.set_item("label_storage", "string")?;
        }
        if !column.na_values_double.is_empty() {
            dict.set_item("na_values", column.na_values_double)?;
        }
        if !column.na_values_string.is_empty() {
            let items = PyList::empty(py);
            for value in column.na_values_string {
                match value {
                    Some(text) => items.append(text)?,
                    None => items.append(py.None())?,
                }
            }
            dict.set_item("na_values", items)?;
        }
        if let Some((lo, hi)) = column.na_range_double {
            dict.set_item("na_range", vec![lo, hi])?;
        }
        if let Some((lo, hi)) = column.na_range_string {
            dict.set_item("na_range", vec![lo, hi])?;
        }
        Ok(dict.into_any().unbind())
    }

    fn f64_list(value: &Bound<'_, PyAny>) -> PyResult<Vec<f64>> {
        if value.is_none() {
            return Ok(Vec::new());
        }
        let mut out = Vec::new();
        for item in value.try_iter()? {
            out.push(item?.extract::<f64>()?);
        }
        Ok(out)
    }

    fn i32_list(value: &Bound<'_, PyAny>) -> PyResult<Vec<i32>> {
        if value.is_none() {
            return Ok(Vec::new());
        }
        let mut out = Vec::new();
        for item in value.try_iter()? {
            let item = item?;
            if item.is_none() {
                out.push(i32::MIN);
            } else {
                out.push(item.extract::<i32>()?);
            }
        }
        Ok(out)
    }

    fn pair_f64(column: &Bound<'_, PyAny>, key: &str) -> PyResult<Option<(f64, f64)>> {
        let Ok(item) = column.get_item(key) else {
            return Ok(None);
        };
        if item.is_none() {
            return Ok(None);
        }
        let values = f64_list(&item)?;
        if values.len() == 2 {
            Ok(Some((values[0], values[1])))
        } else {
            Ok(None)
        }
    }

    fn pair_string(column: &Bound<'_, PyAny>, key: &str) -> PyResult<Option<(String, String)>> {
        let Ok(item) = column.get_item(key) else {
            return Ok(None);
        };
        if item.is_none() {
            return Ok(None);
        }
        let values = string_list(Some(&item))?;
        if values.len() == 2 {
            Ok(Some((values[0].clone(), values[1].clone())))
        } else {
            Ok(None)
        }
    }

    fn extract_column(column: &Bound<'_, PyAny>) -> PyResult<WriteColumn> {
        let storage_name: String = column.get_item("storage")?.extract()?;
        let values = column.get_item("values")?;
        let storage = match storage_name.as_str() {
            "double" => Storage::Double(f64_list(&values)?),
            "integer" => Storage::Integer(i32_list(&values)?),
            "logical" => Storage::Logical(i32_list(&values)?),
            "string" => {
                let mut out = Vec::new();
                for item in values.try_iter()? {
                    let item = item?;
                    if item.is_none() {
                        out.push(None);
                    } else {
                        out.push(Some(item.extract::<String>()?));
                    }
                }
                Storage::String(out)
            }
            other => return Err(py_err(format!("unsupported column storage {other}"))),
        };
        Ok(WriteColumn {
            name: column.get_item("name")?.extract()?,
            storage,
            label: optional_string(Some(&column.get_item("label")?))?,
            labels_double: f64_list(&column.get_item("labels_double").unwrap_or(column.py().None().into_bound(column.py())))?,
            labels_int: i32_list(&column.get_item("labels_int").unwrap_or(column.py().None().into_bound(column.py())))?,
            labels_string: string_list(column.get_item("labels_string").ok().as_ref())?,
            label_names: string_list(column.get_item("label_names").ok().as_ref())?,
            class: string_list(column.get_item("class").ok().as_ref())?,
            format_stata: optional_string(column.get_item("format_stata").ok().as_ref())?,
            format_spss: optional_string(column.get_item("format_spss").ok().as_ref())?,
            format_sas: optional_string(column.get_item("format_sas").ok().as_ref())?,
            display_width: column.get_item("display_width").ok().and_then(|item| item.extract().ok()).unwrap_or(0),
            width: column.get_item("width").ok().and_then(|item| item.extract().ok()).unwrap_or(0),
            na_values_double: f64_list(&column.get_item("na_values_double").unwrap_or(column.py().None().into_bound(column.py())))?,
            na_values_int: i32_list(&column.get_item("na_values_int").unwrap_or(column.py().None().into_bound(column.py())))?,
            na_values_string: string_list(column.get_item("na_values_string").ok().as_ref())?,
            na_range_double: pair_f64(column, "na_range_double")?,
            na_range_string: pair_string(column, "na_range_string")?,
            levels: string_list(column.get_item("levels").ok().as_ref())?,
            ordered: column.get_item("ordered").ok().and_then(|item| item.extract().ok()).unwrap_or(false),
            spss: column.get_item("spss").ok().and_then(|item| item.extract().ok()).unwrap_or(false),
            labelled: column.get_item("labelled").ok().and_then(|item| item.extract().ok()).unwrap_or(false),
        })
    }

    #[pyfunction]
    #[pyo3(signature = (kind, path, columns, label=None, version=0, strl_threshold=2045, compress=None, name=None))]
    fn write_table(
        kind: String,
        path: String,
        columns: Vec<Bound<'_, PyDict>>,
        label: Option<String>,
        version: i32,
        strl_threshold: i32,
        compress: Option<String>,
        name: Option<String>,
    ) -> PyResult<Vec<String>> {
        let mut extracted = Vec::new();
        for column in columns {
            extracted.push(extract_column(column.as_any())?);
        }
        let table = WriteTable {
            columns: extracted,
            label: label.clone(),
        };
        writer::write_table(
            &table,
            &WriteOptions {
                kind,
                path,
                version,
                label,
                strl_threshold,
                compress: compress.unwrap_or_else(|| "byte".into()),
                name,
            },
        )
        .map_err(py_err)
    }

    #[pymodule]
    fn havenio(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(read_table, m)?)?;
        m.add_function(wrap_pyfunction!(write_table, m)?)?;
        Ok(())
    }
}
