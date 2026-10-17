"""File permission bits from fs 2.1.0.

Symbolic modes follow the BSD ``setmode`` used by the installed package.
A character vector longer than two is read back rotated, because the
installed loop indexes with ``((i + 1) %% length) + 1``.
"""

from __future__ import annotations

import os
import re

from fs._error import FsError

S_ISUID = 0o4000
S_ISGID = 0o2000
S_ISVTX = 0o1000
S_IRUSR = 0o400
S_IWUSR = 0o200
S_IXUSR = 0o100
S_IRWXU = 0o700
S_IRGRP = 0o040
S_IWGRP = 0o020
S_IXGRP = 0o010
S_IRWXG = 0o070
S_IROTH = 0o004
S_IWOTH = 0o002
S_IXOTH = 0o001
S_IRWXO = 0o007
S_IFDIR = 0o040000
STANDARD_BITS = S_ISUID | S_ISGID | S_IRWXU | S_IRWXG | S_IRWXO
S_ISTXT = S_ISVTX

_CLR = 0x01
_SET = 0x02
_GBITS = 0x04
_OBITS = 0x08
_UBITS = 0x10
_DISPLAY = re.compile(r"^[rwxXst-]{9}$")


class FsPerms(list):
    """Integer permission bits, shown as a nine-character mode."""

    def __str__(self) -> str:
        return " ".join(format_fs_perms(self))


def _i32(value: int) -> int:
    value &= 0xFFFFFFFF
    if value >= 0x80000000:
        return value - 0x100000000
    return value


def _mask() -> int:
    current = os.umask(0)
    os.umask(current)
    return (~current) & 0xFFFFFFFF


def _cmd(op, who, oparg, mask) -> list[dict]:
    made = []
    if op == "=":
        made.append({"cmd": "-", "cmd2": 0, "bits": who or STANDARD_BITS})
        op = "+"
    if op in {"+", "-", "X"}:
        made.append({"cmd": op, "cmd2": 0, "bits": (who or mask) & oparg})
        return made
    command = {"cmd": op, "cmd2": 0, "bits": 0}
    if who:
        command["cmd2"] = (
            (_UBITS if who & S_IRUSR else 0)
            | (_GBITS if who & S_IRGRP else 0)
            | (_OBITS if who & S_IROTH else 0)
        )
        command["bits"] = 0xFFFFFFFF
    else:
        command["cmd2"] = _UBITS | _GBITS | _OBITS
        command["bits"] = mask
    if oparg == "+":
        command["cmd2"] |= _SET
    elif oparg == "-":
        command["cmd2"] |= _CLR
    elif oparg == "=":
        command["cmd2"] |= _SET | _CLR
    made.append(command)
    return made


def _getmode(commands: list[dict], omode: int) -> int:
    newmode = omode & 0xFFFFFFFF
    for command in commands:
        cmd = command["cmd"]
        bits = command["bits"] & 0xFFFFFFFF
        cmd2 = command["cmd2"]
        if cmd == "u":
            value = (newmode & S_IRWXU) >> 6
        elif cmd == "g":
            value = (newmode & S_IRWXG) >> 3
        elif cmd == "o":
            value = newmode & S_IRWXO
        elif cmd == "+":
            newmode |= bits
            continue
        elif cmd == "-":
            newmode &= ~bits
            continue
        elif cmd == "X":
            if omode & (S_IFDIR | S_IXUSR | S_IXGRP | S_IXOTH):
                newmode |= bits
            continue
        else:
            break
        if cmd in "ugo":
            if cmd2 & _CLR:
                clrval = value if not (cmd2 & _SET) else S_IRWXO
                if cmd2 & _UBITS:
                    newmode &= ~((clrval << 6) & bits)
                if cmd2 & _GBITS:
                    newmode &= ~((clrval << 3) & bits)
                if cmd2 & _OBITS:
                    newmode &= ~(clrval & bits)
            if cmd2 & _SET:
                if cmd2 & _UBITS:
                    newmode |= (value << 6) & bits
                if cmd2 & _GBITS:
                    newmode |= (value << 3) & bits
                if cmd2 & _OBITS:
                    newmode |= value & bits
    return _i32(newmode)


