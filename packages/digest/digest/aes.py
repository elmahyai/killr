"""AES-128, AES-192, and AES-256, matching digest 0.6.39.

The block cipher is FIPS-197. ECB, CBC, CFB, and CTR follow the R
wrapper in ``R/AES.R``, including the IV updates that closure keeps.
"""

from __future__ import annotations

import math
import warnings

_BLOCK = 16
_MODES = ("ECB", "CBC", "CFB", "CTR")


def _xtime(a: int) -> int:
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF


def _mul(a: int, b: int) -> int:
    product = 0
    for _ in range(8):
        if b & 1:
            product ^= a
        a = _xtime(a)
        b >>= 1
    return product


def _rotl8(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (8 - shift))) & 0xFF


def _gf_inv(value: int) -> int:
    if value == 0:
        return 0
    result = 1
    base = value
    exponent = 254
    while exponent:
        if exponent & 1:
            result = _mul(result, base)
        base = _mul(base, base)
        exponent >>= 1
    return result


def _sbox_byte(value: int) -> int:
    inverse = _gf_inv(value)
    return (
        inverse
        ^ _rotl8(inverse, 1)
        ^ _rotl8(inverse, 2)
        ^ _rotl8(inverse, 3)
        ^ _rotl8(inverse, 4)
        ^ 0x63
    ) & 0xFF


_SBOX = bytes(_sbox_byte(i) for i in range(256))
_INV_SBOX = bytearray(256)
for _index, _substituted in enumerate(_SBOX):
    _INV_SBOX[_substituted] = _index
_INV_SBOX = bytes(_INV_SBOX)

_RCON = [0]
_rcon_byte = 1
for _ in range(14):
    _RCON.append(_rcon_byte)
    _rcon_byte = _xtime(_rcon_byte)

assert _SBOX[0x00] == 0x63
assert _SBOX[0x01] == 0x7C
assert _SBOX[0x53] == 0xED


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=3)


def _match_mode(mode) -> str:
    """``match.arg`` against ECB, CBC, CFB, and CTR.

    ``NULL`` is the first choice. An ambiguous prefix is not a match.
    The choices are quoted the way R 4.5 ``dQuote`` quotes them.
    """
    if mode is None:
        return "ECB"
    if isinstance(mode, (list, tuple)):
        if list(mode) == list(_MODES):
            return "ECB"
        if len(mode) != 1:
            raise ValueError("'arg' must be of length 1")
        mode = mode[0]
        if mode is None:
            return "ECB"
    if not isinstance(mode, str):
        raise ValueError("'arg' must be NULL or a character vector")
    if mode in _MODES:
        return mode
    partial = [name for name in _MODES if mode and name.startswith(mode)]
    if len(partial) == 1:
        return partial[0]
    quoted = ", ".join(f"\u201c{name}\u201d" for name in _MODES)
    raise ValueError(f"'arg' should be one of {quoted}")


def _as_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and math.isnan(value):
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (list, tuple)):
        raise ValueError(f"'length = {len(value)}' in coercion to 'logical(1)'")
    if value is None:
        raise ValueError("argument is of length zero")
    raise ValueError("argument is not interpretable as logical")


def _raw_byte(value, na_from_string: bool) -> tuple[int, bool, bool]:
    """Return ``(byte, out_of_range, na_introduced)``."""
    if isinstance(value, bool):
        return (1 if value else 0), False, False
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return 0, True, True
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return 0, True, na_from_string
    if isinstance(value, (int, float)):
        truncated = math.trunc(value)
        if truncated < 0 or truncated > 255:
            return 0, True, False
        return int(truncated), False, False
    raise ValueError("cannot coerce type '%s' to vector of type 'raw'" % type(value).__name__)


def as_raw(value) -> bytes:
    """R's ``as.raw``. ``NULL`` is an empty raw vector."""
    if value is None:
        return b""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    items = value if isinstance(value, (list, tuple, range)) else (value,)
    out = bytearray()
    out_of_range = False
    na_introduced = False
    for item in items:
        byte, bad, na = _raw_byte(item, False)
        out.append(byte)
        out_of_range = out_of_range or bad
        na_introduced = na_introduced or na
    if na_introduced:
        _warn("NAs introduced by coercion")
    if out_of_range:
        _warn("out-of-range values treated as 0 in coercion to raw")
    return bytes(out)


