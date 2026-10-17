//! Zone names and the database version from the text time zone files.
//!
//! This is the `USE_OS_TZDB=0` path in tzdb `src/tz.cpp`: `init_tzdb` reads a
//! fixed list of source files, and `get_version` reads the `version` file.
//! `tzdb_names` then sorts the zone names and the link names together.

use std::fs;
use std::path::Path;

const SOURCE_FILES: [&str; 12] = [
    "africa",
    "antarctica",
    "asia",
    "australasia",
    "backward",
    "etcetera",
    "europe",
    "pacificnew",
    "northamerica",
    "southamerica",
    "systemv",
    "leapseconds",
];

fn is_cxx_space(ch: char) -> bool {
    matches!(ch, ' ' | '\t' | '\n' | '\r' | '\u{000b}' | '\u{000c}')
}

fn tokens(line: &str) -> Vec<&str> {
    line.split(is_cxx_space).filter(|part| !part.is_empty()).collect()
}

/// `is_prefix_of`: the shorter string is a prefix of the longer one.
fn is_prefix_of(key: &str, value: &str) -> bool {
    let size = key.len().min(value.len());
    key.as_bytes()[..size] == value.as_bytes()[..size]
}

fn ascii_lower(text: &str) -> String {
    text.chars()
        .map(|ch| {
            if ch.is_ascii_uppercase() {
                ch.to_ascii_lowercase()
            } else {
                ch
            }
        })
        .collect()
}

fn first_token_of_file(path: &Path) -> Option<String> {
    let text = fs::read_to_string(path).ok()?;
    tokens(&text).first().map(|token| (*token).to_string())
}

/// `get_version`. `install` is the database directory, without a trailing slash.
pub fn read_version(install: &str) -> Result<String, String> {
    let install_path = Path::new(install);
    if !install_path.exists() {
        return Err(format!("Timezone database not found at \"{install}\""));
    }
    let version_path = install_path.join("version");
    if version_path.exists() {
        if let Some(version) = first_token_of_file(&version_path) {
            return Ok(version);
        }
    }
    let news_path = install_path.join("NEWS");
    if news_path.exists() {
        if let Ok(text) = fs::read_to_string(&news_path) {
            let words = tokens(&text);
            for (index, word) in words.iter().enumerate() {
                if *word == "Release" {
                    return Ok(words.get(index + 1).unwrap_or(&"Release").to_string());
                }
            }
        }
    }
    Err(format!(
        "Unable to get Timezone database version from {install}/"
    ))
}

/// Zone names and link names from `init_tzdb`, sorted as `tzdb_names` sorts them.
pub fn parse_zone_names(install: &str) -> Result<Vec<String>, String> {
    read_version(install)?;
    let install_path = Path::new(install);
    let mut names = Vec::new();
    for filename in SOURCE_FILES {
        let file_path = install_path.join(filename);
        if !file_path.exists() {
            continue;
        }
        let text = fs::read_to_string(&file_path).map_err(|error| {
            format!(
                "Unable to read time zone file {}: {error}",
                file_path.display()
            )
        })?;
        for line in text.lines() {
            if line.is_empty() || line.as_bytes()[0] == b'#' {
                continue;
            }
            let parts = tokens(line);
            let word = parts.first().map(|token| ascii_lower(token)).unwrap_or_default();
            if is_prefix_of(&word, "rule") || is_prefix_of(&word, "leap") {
                continue;
            }
            if is_prefix_of(&word, "link") {
                let name = parts.get(2).ok_or_else(|| {
                    format!("Unable to parse time zone link in {filename}")
                })?;
                names.push((*name).to_string());
                continue;
            }
            if is_prefix_of(&word, "zone") {
                let name = parts.get(1).ok_or_else(|| {
                    format!("Unable to parse time zone in {filename}")
                })?;
                names.push((*name).to_string());
            }
        }
    }
    names.sort();
    Ok(names)
}

#[cfg(feature = "python")]
mod python {
    use super::{parse_zone_names, read_version};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use std::sync::Mutex;

    struct Cached {
        install: String,
        names: Vec<String>,
        version: String,
    }

    static CACHE: Mutex<Option<Cached>> = Mutex::new(None);

    #[pyfunction]
    fn zone_names(path: &str) -> PyResult<Vec<String>> {
        let mut cache = CACHE
            .lock()
            .map_err(|_| PyValueError::new_err("time zone database cache is locked"))?;
        if let Some(hit) = cache.as_ref() {
            if hit.install == path {
                return Ok(hit.names.clone());
            }
        }
        let names = parse_zone_names(path).map_err(PyValueError::new_err)?;
        let version = read_version(path).map_err(PyValueError::new_err)?;
        *cache = Some(Cached {
            install: path.to_string(),
            names: names.clone(),
            version,
        });
        Ok(names)
    }

    #[pyfunction]
    fn database_version(path: &str) -> PyResult<String> {
        let mut cache = CACHE
            .lock()
            .map_err(|_| PyValueError::new_err("time zone database cache is locked"))?;
        if let Some(hit) = cache.as_ref() {
            if hit.install == path {
                return Ok(hit.version.clone());
            }
        }
        let version = read_version(path).map_err(PyValueError::new_err)?;
        let names = parse_zone_names(path).map_err(PyValueError::new_err)?;
        *cache = Some(Cached {
            install: path.to_string(),
            names,
            version: version.clone(),
        });
        Ok(version)
    }

    #[pymodule]
    fn tzdb_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(zone_names, m)?)?;
        m.add_function(wrap_pyfunction!(database_version, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_zone_names, read_version};
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn scratch() -> std::path::PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("tzdb-kernel-{nanos}"));
        fs::create_dir_all(&path).unwrap();
        path
    }

    #[test]
    fn names_and_version_follow_the_text_files() {
        let dir = scratch();
        fs::write(dir.join("version"), "2025a\n").unwrap();
        fs::write(
            dir.join("africa"),
            "# comment\nZone\tAfrica/Abidjan\t0\t-\tGMT\nLink\tAfrica/Abidjan\tAfrica/Timbuktu\n",
        )
        .unwrap();
        fs::write(dir.join("etcetera"), "Zone\tEtc/UTC\t0\t-\tUTC\n").unwrap();
        let install = dir.to_str().unwrap();
        assert_eq!(read_version(install).unwrap(), "2025a");
        assert_eq!(
            parse_zone_names(install).unwrap(),
            vec![
                "Africa/Abidjan".to_string(),
                "Africa/Timbuktu".to_string(),
                "Etc/UTC".to_string(),
            ]
        );
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn news_release_is_the_fallback_version() {
        let dir = scratch();
        fs::write(dir.join("NEWS"), "Release 9999a\n").unwrap();
        fs::write(dir.join("africa"), "Zone\tA/B\t0\t-\tX\n").unwrap();
        let install = dir.to_str().unwrap();
        assert_eq!(read_version(install).unwrap(), "9999a");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn missing_directory_names_the_install_path() {
        let message = read_version("/no/such/tzdb-install").unwrap_err();
        assert_eq!(
            message,
            "Timezone database not found at \"/no/such/tzdb-install\""
        );
    }
}
