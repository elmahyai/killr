"""License specification tools from R tools."""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent


def _posix_regex(pattern: str) -> str:
    out = pattern
    out = out.replace("[[:space:]]", r"\s")
    out = out.replace("[[:digit:]]", r"\d")
    return out


def _re_anchor(pattern: str) -> str:
    if not pattern:
        return pattern
    return f"^{pattern}$"


@lru_cache(maxsize=1)
def _bundle() -> dict[str, Any]:
    data = json.loads((_HERE / "license_data.json").read_text(encoding="utf-8"))
    tab_a = dict(data["tab_versioned_style_A"])
    tab_a.setdefault("CeCILL", tab_a.pop("CeCILL.1", [11, 12]))
    data["tab_versioned_style_A"] = tab_a
    return data


@lru_cache(maxsize=1)
def _compiled() -> dict[str, re.Pattern[str]]:
    data = _bundle()
    keys = [
        "re_component",
        "re_license_file",
        "re_license_extension",
        "re_single_version_spec",
        "re_sss",
        "re_unversioned",
        "re_versioned_style_A",
        "re_versioned_style_B",
        "re_versioned_style_C",
        "valid_numeric_version",
    ]
    return {key: re.compile(_posix_regex(data[key])) for key in keys}


def _parse_numeric_version(version: str) -> tuple[int, ...]:
    parts = re.split(r"[.-]", version)
    return tuple(int(part) for part in parts if part)


def _compare_numeric(op: str, left: tuple[int, ...], right: tuple[int, ...]) -> bool:
    for index in range(max(len(left), len(right))):
        lv = left[index] if index < len(left) else 0
        rv = right[index] if index < len(right) else 0
        if lv != rv:
            return {"<": lv < rv, "<=": lv <= rv, ">": lv > rv, ">=": lv >= rv, "==": False, "!=": True}[op]
    return op in {"==", ">=", "<="}


def _numeric_version_meets_constraints(version: str, constraints: list[str]) -> bool:
    compiled = _compiled()
    version_tuple = _parse_numeric_version(version)
    re_single = compiled["re_single_version_spec"]
    for term in constraints:
        match = re_single.match(term)
        if not match:
            return False
        op = match.group(1)
        target = match.group(2)
        if not _compare_numeric(op, version_tuple, _parse_numeric_version(target)):
            return False
    return True


def _license_db_rows() -> list[dict[str, Any]]:
    return _bundle()["license_db"]


def _rows_at(positions: int | list[int]) -> list[dict[str, Any]]:
    db = _license_db_rows()
    if isinstance(positions, int):
        positions = [positions]
    return [dict(db[index - 1]) for index in positions]


def _standardize_license_components(values: list[str]) -> list[str]:
    data = _bundle()
    mapping = dict(zip(data["ispecs"], data["ospecs"]))
    return [mapping.get(value, value) for value in values]


def expand_license_spec_component_from_db(component: str) -> list[dict[str, Any]] | None:
    data = _bundle()
    compiled = _compiled()
    re_license_file = data["re_license_file"]

    if component == "Unlimited" or re.search(_posix_regex(component), re_license_file):
        return None

    component = compiled["re_license_extension"].sub("", component)

    if re.search(_re_anchor(data["re_sss"]), component):
        pos = data["tab_sss"][component]
        return _rows_at(pos)

    if re.search(_re_anchor(data["re_unversioned"]), component):
        pos = data["tab_unversioned"][component]
        return _rows_at(pos)

    pattern = _re_anchor(data["re_versioned_style_A"])
    match = re.match(_posix_regex(pattern), component)
    if match:
        version_part = match.group(2) or ""
        base = match.group(1)
        pos = data["tab_versioned_style_A"][base]
        entries = _rows_at(pos)
        version_part = re.sub(r"\s*\((.*)\)\s*", r"\1", version_part)
        if version_part:
            constraints = re.split(r"\s*,\s*", version_part)
            entries = [
                row
                for row in entries
                if _numeric_version_meets_constraints(str(row["Version"]), constraints)
            ]
        return entries

    if re.search(_re_anchor(data["re_versioned_style_B"]), component):
        inner = re.compile(
            _posix_regex(
                rf"\s+([Vv]ersion\s+)?({data['valid_numeric_version']})"
            )
        )
        component = inner.sub(r" \2", component)
        pos = data["tab_versioned_style_B"][component]
        return _rows_at(pos)

    if re.search(_re_anchor(data["re_versioned_style_C"]), component):
        pos = data["tab_versioned_style_C"][component]
        return _rows_at(pos)

    return None


def _make_results(
    *,
    is_empty: bool = False,
    is_canonical: bool = False,
    bad_components: list[str] | None = None,
    is_standardizable: bool = False,
    is_verified: bool = False,
    standardization: str | None = None,
    components: list[str] | None = None,
    expansions: list[Any] | None = None,
    extensions: list[dict[str, Any]] | None = None,
    pointers: list[str] | None = None,
    is_foss: float | bool = math.nan,
    restricts_use: float | bool = math.nan,
) -> dict[str, Any]:
    return {
        "is_empty": is_empty,
        "is_canonical": is_canonical,
        "bad_components": bad_components if bad_components is not None else [],
        "is_standardizable": is_standardizable,
        "is_verified": is_verified,
        "standardization": standardization,
        "components": components,
        "expansions": expansions,
        "extensions": extensions,
        "pointers": pointers,
        "is_FOSS": is_foss,
        "restricts_use": restricts_use,
    }