def _compress(commands: list[dict]) -> list[dict]:
    output = []
    index = 0
    while index < len(commands):
        while index < len(commands) and commands[index]["cmd"] not in {"+", "-", "X"}:
            output.append(commands[index])
            if commands[index]["cmd"] == "\0":
                return output
            index += 1
        cleared = set_bits = extra = 0
        while index < len(commands) and commands[index]["cmd"] in {"+", "-", "X"}:
            op = commands[index]["cmd"]
            bits = commands[index]["bits"]
            if op == "-":
                cleared |= bits
                set_bits &= ~bits
                extra &= ~bits
            elif op == "+":
                set_bits |= bits
                cleared &= ~bits
                extra &= ~bits
            else:
                extra |= bits & ~set_bits
            index += 1
        if cleared:
            output.append({"cmd": "-", "cmd2": 0, "bits": cleared})
        if set_bits:
            output.append({"cmd": "+", "cmd2": 0, "bits": set_bits})
        if extra:
            output.append({"cmd": "X", "cmd2": 0, "bits": extra})
    output.append({"cmd": "\0", "cmd2": 0, "bits": 0})
    return output


def _setmode(text: str) -> list[dict]:
    if text == "":
        raise FsError(f"Invalid mode '{text}'")
    mask = _mask()
    if text[0].isdigit():
        if any(char not in "01234567" for char in text):
            raise FsError(f"Invalid mode '{text}'")
        try:
            value = int(text, 8)
        except ValueError as error:
            raise FsError(f"Invalid mode '{text}'") from error
        if value & ~(STANDARD_BITS | S_ISTXT):
            raise FsError(f"Invalid mode '{text}'")
        commands = _cmd("=", STANDARD_BITS | S_ISTXT, value, mask)
        commands.append({"cmd": "\0", "cmd2": 0, "bits": 0})
        return commands
    commands: list[dict] = []
    index = 0
    size = len(text)

    def clause(who: int) -> bool:
        """Parse one operator. Return true when a comma starts the next who."""
        nonlocal index
        if index >= size or text[index] not in "+-=":
            raise FsError(f"Invalid mode '{text}'")
        op = text[index]
        index += 1
        equal_done = 0
        who = who & ~S_ISTXT
        perm = 0
        perm_x = 0
        while index < size:
            char = text[index]
            if char == "r":
                perm |= S_IRUSR | S_IRGRP | S_IROTH
            elif char == "s":
                if who == 0 or (who & ~S_IRWXO):
                    perm |= S_ISUID | S_ISGID
            elif char == "t":
                if who == 0 or (who & ~S_IRWXO):
                    who |= S_ISTXT
                    perm |= S_ISTXT
            elif char == "w":
                perm |= S_IWUSR | S_IWGRP | S_IWOTH
            elif char == "X":
                perm_x = S_IXUSR | S_IXGRP | S_IXOTH
            elif char == "x":
                perm |= S_IXUSR | S_IXGRP | S_IXOTH
            elif char in "ugo":
                if perm:
                    commands.extend(_cmd(op, who, perm, mask))
                    perm = 0
                if op == "=":
                    equal_done = 1
                if op == "+" and perm_x:
                    commands.extend(_cmd("X", who, perm_x, mask))
                    perm_x = 0
                commands.extend(_cmd(char, who, op, mask))
            else:
                if perm or (op == "=" and not equal_done):
                    if op == "=":
                        equal_done = 1
                    commands.extend(_cmd(op, who, perm, mask))
                    perm = 0
                if perm_x:
                    commands.extend(_cmd("X", who, perm_x, mask))
                return False
            index += 1
        if perm or (op == "=" and not equal_done):
            commands.extend(_cmd(op, who, perm, mask))
        if perm_x:
            commands.extend(_cmd("X", who, perm_x, mask))
        return True

    while index < size:
        who = 0
        while index < size and text[index] in "augo":
            char = text[index]
            if char == "a":
                who |= STANDARD_BITS
            elif char == "u":
                who |= S_ISUID | S_IRWXU
            elif char == "g":
                who |= S_ISGID | S_IRWXG
            else:
                who |= S_IRWXO
            index += 1
        while True:
            finished = clause(who)
            if finished or index >= size:
                index = size
                break
            if text[index] == ",":
                index += 1
                break
    commands.append({"cmd": "\0", "cmd2": 0, "bits": 0})
    return _compress(commands)


def getmode(text: str, mode: int = 0) -> int:
    """Apply one symbolic or octal mode to an existing mode integer."""
    return _getmode(_setmode(text), 0 if mode is None else int(mode))


def _display_to_symbolic(text: str) -> str:
    return f"u={text[0:3]},g={text[3:6]},o={text[6:9]}"


def _as_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:
            return None
        if value != int(value):
            raise FsError("'x' cannot be coerced to class \"fs_perms\"")
        return int(value)
    raise FsError("'x' cannot be coerced to class \"fs_perms\"")