def _plaintext(text) -> bytes:
    if isinstance(text, str):
        return text.encode("utf-8")
    if isinstance(text, (list, tuple)) and all(isinstance(item, str) for item in text):
        if len(text) == 0:
            raise ValueError("argument must be a character vector of length 1")
        if len(text) > 1:
            _warn(
                "argument should be a character vector of length 1\n"
                "all but the first element will be ignored"
            )
        return text[0].encode("utf-8")
    if isinstance(text, memoryview):
        return text.tobytes()
    if isinstance(text, (bytes, bytearray)):
        return bytes(text)
    raise ValueError("Text must be a raw vector")


def _ciphertext(text) -> bytes:
    if isinstance(text, memoryview):
        return text.tobytes()
    if isinstance(text, (bytes, bytearray)):
        return bytes(text)
    raise ValueError("Ciphertext must be a raw vector")


def _xor(left: bytes, right: bytes) -> bytes:
    """Element-wise raw ``xor``. The result has the longer length."""
    if len(left) == 0 or len(right) == 0:
        return b""
    length = max(len(left), len(right))
    if length % min(len(left), len(right)) != 0:
        # Raw xor is `(x | y) & !(x & y)`, so R warns once for each bitwise op.
        _warn("longer object length is not a multiple of shorter object length")
        _warn("longer object length is not a multiple of shorter object length")
    return bytes(left[i % len(left)] ^ right[i % len(right)] for i in range(length))


def _recycle(value: bytes, count: int) -> bytes:
    """Fill ``count`` positions from ``value``, the way R's ``[<-`` recycles."""
    if len(value) == 0:
        raise ValueError("replacement has length zero")
    if count % len(value) != 0:
        _warn("number of items to replace is not a multiple of replacement length")
    return bytes(value[i % len(value)] for i in range(count))


def _escape_raw(data: bytes) -> str:
    """Escapes used in R's ``embedded nul in string`` message."""
    named = {7: "\\a", 8: "\\b", 9: "\\t", 10: "\\n", 11: "\\v", 12: "\\f", 13: "\\r", 92: "\\\\"}
    parts = []
    for byte in data:
        if byte == 0:
            parts.append("\\0")
        elif byte in named:
            parts.append(named[byte])
        elif 32 <= byte <= 126:
            parts.append(chr(byte))
        elif byte < 128:
            parts.append(f"\\{byte:03o}")
        else:
            parts.append(f"\\x{byte:02x}")
    return "".join(parts)


def _raw_to_char(data: bytes) -> str:
    """``rawToChar``. A trailing run of nuls is dropped. A later non-zero byte is an error."""
    if b"\x00" not in data:
        return data.decode("latin-1")
    head, tail = data.split(b"\x00", 1)
    if any(byte != 0 for byte in tail):
        raise ValueError(f"embedded nul in string: '{_escape_raw(data)}'")
    return head.decode("latin-1")


