//! String-to-index map from fastmap `src/fastmap.cpp`.
//!
//! The R object stores values in a backing list and fills free slots from the
//! end of a hole stack. This map only answers which slot a string occupies.
//! Key order is not the hash order.

use std::collections::HashMap;

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[derive(Clone, Default)]
struct Map {
    inner: HashMap<String, i32>,
}

impl Map {
    fn set(&mut self, key: &str, idx: i32) {
        self.inner.insert(key.to_string(), idx);
    }

    fn get(&self, key: &str) -> i32 {
        self.inner.get(key).copied().unwrap_or(-1)
    }

    fn has(&self, key: &str) -> bool {
        self.inner.contains_key(key)
    }

    fn remove(&mut self, key: &str) -> i32 {
        self.inner.remove(key).unwrap_or(-1)
    }

    fn keys_idxs(&self, sort: bool) -> Vec<(String, i32)> {
        let mut pairs: Vec<(String, i32)> = self
            .inner
            .iter()
            .map(|(key, idx)| (key.clone(), *idx))
            .collect();
        if sort {
            pairs.sort_unstable_by(|a, b| a.0.cmp(&b.0));
        }
        pairs
    }
}

#[cfg(feature = "python")]
#[pyclass]
struct IndexMap {
    map: Map,
}

#[cfg(feature = "python")]
#[pymethods]
impl IndexMap {
    #[new]
    fn new() -> Self {
        Self { map: Map::default() }
    }

    fn set(&mut self, key: &str, idx: i32) {
        self.map.set(key, idx);
    }

    fn get(&self, key: &str) -> i32 {
        self.map.get(key)
    }

    fn has(&self, key: &str) -> bool {
        self.map.has(key)
    }

    fn remove(&mut self, key: &str) -> i32 {
        self.map.remove(key)
    }

    /// `(key, index)` pairs. `sort` orders keys by Unicode code point.
    fn keys_idxs(&self, sort: bool) -> Vec<(String, i32)> {
        self.map.keys_idxs(sort)
    }

    fn copy(&self) -> Self {
        Self {
            map: self.map.clone(),
        }
    }
}

#[cfg(feature = "python")]
#[pymodule]
#[pyo3(name = "fastmap_kernel")]
fn fastmap_kernel(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<IndexMap>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::Map;

    #[test]
    fn missing_get_is_minus_one() {
        let mut map = Map::default();
        assert_eq!(map.get("a"), -1);
        assert!(!map.has("a"));
        map.set("a", 31);
        assert_eq!(map.get("a"), 31);
        assert!(map.has("a"));
        map.set("a", 4);
        assert_eq!(map.remove("a"), 4);
        assert_eq!(map.remove("a"), -1);
    }
}
