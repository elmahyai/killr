//! Emulation of libstdc++ `std::unordered_map<grid_point, point_connect>`.
//!
//! The C++ marching code walks the map in its iteration order, and that order decides
//! which ring starts first and which id each line gets. Rust's HashMap has no fixed order,
//! so this module keeps the libstdc++ layout: one singly linked list of nodes, a bucket
//! array that points at the node before each bucket, the prime rehash policy with
//! max_load_factor 1.0, and the same insert, rehash, erase, and clear rules.
//! Bucket counts were measured with g++ 14.2 (libstdc++) on inserts of distinct keys.

use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};

use crate::grid::{GridPoint, PointConnect, NONE};

/// Fast mixing for the key index. The bucket layout below is what matches libstdc++,
/// so the index hash does not affect the output order.
#[derive(Default)]
struct MixHasher(u64);

impl Hasher for MixHasher {
    fn finish(&self) -> u64 {
        self.0
    }
    fn write(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.0 = mix(self.0 ^ b as u64);
        }
    }
    fn write_u64(&mut self, v: u64) {
        self.0 = mix(v);
    }
}

fn mix(mut z: u64) -> u64 {
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    z ^ (z >> 31)
}

const NIL: usize = usize::MAX;
/// Index of the `_M_before_begin` sentinel node.
const BEFORE: usize = 0;
/// libstdc++ `__fast_bkt` table for small bucket hints.
const FAST_BKT: [usize; 14] = [2, 2, 2, 3, 5, 5, 7, 7, 11, 11, 11, 11, 13, 13];
/// Bucket counts libstdc++ passes through as the element count grows.
const BUCKET_CHAIN: [usize; 19] = [
    13, 29, 59, 127, 257, 541, 1109, 2357, 5087, 10273, 20753, 42043, 85229, 172933, 351061, 712697,
    1447153, 2938679, 5967347,
];

fn hash_of(k: GridPoint) -> u64 {
    // std::hash<long long> is the identity, applied to (r << 30) ^ (c << 3) ^ type.
    k.packed()
}

fn next_prime_at_least(n: usize) -> usize {
    fn is_prime(k: usize) -> bool {
        if k < 2 {
            return false;
        }
        let mut d = 2;
        while d * d <= k {
            if k % d == 0 {
                return false;
            }
            d += 1;
        }
        true
    }
    let mut k = n.max(2);
    while !is_prime(k) {
        k += 1;
    }
    k
}

struct RehashPolicy {
    next_resize: usize,
}

impl RehashPolicy {
    fn next_bkt(&mut self, n: usize) -> usize {
        if n < FAST_BKT.len() {
            if n == 0 {
                return 1;
            }
            self.next_resize = FAST_BKT[n];
            return FAST_BKT[n];
        }
        let b = BUCKET_CHAIN
            .iter()
            .copied()
            .find(|&b| b >= n)
            .unwrap_or_else(|| next_prime_at_least(n));
        self.next_resize = b;
        b
    }

    /// Mirrors `_Prime_rehash_policy::_M_need_rehash`. Returns the new bucket count if a rehash is due.
    fn need_rehash(&mut self, n_bkt: usize, n_elt: usize, n_ins: usize) -> Option<usize> {
        if n_elt + n_ins > self.next_resize {
            let base = if self.next_resize != 0 {
                n_elt + n_ins
            } else {
                (n_elt + n_ins).max(11)
            };
            if base >= n_bkt {
                let target = (base + 1).max(n_bkt * 2);
                return Some(self.next_bkt(target));
            }
            self.next_resize = n_bkt;
        }
        None
    }
}

struct Node {
    key: GridPoint,
    val: PointConnect,
    next: usize,
}

pub struct OrderedMap {
    nodes: Vec<Node>,
    free: Vec<usize>,
    buckets: Vec<usize>,
    bucket_count: usize,
    policy: RehashPolicy,
    len: usize,
    index: HashMap<GridPoint, usize, BuildHasherDefault<MixHasher>>,
}

impl OrderedMap {
    pub fn new() -> Self {
        Self {
            nodes: vec![Node {
                key: NONE,
                val: PointConnect::default(),
                next: NIL,
            }],
            free: Vec::new(),
            buckets: vec![NIL],
            bucket_count: 1,
            policy: RehashPolicy { next_resize: 0 },
            len: 0,
            index: HashMap::default(),
        }
    }

    fn bucket_of(&self, k: GridPoint) -> usize {
        (hash_of(k) % self.bucket_count as u64) as usize
    }

    /// `clear()`: drops all nodes but keeps the bucket count and rehash state, as libstdc++ does.
    pub fn clear(&mut self) {
        self.nodes.truncate(1);
        self.nodes[BEFORE].next = NIL;
        self.free.clear();
        for b in self.buckets.iter_mut() {
            *b = NIL;
        }
        self.len = 0;
        self.index.clear();
    }

    pub fn contains(&self, k: GridPoint) -> bool {
        self.index.contains_key(&k)
    }

    /// Copy of the value stored under `k`. The key must exist.
    pub fn get(&self, k: GridPoint) -> PointConnect {
        self.nodes[self.index[&k]].val
    }

    /// `operator[]`: inserts a default value when the key is missing.
    pub fn at(&mut self, k: GridPoint) -> &mut PointConnect {
        let i = self.node_of(k);
        &mut self.nodes[i].val
    }