def _expand_key(key: bytes) -> tuple[bytes, int]:
    word_count = len(key) // 4
    rounds = word_count + 6
    words = [bytearray(key[4 * i : 4 * i + 4]) for i in range(word_count)]
    index = word_count
    while len(words) < 4 * (rounds + 1):
        temp = bytearray(words[-1])
        if index % word_count == 0:
            temp = bytearray(_SBOX[byte] for byte in temp[1:] + temp[:1])
            temp[0] ^= _RCON[index // word_count]
        elif word_count > 6 and index % word_count == 4:
            temp = bytearray(_SBOX[byte] for byte in temp)
        previous = words[len(words) - word_count]
        words.append(bytearray(previous[j] ^ temp[j] for j in range(4)))
        index += 1
    flat = bytearray()
    for word in words:
        flat.extend(word)
    return bytes(flat), rounds


def _add_round_key(state: bytearray, round_keys: bytes, round_index: int) -> None:
    offset = round_index * _BLOCK
    for index, byte in enumerate(state):
        state[index] = byte ^ round_keys[offset + index]


def _shift_rows(state: bytearray) -> None:
    state[1], state[5], state[9], state[13] = state[5], state[9], state[13], state[1]
    state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
    state[3], state[7], state[11], state[15] = state[15], state[3], state[7], state[11]


def _inv_shift_rows(state: bytearray) -> None:
    state[1], state[5], state[9], state[13] = state[13], state[1], state[5], state[9]
    state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
    state[3], state[7], state[11], state[15] = state[7], state[11], state[15], state[3]


def _mix_columns(state: bytearray) -> None:
    for column in range(4):
        offset = 4 * column
        a0, a1, a2, a3 = state[offset : offset + 4]
        folded = a0 ^ a1 ^ a2 ^ a3
        state[offset] ^= folded ^ _xtime(a0 ^ a1)
        state[offset + 1] ^= folded ^ _xtime(a1 ^ a2)
        state[offset + 2] ^= folded ^ _xtime(a2 ^ a3)
        state[offset + 3] ^= folded ^ _xtime(a3 ^ a0)


def _inv_mix_columns(state: bytearray) -> None:
    for column in range(4):
        offset = 4 * column
        a0, a1, a2, a3 = state[offset : offset + 4]
        state[offset] = _mul(a0, 0x0E) ^ _mul(a1, 0x0B) ^ _mul(a2, 0x0D) ^ _mul(a3, 0x09)
        state[offset + 1] = _mul(a0, 0x09) ^ _mul(a1, 0x0E) ^ _mul(a2, 0x0B) ^ _mul(a3, 0x0D)
        state[offset + 2] = _mul(a0, 0x0D) ^ _mul(a1, 0x09) ^ _mul(a2, 0x0E) ^ _mul(a3, 0x0B)
        state[offset + 3] = _mul(a0, 0x0B) ^ _mul(a1, 0x0D) ^ _mul(a2, 0x09) ^ _mul(a3, 0x0E)


def _encrypt_block(block: bytes, round_keys: bytes, rounds: int) -> bytes:
    state = bytearray(block)
    _add_round_key(state, round_keys, 0)
    for round_index in range(1, rounds):
        for index, byte in enumerate(state):
            state[index] = _SBOX[byte]
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, round_keys, round_index)
    for index, byte in enumerate(state):
        state[index] = _SBOX[byte]
    _shift_rows(state)
    _add_round_key(state, round_keys, rounds)
    return bytes(state)


def _decrypt_block(block: bytes, round_keys: bytes, rounds: int) -> bytes:
    state = bytearray(block)
    _add_round_key(state, round_keys, rounds)
    for round_index in range(rounds - 1, 0, -1):
        _inv_shift_rows(state)
        for index, byte in enumerate(state):
            state[index] = _INV_SBOX[byte]
        _add_round_key(state, round_keys, round_index)
        _inv_mix_columns(state)
    _inv_shift_rows(state)
    for index, byte in enumerate(state):
        state[index] = _INV_SBOX[byte]
    _add_round_key(state, round_keys, 0)
    return bytes(state)