def analyze_license(x: str | None) -> dict[str, Any]:
    """Check and expand a DESCRIPTION License field specification."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return _make_results(is_empty=True)

    text = str(x).strip()
    if text == "":
        return _make_results(is_empty=True)

    pointers = None
    extensions = None
    expansions = None
    is_verified = False
    is_foss: float | bool = math.nan
    restricts_use: float | bool = math.nan

    normalized = re.sub(r"\s*\+\s*", " + ", text)
    components = [part.strip() for part in normalized.split("|")]
    components = [part for part in components if part != ""]

    compiled = _compiled()
    ok = [bool(compiled["re_component"].fullmatch(part)) for part in components]
    bad_components = [part for part, good in zip(components, ok) if not good]
    is_canonical = all(ok)

    data = _bundle()
    standardizable = [part in data["ispecs"] for part in components]
    is_standardizable = is_canonical or all(standardizable)

    standardization: str | None
    if is_standardizable:
        for index, (good, std) in enumerate(zip(ok, standardizable)):
            if not good and std:
                components[index] = _standardize_license_components([components[index]])[0]
        for index, part in enumerate(components):
            if ok[index] and "(" in part:
                segment = re.sub(r"\s*\(\s*", " (", part)
                segment = re.sub(r"\s*\)", ")", segment)
                segment = re.sub(r"\s*,\s*", ", ", segment)
                segment = re.sub(r"\s+(<=?|>=?|==|!=)", r" \1", segment)
                segment = re.sub(
                    _posix_regex(rf"\s*({data['valid_numeric_version']})"),
                    r" \1",
                    segment,
                )
                components[index] = segment
        standardization = " | ".join(components)
    else:
        standardization = None

    if is_standardizable:

        def verifiable(rows: list[dict[str, Any]] | None, value: str = "yes") -> bool:
            if rows is None:
                return False
            flags = [row.get("FOSS") for row in rows]
            return all(flag == value for flag in flags if flag is not None and flag == flag)

        raw_expansions = [expand_license_spec_component_from_db(part) for part in components]

        if any(part == "Unlimited" for part in components):
            is_foss = True
        elif any(verifiable(rows) for rows in raw_expansions):
            is_foss = True
        elif all(any(row.get("FOSS") == "no" for row in (rows or [])) for rows in raw_expansions):
            is_foss = False
        else:
            is_foss = math.nan

        is_verified = isinstance(is_foss, bool) and is_foss

        if is_verified:
            restricts_use = False
        elif any(
            rows is not None
            and len(rows) > 0
            and all(row.get("Restricts_use") == "no" for row in rows)
            for rows in raw_expansions
        ):
            restricts_use = False
        elif all(
            any(row.get("Restricts_use") == "yes" for row in (rows or []))
            for rows in raw_expansions
        ):
            restricts_use = True
        else:
            restricts_use = math.nan

        re_license = data["re_license_file"]
        end_re = re.compile(_posix_regex(rf"{re_license}$"))
        pos = [index for index, part in enumerate(components) if end_re.search(part)]
        if pos:
            elements = [components[index] for index in pos]
            pointers = [re.sub(r".*file ", "", element) for element in elements]
            plus_indices = [index for index, element in enumerate(elements) if "+" in element]
            if plus_indices:
                extensions = []
                for index in plus_indices:
                    element = elements[index]
                    source_index = pos[index]
                    rows = raw_expansions[source_index]
                    extensible = verifiable(rows, "yes") if rows else False
                    extensions.append({"components": element, "extensible": extensible})

        expansions = [[row["Labels"] for row in (rows or [])] for rows in raw_expansions]
        direct = re.compile(_posix_regex(rf"^(Unlimited|{re_license})$"))
        for index, part in enumerate(components):
            if direct.search(part):
                expansions[index] = [part]

        suffix = re.compile(_posix_regex(rf"\+ *{re_license}$"))
        for index, part in enumerate(components):
            match = suffix.search(part)
            if match:
                tail = match.group(0).lstrip()
                expansions[index] = [f"{label} {tail}" for label in expansions[index]]
            elif "+" in part and len(expansions[index]) == 1:
                expansions[index] = [part]

    if any(part.startswith("Part of R") for part in components):
        is_verified = True
        is_foss = True
        restricts_use = False

    return _make_results(
        is_canonical=is_canonical,
        bad_components=bad_components,
        is_standardizable=is_standardizable,
        standardization=standardization,
        is_verified=is_verified,
        components=components,
        expansions=expansions,
        extensions=extensions,
        pointers=pointers,
        is_foss=is_foss,
        restricts_use=restricts_use,
    )