    /// `operator[] = v`.
    pub fn set(&mut self, k: GridPoint, v: PointConnect) {
        *self.at(k) = v;
    }

    pub fn key(&self, idx: usize) -> GridPoint {
        self.nodes[idx].key
    }

    pub fn val(&self, idx: usize) -> PointConnect {
        self.nodes[idx].val
    }

    /// Node handles in iteration order (the order a `for (auto it = m.begin(); ...)` loop visits).
    pub fn order(&self) -> Vec<usize> {
        let mut out = Vec::with_capacity(self.len);
        let mut p = self.nodes[BEFORE].next;
        while p != NIL {
            out.push(p);
            p = self.nodes[p].next;
        }
        out
    }

    fn node_of(&mut self, k: GridPoint) -> usize {
        if let Some(&i) = self.index.get(&k) {
            return i;
        }
        self.insert_unique(k, PointConnect::default())
    }

    fn insert_unique(&mut self, k: GridPoint, v: PointConnect) -> usize {
        if let Some(nb) = self.policy.need_rehash(self.bucket_count, self.len, 1) {
            self.rehash(nb);
        }
        let bkt = self.bucket_of(k);
        let idx = match self.free.pop() {
            Some(f) => {
                self.nodes[f] = Node {
                    key: k,
                    val: v,
                    next: NIL,
                };
                f
            }
            None => {
                self.nodes.push(Node {
                    key: k,
                    val: v,
                    next: NIL,
                });
                self.nodes.len() - 1
            }
        };
        self.insert_bucket_begin(bkt, idx);
        self.index.insert(k, idx);
        self.len += 1;
        idx
    }

    /// `_M_insert_bucket_begin`.
    fn insert_bucket_begin(&mut self, bkt: usize, n: usize) {
        if self.buckets[bkt] != NIL {
            let before = self.buckets[bkt];
            self.nodes[n].next = self.nodes[before].next;
            self.nodes[before].next = n;
        } else {
            self.nodes[n].next = self.nodes[BEFORE].next;
            self.nodes[BEFORE].next = n;
            let nx = self.nodes[n].next;
            if nx != NIL {
                let nb = self.bucket_of(self.nodes[nx].key);
                self.buckets[nb] = n;
            }
            self.buckets[bkt] = BEFORE;
        }
    }

    /// `_M_rehash_aux` for unique keys.
    fn rehash(&mut self, n: usize) {
        let mut new_buckets = vec![NIL; n];
        let mut p = self.nodes[BEFORE].next;
        self.nodes[BEFORE].next = NIL;
        let mut bbegin_bkt = 0usize;
        while p != NIL {
            let next = self.nodes[p].next;
            let bkt = (hash_of(self.nodes[p].key) % n as u64) as usize;
            if new_buckets[bkt] == NIL {
                self.nodes[p].next = self.nodes[BEFORE].next;
                self.nodes[BEFORE].next = p;
                new_buckets[bkt] = BEFORE;
                if self.nodes[p].next != NIL {
                    new_buckets[bbegin_bkt] = p;
                }
                bbegin_bkt = bkt;
            } else {
                let before = new_buckets[bkt];
                self.nodes[p].next = self.nodes[before].next;
                self.nodes[before].next = p;
            }
            p = next;
        }
        self.buckets = new_buckets;
        self.bucket_count = n;
    }

    /// `erase(key)`.
    pub fn erase(&mut self, k: GridPoint) {
        let n = match self.index.get(&k) {
            Some(&n) => n,
            None => return,
        };
        let bkt = self.bucket_of(k);
        let prev = self
            .find_before(bkt, k)
            .expect("key is present in its bucket");
        self.erase_after(bkt, prev, n);
        self.index.remove(&k);
        self.len -= 1;
        self.free.push(n);
    }

    /// `_M_find_before_node`.
    fn find_before(&self, bkt: usize, k: GridPoint) -> Option<usize> {
        let mut prev = self.buckets[bkt];
        if prev == NIL {
            return None;
        }
        loop {
            let p = self.nodes[prev].next;
            if p == NIL {
                return None;
            }
            if self.nodes[p].key == k {
                return Some(prev);
            }
            let nx = self.nodes[p].next;
            if nx == NIL || self.bucket_of(self.nodes[nx].key) != bkt {
                return None;
            }
            prev = p;
        }
    }

    /// `_M_erase` and `_M_remove_bucket_begin`.
    fn erase_after(&mut self, bkt: usize, prev: usize, n: usize) {
        let next = self.nodes[n].next;
        if prev == self.buckets[bkt] {
            let next_bkt = if next != NIL {
                self.bucket_of(self.nodes[next].key)
            } else {
                0
            };
            if next == NIL || next_bkt != bkt {
                if next != NIL {
                    self.buckets[next_bkt] = self.buckets[bkt];
                }
                if self.buckets[bkt] == BEFORE {
                    self.nodes[BEFORE].next = next;
                }
                self.buckets[bkt] = NIL;
            }
        } else if next != NIL {
            let next_bkt = self.bucket_of(self.nodes[next].key);
            if next_bkt != bkt {
                self.buckets[next_bkt] = prev;
            }
        }
        self.nodes[prev].next = next;
    }
}