class AES:
    """An AES cipher object. ``mode`` is ECB, CBC, CFB, or CTR, or a unique prefix."""

    def __init__(self, key, mode="ECB", IV=None, padding=False):
        chosen = _match_mode(mode)
        if _as_flag(padding) and chosen != "CBC":
            raise ValueError("Only CBC mode supports padding")
        key_bytes = as_raw(key)
        if len(key_bytes) not in (16, 24, 32):
            raise ValueError("AES only supports 16, 24 and 32 byte keys")
        self._round_keys, self._rounds = _expand_key(key_bytes)
        self._key_size = len(key_bytes)
        self._mode = chosen
        self._padding = _as_flag(padding)
        self._iv = bytearray(as_raw(IV))

    def block_size(self) -> int:
        return _BLOCK

    def key_size(self) -> int:
        return self._key_size

    def mode(self) -> str:
        return self._mode

    def IV(self) -> bytes:
        return bytes(self._iv)

    def __str__(self) -> str:
        # cat() separates the trailing newline argument with a space.
        return f"AES cipher object; mode {self._mode} key size {self._key_size} "

    def __repr__(self) -> str:
        return str(self)

    def _ecb(self, data: bytes, decrypt: bool) -> bytes:
        if len(data) % _BLOCK:
            if decrypt:
                raise ValueError("Ciphertext length must be a multiple of 16 bytes")
            raise ValueError("Text length must be a multiple of 16 bytes")
        blocks = []
        for offset in range(0, len(data), _BLOCK):
            block = data[offset : offset + _BLOCK]
            if decrypt:
                blocks.append(_decrypt_block(block, self._round_keys, self._rounds))
            else:
                blocks.append(_encrypt_block(block, self._round_keys, self._rounds))
        return b"".join(blocks)

    def _increment_iv(self) -> None:
        """Add 1 to byte 16 of the IV, carrying toward byte 1. A short IV is extended with zeros."""
        byte = 16
        while True:
            if len(self._iv) < byte:
                self._iv.extend(b"\x00" * (byte - len(self._iv)))
            index = byte - 1
            self._iv[index] = (self._iv[index] + 1) & 0xFF
            if self._iv[index] != 0 or byte == 1:
                return
            byte -= 1

    def _ctr_empty(self) -> bytes:
        # R's `for (i in 1:blocks)` with blocks == 0 iterates `c(1, 0)`.
        if len(self._iv) == 0:
            raise ValueError("replacement has length zero")
        if 16 % len(self._iv) != 0:
            _warn("number of items to replace is not a multiple of replacement length")
        self._increment_iv()
        if len(self._iv) == 0 or 1 % len(self._iv) != 0:
            _warn("number of items to replace is not a multiple of replacement length")
        self._increment_iv()
        return b""

    def _crypt_ctr(self, data: bytes) -> bytes:
        blocks = (len(data) + 15) // 16
        if blocks == 0:
            return self._ctr_empty()
        counter = bytearray()
        for _ in range(blocks):
            counter.extend(_recycle(bytes(self._iv), _BLOCK))
            self._increment_iv()
        stream = self._ecb(bytes(counter), decrypt=False)[: len(data)]
        return bytes(left ^ right for left, right in zip(data, stream))

    def _encrypt_cbc(self, data: bytes) -> bytes:
        if self._padding:
            pad = _BLOCK - (len(data) % _BLOCK)
            data += bytes([pad]) * pad
        if len(data) % _BLOCK:
            raise ValueError(
                "Text length must be a multiple of 16 bytes, or use `padding=TRUE`"
            )
        out = bytearray()
        for offset in range(0, len(data), _BLOCK):
            mixed = _xor(data[offset : offset + _BLOCK], bytes(self._iv))
            if len(mixed) % _BLOCK:
                raise ValueError("Text length must be a multiple of 16 bytes")
            encrypted = self._ecb(mixed, decrypt=False)
            self._iv = bytearray(encrypted)
            out.extend(_recycle(encrypted, _BLOCK))
        return bytes(out)

    def _decrypt_cbc(self, data: bytes) -> bytes:
        if len(data) % _BLOCK:
            raise ValueError("Ciphertext length must be a multiple of 16 bytes")
        out = bytearray()
        for offset in range(0, len(data), _BLOCK):
            block = data[offset : offset + _BLOCK]
            mixed = _xor(_decrypt_block(block, self._round_keys, self._rounds), bytes(self._iv))
            out.extend(_recycle(mixed, _BLOCK))
            self._iv = bytearray(block)
        if self._padding:
            if len(out) == 0:
                raise ValueError(
                    "invalid 'n' - must contain at least one non-missing element, got none."
                )
            count = -out[-1]
            if count < 0:
                keep = max(len(out) + count, 0)
            else:
                keep = min(count, len(out))
            out = out[:keep]
        return bytes(out)

    def _crypt_cfb(self, data: bytes, decrypt: bool) -> bytes:
        if len(self._iv) != _BLOCK:
            raise ValueError("IV length must equal block size")
        out = bytearray(len(data))
        offset = 0
        while offset < len(data):
            block = data[offset : offset + _BLOCK]
            # `out[0:len]` drops index 0, which leaves the first `len` bytes.
            stream = _encrypt_block(bytes(self._iv), self._round_keys, self._rounds)[: len(block)]
            mixed = bytes(left ^ right for left, right in zip(block, stream))
            out[offset : offset + len(block)] = mixed
            self._iv = bytearray(block if decrypt else mixed)
            offset += len(block)
        return bytes(out)

    def encrypt(self, text) -> bytes:
        data = _plaintext(text)
        if self._mode == "ECB":
            return self._ecb(data, decrypt=False)
        if self._mode == "CBC":
            return self._encrypt_cbc(data)
        if self._mode == "CFB":
            return self._crypt_cfb(data, decrypt=False)
        return self._crypt_ctr(data)

    def decrypt(self, ciphertext, raw=False):
        data = _ciphertext(ciphertext)
        if self._mode == "ECB":
            result = self._ecb(data, decrypt=True)
        elif self._mode == "CBC":
            result = self._decrypt_cbc(data)
        elif self._mode == "CFB":
            result = self._crypt_cfb(data, decrypt=True)
        else:
            result = self._crypt_ctr(data)
        if raw:
            return result
        return _raw_to_char(result)
