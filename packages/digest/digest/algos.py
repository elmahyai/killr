"""Hash algorithms used by digest.

md5, sha1, sha256, sha512, and crc32 come from the standard library.
The others follow the public specifications those names refer to, checked
against digest 0.6.39.
"""

from __future__ import annotations

import hashlib
import struct
import zlib

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF

P32_1 = 0x9E3779B1
P32_2 = 0x85EBCA77
P32_3 = 0xC2B2AE3D
P32_4 = 0x27D4EB2F
P32_5 = 0x165667B1

P64_1 = 0x9E3779B185EBCA87
P64_2 = 0xC2B2AE3D27D4EB4F
P64_3 = 0x165667B19E3779F9
P64_4 = 0x85EBCA77C2B2AE63
P64_5 = 0x27D4EB2F165667C5

PRIME_MX1 = 0x165667919E3779F9
PRIME_MX2 = 0x9FB21C651E98DF25

XXH3_SECRET = bytes((
    0xB8, 0xFE, 0x6C, 0x39, 0x23, 0xA4, 0x4B, 0xBE, 0x7C, 0x01, 0x81, 0x2C, 0xF7, 0x21, 0xAD, 0x1C,
    0xDE, 0xD4, 0x6D, 0xE9, 0x83, 0x90, 0x97, 0xDB, 0x72, 0x40, 0xA4, 0xA4, 0xB7, 0xB3, 0x67, 0x1F,
    0xCB, 0x79, 0xE6, 0x4E, 0xCC, 0xC0, 0xE5, 0x78, 0x82, 0x5A, 0xD0, 0x7D, 0xCC, 0xFF, 0x72, 0x21,
    0xB8, 0x08, 0x46, 0x74, 0xF7, 0x43, 0x24, 0x8E, 0xE0, 0x35, 0x90, 0xE6, 0x81, 0x3A, 0x26, 0x4C,
    0x3C, 0x28, 0x52, 0xBB, 0x91, 0xC3, 0x00, 0xCB, 0x88, 0xD0, 0x65, 0x8B, 0x1B, 0x53, 0x2E, 0xA3,
    0x71, 0x64, 0x48, 0x97, 0xA2, 0x0D, 0xF9, 0x4E, 0x38, 0x19, 0xEF, 0x46, 0xA9, 0xDE, 0xAC, 0xD8,
    0xA8, 0xFA, 0x76, 0x3F, 0xE3, 0x9C, 0x34, 0x3F, 0xF9, 0xDC, 0xBB, 0xC7, 0xC7, 0x0B, 0x4F, 0x1D,
    0x8A, 0x51, 0xE0, 0x4B, 0xCD, 0xB4, 0x59, 0x31, 0xC8, 0x9F, 0x7E, 0xC9, 0xD9, 0x78, 0x73, 0x64,
    0xEA, 0xC5, 0xAC, 0x83, 0x34, 0xD3, 0xEB, 0xC3, 0xC5, 0x81, 0xA0, 0xFF, 0xFA, 0x13, 0x63, 0xEB,
    0x17, 0x0D, 0xDD, 0x51, 0xB7, 0xF0, 0xDA, 0x49, 0xD3, 0x16, 0x55, 0x26, 0x29, 0xD4, 0x68, 0x9E,
    0x2B, 0x16, 0xBE, 0x58, 0x7D, 0x47, 0xA1, 0xFC, 0x8F, 0xF8, 0xB8, 0xD1, 0x7A, 0xD0, 0x31, 0xCE,
    0x45, 0xCB, 0x3A, 0x8F, 0x95, 0x16, 0x04, 0x28, 0xAF, 0xD7, 0xFB, 0xCA, 0xBB, 0x4B, 0x40, 0x7E,
))


def _u32(value: int) -> int:
    return value & MASK32


def _u64(value: int) -> int:
    return value & MASK64


def _rotl32(value: int, count: int) -> int:
    value &= MASK32
    return _u32((value << count) | (value >> (32 - count)))


def _rotl64(value: int, count: int) -> int:
    value &= MASK64
    return _u64((value << count) | (value >> (64 - count)))


def _read32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little")


def _read64(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 8], "little")


def _swap32(value: int) -> int:
    return int.from_bytes(_u32(value).to_bytes(4, "little"), "big")


def _swap64(value: int) -> int:
    return int.from_bytes(_u64(value).to_bytes(8, "little"), "big")


def md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


def sha1(data: bytes) -> bytes:
    return hashlib.sha1(data).digest()


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & MASK32


def _crc32c_table() -> list[int]:
    table = []
    for index in range(256):
        crc = index
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x82F63B78
            else:
                crc >>= 1
        table.append(crc)
    return table


_CRC32C = _crc32c_table()


def crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc = _CRC32C[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


def murmur32(data: bytes, seed: int = 0) -> int:
    """MurmurHash3 x86 32, the progressive hash digest calls PMurHash32."""
    c1 = 0xCC9E2D51
    c2 = 0x1B873593
    length = len(data)
    h = _u32(seed)
    blocks = length // 4
    for index in range(blocks):
        k = _read32(data, index * 4)
        k = _u32(k * c1)
        k = _rotl32(k, 15)
        k = _u32(k * c2)
        h ^= k
        h = _rotl32(h, 13)
        h = _u32(h * 5 + 0xE6546B64)
    tail = data[blocks * 4 :]
    k = 0
    if len(tail) >= 3:
        k ^= tail[2] << 16
    if len(tail) >= 2:
        k ^= tail[1] << 8
    if tail:
        k ^= tail[0]
        k = _u32(k * c1)
        k = _rotl32(k, 15)
        k = _u32(k * c2)
        h ^= k
    h ^= length
    h ^= h >> 16
    h = _u32(h * 0x85EBCA6B)
    h ^= h >> 13
    h = _u32(h * 0xC2B2AE35)
    h ^= h >> 16
    return h


def xxh32(data: bytes, seed: int = 0) -> int:
    seed = _u32(seed)
    n = len(data)
    offset = 0
    if n >= 16:
        v1 = _u32(seed + P32_1 + P32_2)
        v2 = _u32(seed + P32_2)
        v3 = seed
        v4 = _u32(seed - P32_1)
        while offset + 16 <= n:
            v1 = _xxh32_round(v1, _read32(data, offset))
            v2 = _xxh32_round(v2, _read32(data, offset + 4))
            v3 = _xxh32_round(v3, _read32(data, offset + 8))
            v4 = _xxh32_round(v4, _read32(data, offset + 12))
            offset += 16
        h = _u32(_rotl32(v1, 1) + _rotl32(v2, 7) + _rotl32(v3, 12) + _rotl32(v4, 18))
    else:
        h = _u32(seed + P32_5)
    h = _u32(h + n)
    while offset + 4 <= n:
        h = _u32(h + _read32(data, offset) * P32_3)
        h = _u32(_rotl32(h, 17) * P32_4)
        offset += 4
    while offset < n:
        h = _u32(h + data[offset] * P32_5)
        h = _u32(_rotl32(h, 11) * P32_1)
        offset += 1
    h ^= h >> 15
    h = _u32(h * P32_2)
    h ^= h >> 13
    h = _u32(h * P32_3)
    h ^= h >> 16
    return h


def _xxh32_round(acc: int, value: int) -> int:
    acc = _u32(acc + value * P32_2)
    acc = _rotl32(acc, 13)
    return _u32(acc * P32_1)


def xxh64(data: bytes, seed: int = 0) -> int:
    seed = _u64(seed)
    n = len(data)
    offset = 0
    if n >= 32:
        v1 = _u64(seed + P64_1 + P64_2)
        v2 = _u64(seed + P64_2)
        v3 = seed
        v4 = _u64(seed - P64_1)
        while offset + 32 <= n:
            v1 = _xxh64_round(v1, _read64(data, offset))
            v2 = _xxh64_round(v2, _read64(data, offset + 8))
            v3 = _xxh64_round(v3, _read64(data, offset + 16))
            v4 = _xxh64_round(v4, _read64(data, offset + 24))
            offset += 32
        h = _u64(_rotl64(v1, 1) + _rotl64(v2, 7) + _rotl64(v3, 12) + _rotl64(v4, 18))
        h = _xxh64_merge(h, v1)
        h = _xxh64_merge(h, v2)
        h = _xxh64_merge(h, v3)
        h = _xxh64_merge(h, v4)
    else:
        h = _u64(seed + P64_5)
    h = _u64(h + n)
    while offset + 8 <= n:
        k1 = _xxh64_round(0, _read64(data, offset))
        h ^= k1
        h = _u64(_rotl64(h, 27) * P64_1 + P64_4)
        offset += 8
    if offset + 4 <= n:
        h ^= _u64(_read32(data, offset) * P64_1)
        h = _u64(_rotl64(h, 23) * P64_2 + P64_3)
        offset += 4
    while offset < n:
        h ^= _u64(data[offset] * P64_5)
        h = _u64(_rotl64(h, 11) * P64_1)
        offset += 1
    h ^= h >> 33
    h = _u64(h * P64_2)
    h ^= h >> 29
    h = _u64(h * P64_3)
    h ^= h >> 32
    return h


def _xxh64_round(acc: int, value: int) -> int:
    acc = _u64(acc + value * P64_2)
    acc = _rotl64(acc, 31)
    return _u64(acc * P64_1)


def _xxh64_merge(acc: int, value: int) -> int:
    acc ^= _xxh64_round(0, value)
    return _u64(acc * P64_1 + P64_4)


def _xxh3_avalanche(h: int) -> int:
    h = _u64(h)
    h ^= h >> 37
    h = _u64(h * PRIME_MX1)
    h ^= h >> 32
    return h


def _xxh64_avalanche(h: int) -> int:
    h = _u64(h)
    h ^= h >> 33
    h = _u64(h * P64_2)
    h ^= h >> 29
    h = _u64(h * P64_3)
    h ^= h >> 32
    return h


def _xxh3_rrmxmx(h: int, length: int) -> int:
    h = _u64(h)
    h ^= _rotl64(h, 49) ^ _rotl64(h, 24)
    h = _u64(h * PRIME_MX2)
    h ^= _u64((h >> 35) + length)
    h = _u64(h * PRIME_MX2)
    h ^= h >> 28
    return h


def _mul128_fold64(lhs: int, rhs: int) -> int:
    product = _u64(lhs) * _u64(rhs)
    return _u64(product) ^ _u64(product >> 64)


def _mix16(data: bytes, offset: int, secret: bytes, secret_off: int, seed: int) -> int:
    lo = _read64(data, offset) ^ _u64(_read64(secret, secret_off) + seed)
    hi = _read64(data, offset + 8) ^ _u64(_read64(secret, secret_off + 8) - seed)
    return _mul128_fold64(lo, hi)


def xxh3_64(data: bytes, seed: int = 0) -> int:
    seed = _u64(seed)
    secret = _xxh3_secret(seed) if len(data) > 240 and seed else XXH3_SECRET
    # Lengths through 240 mix the seed into the short path and keep the default secret.
    short_secret = XXH3_SECRET
    n = len(data)
    if n <= 16:
        return _xxh3_0to16_64(data, short_secret, seed)
    if n <= 128:
        return _xxh3_17to128_64(data, short_secret, seed)
    if n <= 240:
        return _xxh3_129to240_64(data, short_secret, seed)
    return _xxh3_long_64(data, secret)


def _xxh3_secret(seed: int) -> bytes:
    if seed == 0:
        return XXH3_SECRET
    out = bytearray(192)
    for index in range(12):
        lo = _u64(_read64(XXH3_SECRET, 16 * index) + seed)
        hi = _u64(_read64(XXH3_SECRET, 16 * index + 8) - seed)
        out[16 * index : 16 * index + 8] = lo.to_bytes(8, "little")
        out[16 * index + 8 : 16 * index + 16] = hi.to_bytes(8, "little")
    return bytes(out)


def _xxh3_0to16_64(data: bytes, secret: bytes, seed: int) -> int:
    n = len(data)
    if n > 8:
        bit1 = _u64((_read64(secret, 24) ^ _read64(secret, 32)) + seed)
        bit2 = _u64((_read64(secret, 40) ^ _read64(secret, 48)) - seed)
        lo = _read64(data, 0) ^ bit1
        hi = _read64(data, n - 8) ^ bit2
        acc = _u64(n + _swap64(lo) + hi + _mul128_fold64(lo, hi))
        return _xxh3_avalanche(acc)
    if n >= 4:
        seeded = _u64(seed ^ (_swap32(_u32(seed)) << 32))
        input1 = _read32(data, 0)
        input2 = _read32(data, n - 4)
        bit = _u64((_read64(secret, 8) ^ _read64(secret, 16)) - seeded)
        keyed = _u64((input2 + (input1 << 32)) ^ bit)
        return _xxh3_rrmxmx(keyed, n)
    if n:
        c1 = data[0]
        c2 = data[n >> 1]
        c3 = data[n - 1]
        combined = _u32((c1 << 16) | (c2 << 24) | c3 | (n << 8))
        bit = _u64((_read32(secret, 0) ^ _read32(secret, 4)) + seed)
        return _xxh64_avalanche(combined ^ bit)
    return _xxh64_avalanche(seed ^ (_read64(secret, 56) ^ _read64(secret, 64)))


def _xxh3_17to128_64(data: bytes, secret: bytes, seed: int) -> int:
    n = len(data)
    acc = _u64(n * P64_1)
    if n > 32:
        if n > 64:
            if n > 96:
                acc = _u64(acc + _mix16(data, 48, secret, 96, seed))
                acc = _u64(acc + _mix16(data, n - 64, secret, 112, seed))
            acc = _u64(acc + _mix16(data, 32, secret, 64, seed))
            acc = _u64(acc + _mix16(data, n - 48, secret, 80, seed))
        acc = _u64(acc + _mix16(data, 16, secret, 32, seed))
        acc = _u64(acc + _mix16(data, n - 32, secret, 48, seed))
    acc = _u64(acc + _mix16(data, 0, secret, 0, seed))
    acc = _u64(acc + _mix16(data, n - 16, secret, 16, seed))
    return _xxh3_avalanche(acc)


def _xxh3_129to240_64(data: bytes, secret: bytes, seed: int) -> int:
    n = len(data)
    acc = _u64(n * P64_1)
    rounds = n // 16
    for index in range(8):
        acc = _u64(acc + _mix16(data, 16 * index, secret, 16 * index, seed))
    acc_end = _mix16(data, n - 16, secret, 136 - 17, seed)
    acc = _xxh3_avalanche(acc)
    for index in range(8, rounds):
        acc = _u64(acc + _mix16(data, 16 * index, secret, 16 * (index - 8) + 3, seed))
    return _xxh3_avalanche(_u64(acc + acc_end))


def _xxh3_long_64(data: bytes, secret: bytes) -> int:
    acc = [
        P32_3, P64_1, P64_2, P64_3,
        P64_4, P32_2, P64_5, P32_1,
    ]
    _xxh3_long_loop(acc, data, secret)
    return _xxh3_merge_accs(acc, secret, 11, _u64(len(data) * P64_1))


def _xxh3_long_loop(acc: list[int], data: bytes, secret: bytes) -> None:
    stripe = 64
    secret_size = len(secret)
    stripes_per_block = (secret_size - stripe) // 8
    block_len = stripe * stripes_per_block
    n = len(data)
    nb_blocks = (n - 1) // block_len
    for block in range(nb_blocks):
        _xxh3_accumulate(acc, data, block * block_len, secret, stripes_per_block)
        _xxh3_scramble(acc, secret, secret_size - stripe)
    nb_stripes = ((n - 1) - block_len * nb_blocks) // stripe
    _xxh3_accumulate(acc, data, nb_blocks * block_len, secret, nb_stripes)
    _xxh3_accumulate_512(acc, data, n - stripe, secret, secret_size - stripe - 7)


def _xxh3_accumulate(acc, data, offset, secret, stripes: int) -> None:
    for stripe in range(stripes):
        _xxh3_accumulate_512(acc, data, offset + stripe * 64, secret, stripe * 8)


def _xxh3_accumulate_512(acc, data, offset, secret, secret_off: int) -> None:
    for lane in range(8):
        data_val = _read64(data, offset + lane * 8)
        data_key = data_val ^ _read64(secret, secret_off + lane * 8)
        acc[lane ^ 1] = _u64(acc[lane ^ 1] + data_val)
        acc[lane] = _u64(_u64(_u32(data_key) * (data_key >> 32)) + acc[lane])


def _xxh3_scramble(acc, secret, secret_off: int) -> None:
    for lane in range(8):
        key = _read64(secret, secret_off + lane * 8)
        value = acc[lane]
        value ^= value >> 47
        value ^= key
        acc[lane] = _u64(value * P32_1)


def _xxh3_merge_accs(acc, secret, secret_off: int, start: int) -> int:
    result = start
    for index in range(4):
        result = _u64(result + _mul128_fold64(
            acc[2 * index] ^ _read64(secret, secret_off + 16 * index),
            acc[2 * index + 1] ^ _read64(secret, secret_off + 16 * index + 8),
        ))
    return _xxh3_avalanche(result)


def _mix32(low: int, high: int, data: bytes, off1: int, off2: int, secret: bytes, secret_off: int, seed: int):
    low = _u64(low + _mix16(data, off1, secret, secret_off, seed))
    low ^= _u64(_read64(data, off2) + _read64(data, off2 + 8))
    high = _u64(high + _mix16(data, off2, secret, secret_off + 16, seed))
    high ^= _u64(_read64(data, off1) + _read64(data, off1 + 8))
    return low, high


def _xxh3_finish_128(low: int, high: int, length: int, seed: int) -> tuple[int, int]:
    out_low = _u64(low + high)
    out_high = _u64(low * P64_1 + high * P64_4 + _u64(length - seed) * P64_2)
    return _u64(0 - _xxh3_avalanche(out_high)), _xxh3_avalanche(out_low)


def xxh3_128(data: bytes, seed: int = 0) -> tuple[int, int]:
    """Return (high64, low64), which is the order digest prints."""
    seed = _u64(seed)
    n = len(data)
    secret = XXH3_SECRET
    if n <= 16:
        if n == 0:
            low = _xxh64_avalanche(seed ^ (_read64(secret, 64) ^ _read64(secret, 72)))
            high = _xxh64_avalanche(seed ^ (_read64(secret, 80) ^ _read64(secret, 88)))
            return high, low
        if n <= 3:
            return _xxh3_1to3_128(data, secret, seed)
        if n <= 8:
            return _xxh3_4to8_128(data, secret, seed)
        return _xxh3_9to16_128(data, secret, seed)
    if n <= 128:
        return _xxh3_17to128_128(data, secret, seed)
    if n <= 240:
        return _xxh3_129to240_128(data, secret, seed)
    long_secret = _xxh3_secret(seed) if seed else secret
    return _xxh3_long_128(data, long_secret)


def _xxh3_17to128_128(data: bytes, secret: bytes, seed: int) -> tuple[int, int]:
    n = len(data)
    low = _u64(n * P64_1)
    high = 0
    if n > 32:
        if n > 64:
            if n > 96:
                low, high = _mix32(low, high, data, 48, n - 64, secret, 96, seed)
            low, high = _mix32(low, high, data, 32, n - 48, secret, 64, seed)
        low, high = _mix32(low, high, data, 16, n - 32, secret, 32, seed)
    low, high = _mix32(low, high, data, 0, n - 16, secret, 0, seed)
    return _xxh3_finish_128(low, high, n, seed)


def _xxh3_129to240_128(data: bytes, secret: bytes, seed: int) -> tuple[int, int]:
    n = len(data)
    low = _u64(n * P64_1)
    high = 0
    for offset in range(32, 160, 32):
        low, high = _mix32(low, high, data, offset - 32, offset - 16, secret, offset - 32, seed)
    low = _xxh3_avalanche(low)
    high = _xxh3_avalanche(high)
    for offset in range(160, n + 1, 32):
        low, high = _mix32(
            low, high, data, offset - 32, offset - 16, secret, 3 + offset - 160, seed
        )
    low, high = _mix32(low, high, data, n - 16, n - 32, secret, 136 - 17 - 16, _u64(0 - seed))
    return _xxh3_finish_128(low, high, n, seed)


def _xxh3_long_128(data: bytes, secret: bytes) -> tuple[int, int]:
    acc = [
        P32_3, P64_1, P64_2, P64_3,
        P64_4, P32_2, P64_5, P32_1,
    ]
    _xxh3_long_loop(acc, data, secret)
    low = _xxh3_merge_accs(acc, secret, 11, _u64(len(data) * P64_1))
    high = _xxh3_merge_accs(
        acc, secret, len(secret) - 64 - 11, _u64(~_u64(len(data) * P64_2))
    )
    return high, low


def _xxh3_1to3_128(data: bytes, secret: bytes, seed: int) -> tuple[int, int]:
    n = len(data)
    c1 = data[0]
    c2 = data[n >> 1]
    c3 = data[n - 1]
    combined_l = _u32((c1 << 16) | (c2 << 24) | c3 | (n << 8))
    combined_h = _rotl32(_swap32(combined_l), 13)
    bit_l = _u64((_read32(secret, 0) ^ _read32(secret, 4)) + seed)
    bit_h = _u64((_read32(secret, 8) ^ _read32(secret, 12)) - seed)
    low = _xxh64_avalanche(combined_l ^ bit_l)
    high = _xxh64_avalanche(combined_h ^ bit_h)
    return high, low


def _xxh3_4to8_128(data: bytes, secret: bytes, seed: int) -> tuple[int, int]:
    seeded = _u64(seed ^ (_swap32(_u32(seed)) << 32))
    n = len(data)
    input_lo = _read32(data, 0)
    input_hi = _read32(data, n - 4)
    input64 = _u64(input_lo + (input_hi << 32))
    bit = _u64((_read64(secret, 16) ^ _read64(secret, 24)) + seeded)
    keyed = input64 ^ bit
    product = keyed * _u64(P64_1 + (n << 2))
    low = _u64(product)
    high = _u64(product >> 64)
    high = _u64(high + (low << 1))
    low ^= high >> 3
    low = _u64(low)
    low ^= low >> 35
    low = _u64(low * PRIME_MX2)
    low ^= low >> 28
    high = _xxh3_avalanche(high)
    return high, low


def _xxh3_9to16_128(data: bytes, secret: bytes, seed: int) -> tuple[int, int]:
    n = len(data)
    bit_l = _u64((_read64(secret, 32) ^ _read64(secret, 40)) - seed)
    bit_h = _u64((_read64(secret, 48) ^ _read64(secret, 56)) + seed)
    input_lo = _read64(data, 0)
    input_hi = _read64(data, n - 8)
    product = (input_lo ^ input_hi ^ bit_l) * P64_1
    low = _u64(product)
    high = _u64(product >> 64)
    low = _u64(low + ((n - 1) << 54))
    input_hi ^= bit_h
    high = _u64(high + input_hi + _u64(_u32(input_hi) * (P32_2 - 1)))
    low ^= _swap64(high)
    product = low * P64_2
    out_low = _u64(product)
    out_high = _u64(_u64(product >> 64) + _u64(high * P64_2))
    return _xxh3_avalanche(out_high), _xxh3_avalanche(out_low)


# --- BLAKE3 -----------------------------------------------------------------

_BLAKE3_IV = (
    0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
    0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
)
_BLAKE3_PERM = (2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8)
_CHUNK_START = 1
_CHUNK_END = 2
_PARENT = 4
_ROOT = 8


def _blake3_g(state, a, b, c, d, x, y) -> None:
    state[a] = _u32(state[a] + state[b] + x)
    state[d] = _rotl32(state[d] ^ state[a], 32 - 16)
    state[c] = _u32(state[c] + state[d])
    state[b] = _rotl32(state[b] ^ state[c], 32 - 12)
    state[a] = _u32(state[a] + state[b] + y)
    state[d] = _rotl32(state[d] ^ state[a], 32 - 8)
    state[c] = _u32(state[c] + state[d])
    state[b] = _rotl32(state[b] ^ state[c], 32 - 7)


def _blake3_compress(cv, block: bytes, block_len: int, counter: int, flags: int) -> list[int]:
    state = list(cv[:8]) + list(_BLAKE3_IV[:4])
    state.append(_u32(counter))
    state.append(_u32(counter >> 32))
    state.append(block_len)
    state.append(flags)
    words = [int.from_bytes(block[i * 4 : i * 4 + 4], "little") for i in range(16)]
    for round_index in range(7):
        _blake3_g(state, 0, 4, 8, 12, words[0], words[1])
        _blake3_g(state, 1, 5, 9, 13, words[2], words[3])
        _blake3_g(state, 2, 6, 10, 14, words[4], words[5])
        _blake3_g(state, 3, 7, 11, 15, words[6], words[7])
        _blake3_g(state, 0, 5, 10, 15, words[8], words[9])
        _blake3_g(state, 1, 6, 11, 12, words[10], words[11])
        _blake3_g(state, 2, 7, 8, 13, words[12], words[13])
        _blake3_g(state, 3, 4, 9, 14, words[14], words[15])
        if round_index != 6:
            words = [words[index] for index in _BLAKE3_PERM]
    return [_u32(state[index] ^ state[index + 8]) for index in range(8)]


def _words_to_bytes(words) -> bytes:
    return b"".join(_u32(word).to_bytes(4, "little") for word in words)


def _blake3_chunk(chunk: bytes, counter: int, root: bool) -> list[int]:
    """ROOT is set only on the last block, and only when this chunk is the root."""
    cv = list(_BLAKE3_IV)
    if not chunk:
        flags = _CHUNK_START | _CHUNK_END | (_ROOT if root else 0)
        return _blake3_compress(cv, bytes(64), 0, counter, flags)
    blocks = (len(chunk) + 63) // 64
    for index in range(blocks):
        piece = chunk[index * 64 : (index + 1) * 64]
        block_flags = 0
        if index == 0:
            block_flags |= _CHUNK_START
        if index == blocks - 1:
            block_flags |= _CHUNK_END
            if root:
                block_flags |= _ROOT
        padded = piece.ljust(64, b"\0")
        cv = _blake3_compress(cv, padded, len(piece), counter, block_flags)
    return cv


def _blake3_parent(left, right, flags: int) -> list[int]:
    block = _words_to_bytes(left) + _words_to_bytes(right)
    return _blake3_compress(list(_BLAKE3_IV), block, 64, 0, flags)


def blake3(data: bytes) -> bytes:
    if len(data) <= 1024:
        return _words_to_bytes(_blake3_chunk(data, 0, True))
    cvs = []
    counter = 0
    for offset in range(0, len(data), 1024):
        cvs.append(_blake3_chunk(data[offset : offset + 1024], counter, False))
        counter += 1
    while len(cvs) > 1:
        root_now = len(cvs) == 2
        nxt = []
        index = 0
        while index + 1 < len(cvs):
            flags = _PARENT | (_ROOT if root_now else 0)
            nxt.append(_blake3_parent(cvs[index], cvs[index + 1], flags))
            index += 2
        if index < len(cvs):
            nxt.append(cvs[index])
        cvs = nxt
    return _words_to_bytes(cvs[0])


# --- SpookyHash V2 ----------------------------------------------------------

_SPOOKY_CONST = 0xDEADBEEFDEADBEEF
_SPOOKY_BLOCK = 96
_SPOOKY_BUF = 192


def _spooky_short_mix(h0, h1, h2, h3):
    h2 = _u64(_rotl64(h2, 50) + h3); h0 ^= h2
    h3 = _u64(_rotl64(h3, 52) + h0); h1 ^= h3
    h0 = _u64(_rotl64(h0, 30) + h1); h2 ^= h0
    h1 = _u64(_rotl64(h1, 41) + h2); h3 ^= h1
    h2 = _u64(_rotl64(h2, 54) + h3); h0 ^= h2
    h3 = _u64(_rotl64(h3, 48) + h0); h1 ^= h3
    h0 = _u64(_rotl64(h0, 38) + h1); h2 ^= h0
    h1 = _u64(_rotl64(h1, 37) + h2); h3 ^= h1
    h2 = _u64(_rotl64(h2, 62) + h3); h0 ^= h2
    h3 = _u64(_rotl64(h3, 34) + h0); h1 ^= h3
    h0 = _u64(_rotl64(h0, 5) + h1); h2 ^= h0
    h1 = _u64(_rotl64(h1, 36) + h2); h3 ^= h1
    return h0, h1, h2, h3


def _spooky_short_end(h0, h1, h2, h3):
    h3 ^= h2; h2 = _rotl64(h2, 15); h3 = _u64(h3 + h2)
    h0 ^= h3; h3 = _rotl64(h3, 52); h0 = _u64(h0 + h3)
    h1 ^= h0; h0 = _rotl64(h0, 26); h1 = _u64(h1 + h0)
    h2 ^= h1; h1 = _rotl64(h1, 51); h2 = _u64(h2 + h1)
    h3 ^= h2; h2 = _rotl64(h2, 28); h3 = _u64(h3 + h2)
    h0 ^= h3; h3 = _rotl64(h3, 9); h0 = _u64(h0 + h3)
    h1 ^= h0; h0 = _rotl64(h0, 47); h1 = _u64(h1 + h0)
    h2 ^= h1; h1 = _rotl64(h1, 54); h2 = _u64(h2 + h1)
    h3 ^= h2; h2 = _rotl64(h2, 32); h3 = _u64(h3 + h2)
    h0 ^= h3; h3 = _rotl64(h3, 25); h0 = _u64(h0 + h3)
    h1 ^= h0; h0 = _rotl64(h0, 63); h1 = _u64(h1 + h0)
    return h0, h1, h2, h3


def _spooky_short(message: bytes, seed1: int, seed2: int) -> tuple[int, int]:
    length = len(message)
    remainder = length % 32
    a = _u64(seed1)
    b = _u64(seed2)
    c = _SPOOKY_CONST
    d = _SPOOKY_CONST
    offset = 0
    if length > 15:
        end = (length // 32) * 32
        while offset < end:
            c = _u64(c + _read64(message, offset))
            d = _u64(d + _read64(message, offset + 8))
            a, b, c, d = _spooky_short_mix(a, b, c, d)
            a = _u64(a + _read64(message, offset + 16))
            b = _u64(b + _read64(message, offset + 24))
            offset += 32
        if remainder >= 16:
            c = _u64(c + _read64(message, offset))
            d = _u64(d + _read64(message, offset + 8))
            a, b, c, d = _spooky_short_mix(a, b, c, d)
            offset += 16
            remainder -= 16
    d = _u64(d + (length << 56))
    if remainder == 0:
        c = _u64(c + _SPOOKY_CONST)
        d = _u64(d + _SPOOKY_CONST)
    else:
        # The switch falls through. Bytes are little-endian loads of the tail.
        if remainder >= 12:
            c = _u64(c + _read64(message, offset))
            d = _u64(d + _read32(message, offset + 8))
            base = offset + 12
            for index in range(remainder - 12):
                d = _u64(d + (message[base + index] << (8 * index + 32)))
        elif remainder >= 8:
            c = _u64(c + _read64(message, offset))
            base = offset + 8
            for index in range(remainder - 8):
                d = _u64(d + (message[base + index] << (8 * index)))
        else:
            for index in range(remainder):
                shift = 8 * index
                if index < 4:
                    c = _u64(c + (message[offset + index] << shift))
                else:
                    c = _u64(c + (message[offset + index] << shift))
    a, b, c, d = _spooky_short_end(a, b, c, d)
    return a, b


def _spooky_mix(data: bytes, offset: int, s) -> list[int]:
    s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11 = s
    words = [_read64(data, offset + 8 * i) for i in range(12)]
    s0 = _u64(s0 + words[0]); s2 ^= s10; s11 ^= s0; s0 = _rotl64(s0, 11); s11 = _u64(s11 + s1)
    s1 = _u64(s1 + words[1]); s3 ^= s11; s0 ^= s1; s1 = _rotl64(s1, 32); s0 = _u64(s0 + s2)
    s2 = _u64(s2 + words[2]); s4 ^= s0; s1 ^= s2; s2 = _rotl64(s2, 43); s1 = _u64(s1 + s3)
    s3 = _u64(s3 + words[3]); s5 ^= s1; s2 ^= s3; s3 = _rotl64(s3, 31); s2 = _u64(s2 + s4)
    s4 = _u64(s4 + words[4]); s6 ^= s2; s3 ^= s4; s4 = _rotl64(s4, 17); s3 = _u64(s3 + s5)
    s5 = _u64(s5 + words[5]); s7 ^= s3; s4 ^= s5; s5 = _rotl64(s5, 28); s4 = _u64(s4 + s6)
    s6 = _u64(s6 + words[6]); s8 ^= s4; s5 ^= s6; s6 = _rotl64(s6, 39); s5 = _u64(s5 + s7)
    s7 = _u64(s7 + words[7]); s9 ^= s5; s6 ^= s7; s7 = _rotl64(s7, 57); s6 = _u64(s6 + s8)
    s8 = _u64(s8 + words[8]); s10 ^= s6; s7 ^= s8; s8 = _rotl64(s8, 55); s7 = _u64(s7 + s9)
    s9 = _u64(s9 + words[9]); s11 ^= s7; s8 ^= s9; s9 = _rotl64(s9, 54); s8 = _u64(s8 + s10)
    s10 = _u64(s10 + words[10]); s0 ^= s8; s9 ^= s10; s10 = _rotl64(s10, 22); s9 = _u64(s9 + s11)
    s11 = _u64(s11 + words[11]); s1 ^= s9; s10 ^= s11; s11 = _rotl64(s11, 46); s10 = _u64(s10 + s0)
    return [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11]


def _spooky_end_partial(s) -> list[int]:
    h0, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11 = s
    h11 = _u64(h11 + h1); h2 ^= h11; h1 = _rotl64(h1, 44)
    h0 = _u64(h0 + h2); h3 ^= h0; h2 = _rotl64(h2, 15)
    h1 = _u64(h1 + h3); h4 ^= h1; h3 = _rotl64(h3, 34)
    h2 = _u64(h2 + h4); h5 ^= h2; h4 = _rotl64(h4, 21)
    h3 = _u64(h3 + h5); h6 ^= h3; h5 = _rotl64(h5, 38)
    h4 = _u64(h4 + h6); h7 ^= h4; h6 = _rotl64(h6, 33)
    h5 = _u64(h5 + h7); h8 ^= h5; h7 = _rotl64(h7, 10)
    h6 = _u64(h6 + h8); h9 ^= h6; h8 = _rotl64(h8, 13)
    h7 = _u64(h7 + h9); h10 ^= h7; h9 = _rotl64(h9, 38)
    h8 = _u64(h8 + h10); h11 ^= h8; h10 = _rotl64(h10, 53)
    h9 = _u64(h9 + h11); h0 ^= h9; h11 = _rotl64(h11, 42)
    h10 = _u64(h10 + h0); h1 ^= h10; h0 = _rotl64(h0, 54)
    return [h0, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11]


def _spooky_long(message: bytes, seed1: int, seed2: int) -> tuple[int, int]:
    state = [
        _u64(seed1), _u64(seed2), _SPOOKY_CONST,
        _u64(seed1), _u64(seed2), _SPOOKY_CONST,
        _u64(seed1), _u64(seed2), _SPOOKY_CONST,
        _u64(seed1), _u64(seed2), _SPOOKY_CONST,
    ]
    length = len(message)
    blocks = length // _SPOOKY_BLOCK
    for index in range(blocks):
        state = _spooky_mix(message, index * _SPOOKY_BLOCK, state)
    remainder = length - blocks * _SPOOKY_BLOCK
    tail = bytearray(message[blocks * _SPOOKY_BLOCK :])
    tail.extend(b"\0" * (_SPOOKY_BLOCK - remainder))
    tail[_SPOOKY_BLOCK - 1] = remainder
    words = [_read64(tail, 8 * i) for i in range(12)]
    state = [_u64(state[i] + words[i]) for i in range(12)]
    state = _spooky_end_partial(state)
    state = _spooky_end_partial(state)
    state = _spooky_end_partial(state)
    return state[0], state[1]


def spooky128(message: bytes, seed1: int = 0, seed2: int = 0) -> bytes:
    """16 little-endian bytes, hash1 then hash2, which is what digest pastes."""
    if len(message) < _SPOOKY_BUF:
        h1, h2 = _spooky_short(message, seed1, seed2)
    else:
        h1, h2 = _spooky_long(message, seed1, seed2)
    return h1.to_bytes(8, "little") + h2.to_bytes(8, "little")