def _numeric_items(x) -> list | None:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return [_as_int(x)]
    if isinstance(x, (list, tuple)) and all(
        item is None or (isinstance(item, (int, float)) and not isinstance(item, bool))
        for item in x
    ):
        return [_as_int(item) for item in x]
    return None


def fs_perms(x=None, mode=0) -> FsPerms:
    """Coerce numbers or mode strings such as ``644`` and ``u+rw``."""
    if x is None:
        return FsPerms()
    if isinstance(x, FsPerms):
        return FsPerms(x)
    numeric = _numeric_items(x)
    if numeric is not None:
        return FsPerms(numeric)
    texts = [x] if isinstance(x, str) else list(x)
    modes = [mode] if isinstance(mode, (int, float)) and not isinstance(mode, bool) else list(mode)
    if len(texts) > 1 and len(modes) > 1 and len(texts) != len(modes):
        raise FsError(
            "`x` and `mode` must have compatible lengths:\n"
            f"* `x` has length {len(texts)}\n"
            f"* `mode` has length {len(modes)}"
        )
    converted = []
    for item in texts:
        if item is None:
            converted.append(None)
            continue
        text = str(item)
        if _DISPLAY.fullmatch(text):
            text = _display_to_symbolic(text)
        converted.append(text)
    count = max(len(converted), len(modes), 1)
    values = []
    for index in range(count):
        if not converted:
            break
        source = (index + 2) % len(converted)
        mode_at = (index + 2) % len(modes)
        text = converted[source]
        base = modes[mode_at]
        if text is None:
            values.append(None)
        else:
            values.append(getmode(text, 0 if base is None else int(base)))
    return FsPerms(values)


as_fs_perms = fs_perms


def format_fs_perms(x) -> list[str]:
    """Nine-character mode. The file-type character ``strmode`` prints is omitted."""
    values = list(x) if isinstance(x, FsPerms) else list(fs_perms(x))
    return [_format_one(value) for value in values]


def _format_one(mode) -> str:
    if mode is None:
        mode = 0
    mode = int(mode)

    def bit(mask: int, yes: str) -> str:
        return yes if mode & mask else "-"

    user_exec = mode & S_IXUSR
    set_user = mode & S_ISUID
    if set_user and user_exec:
        user_x = "s"
    elif set_user:
        user_x = "S"
    elif user_exec:
        user_x = "x"
    else:
        user_x = "-"
    group_exec = mode & S_IXGRP
    set_group = mode & S_ISGID
    if set_group and group_exec:
        group_x = "s"
    elif set_group:
        group_x = "S"
    elif group_exec:
        group_x = "x"
    else:
        group_x = "-"
    other_exec = mode & S_IXOTH
    sticky = mode & S_ISVTX
    if sticky and other_exec:
        other_x = "t"
    elif sticky:
        other_x = "T"
    elif other_exec:
        other_x = "x"
    else:
        other_x = "-"
    return (
        bit(S_IRUSR, "r")
        + bit(S_IWUSR, "w")
        + user_x
        + bit(S_IRGRP, "r")
        + bit(S_IWGRP, "w")
        + group_x
        + bit(S_IROTH, "r")
        + bit(S_IWOTH, "w")
        + other_x
    )


def bit_not(x) -> FsPerms:
    return FsPerms([None if value is None else _i32(~int(value)) for value in fs_perms_raw(x)])


def bit_and(left, right) -> FsPerms:
    return _bitop(left, right, lambda a, b: a & b)


def bit_or(left, right) -> FsPerms:
    return _bitop(left, right, lambda a, b: a | b)


def perms_equal(left, right) -> list:
    """True where every bit set in ``right`` is also set in ``left``."""
    rights = fs_perms(right)
    masked = bit_and(left, rights)
    result = []
    for one, two in zip(masked, rights):
        if one is None or two is None:
            result.append(None)
        else:
            result.append(int(one) == int(two))
    return result


def fs_perms_raw(x) -> list:
    if isinstance(x, FsPerms):
        return list(x)
    if isinstance(x, (list, tuple)) and all(isinstance(item, (int, type(None))) for item in x):
        return list(x)
    return list(fs_perms(x))


def _bitop(left, right, op) -> FsPerms:
    ones = fs_perms_raw(left)
    twos = list(fs_perms(right))
    if len(ones) == 1 and len(twos) != 1:
        ones = ones * len(twos)
    elif len(twos) == 1 and len(ones) != 1:
        twos = twos * len(ones)
    values = []
    for one, two in zip(ones, twos):
        if one is None or two is None:
            values.append(None)
        else:
            values.append(_i32(op(int(one), int(two))))
    return FsPerms(values)
