"""Package dependency queries from tools 4.5.0."""

import re

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9.]*")
_FIELDS = {
    "strong": ["Depends", "Imports", "LinkingTo"],
    "most": ["Depends", "Imports", "LinkingTo", "Suggests"],
    "all": ["Depends", "Imports", "LinkingTo", "Suggests", "Enhances"],
}


def expand_dependency_type_spec(spec):
    """Turn strong, most, and all into dependency field names."""
    if isinstance(spec, str) and spec in _FIELDS:
        return list(_FIELDS[spec])
    if isinstance(spec, str):
        return [spec]
    return list(spec)


def extract_dependency_package_names(values):
    """Package names inside a Depends-style string. R itself is dropped."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    names = []
    for item in values:
        if item is None:
            continue
        if isinstance(item, float) and item != item:
            continue
        text = str(item)
        if text == "NA":
            continue
        index = 0
        while True:
            match = _NAME.search(text, index)
            if not match:
                break
            name = match.group()
            index = match.end()
            cursor = index
            while cursor < len(text) and text[cursor] in " \t\n\r\f\v":
                cursor += 1
            if cursor < len(text) and text[cursor] == "(":
                depth = 0
                while cursor < len(text):
                    if text[cursor] == "(":
                        depth += 1
                    elif text[cursor] == ")":
                        depth -= 1
                        cursor += 1
                        if depth == 0:
                            break
                        continue
                    cursor += 1
                index = cursor
            if name != "R":
                names.append(name)
    return names


def _unique(values):
    seen = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def _clean(values):
    return _unique(extract_dependency_package_names(values))


def depends_on_pkgs(pkgs, dependencies="strong", recursive=True, installed=None):
    """Packages that use pkgs, optionally following the dependency graph."""
    if isinstance(pkgs, str):
        pkgs = [pkgs]
    else:
        pkgs = list(pkgs)
    fields = expand_dependency_type_spec(dependencies)
    if installed is None:
        raise ValueError("installed package table is required")
    names = [row["Package"] for row in installed]

    def users(targets):
        found = []
        for name, row in zip(names, installed):
            deps = _clean([row.get(field) for field in fields])
            if any(target in deps for target in targets):
                found.append(name)
        return found

    uses = users(pkgs)
    if recursive:
        current = list(pkgs)
        while True:
            current = _unique(current + uses)
            uses = _unique(current + users(current))
            if len(uses) <= len(current):
                break
    return [name for name in uses if name not in pkgs]


def _as_rows(db):
    if isinstance(db, dict) and "Package" in db and not isinstance(db["Package"], (str, list)):
        raise ValueError("db must be a table")
    if isinstance(db, dict):
        packages = db["Package"]
        rows = []
        for index, package in enumerate(packages):
            row = {"Package": package}
            for key, values in db.items():
                if key == "Package":
                    continue
                row[key] = values[index]
            rows.append(row)
        return rows
    return [dict(row) for row in db]


def package_dependencies(packages=None, db=None, which="strong", recursive=False, reverse=False, verbose=False):
    """Dependencies of packages, or the packages that use them when reverse is true."""
    if db is None:
        raise ValueError("db is required")
    packages1 = None if packages is None else _unique(packages if not isinstance(packages, str) else [packages])
    fields = expand_dependency_type_spec(which)
    recursive_fields = None
    if isinstance(recursive, str) or (isinstance(recursive, (list, tuple)) and recursive and isinstance(recursive[0], str) and recursive not in (True, False)):
        recursive_fields = expand_dependency_type_spec(recursive)
        if recursive_fields == fields:
            recursive = True
            recursive_fields = None
        else:
            fields = _unique(fields + recursive_fields)
    rows = _as_rows(db)
    if not isinstance(recursive, str) and recursive_fields is None and not recursive and not reverse and packages1 is not None:
        wanted = set(packages1)
        rows = [row for row in rows if row["Package"] in wanted]
        # match() keeps the db order of hits, and drops unknown. R match keeps packages1 order via later subset.
        order = {name: index for index, name in enumerate(row["Package"] for row in _as_rows(db))}
        rows = [row for row in _as_rows(db) if row["Package"] in wanted]
        rows.sort(key=lambda row: order[row["Package"]])
    else:
        seen = set()
        kept = []
        for row in rows:
            if row["Package"] not in seen:
                seen.add(row["Package"])
                kept.append(row)
        rows = kept
    for row in rows:
        for field in fields:
            value = row.get(field)
            if not isinstance(value, list):
                row[field] = extract_dependency_package_names(value)
    if recursive_fields is not None:
        direct = package_dependencies(packages, rows, which, False, reverse, verbose)
        more = package_dependencies(_unique([name for names in direct.values() for name in names]), rows, recursive_fields, True, reverse, verbose)
        out = {}
        for package, names in direct.items():
            extra = []
            for name in names:
                extra.extend(more.get(name, []))
            out[package] = sorted(_unique(names + extra))
        return out
    which_fields = expand_dependency_type_spec(which)
    depends = []
    for row in rows:
        merged = []
        for field in which_fields:
            merged.extend(row.get(field, []))
        depends.append(_unique(merged))
    if not recursive and not reverse:
        result = {row["Package"]: names for row, names in zip(rows, depends)}
        if packages1 is not None:
            return {package: result.get(package, []) for package in (packages if isinstance(packages, list) else [packages])}
        return result
    all_packages = sorted(_unique([row["Package"] for row in rows] + [name for names in depends for name in names]))
    if not recursive:
        grouped = {name: [] for name in all_packages}
        for row, names in zip(rows, depends):
            for name in names:
                grouped.setdefault(name, []).append(row["Package"])
        if packages is None:
            return {name: grouped.get(name, []) for name in all_packages}
        wanted = packages if isinstance(packages, list) else [packages]
        return {package: grouped.get(package, []) for package in wanted}
    index = {name: pos for pos, name in enumerate(all_packages)}
    edges = {}
    for row, names in zip(rows, depends):
        src = index[row["Package"]]
        edges[src] = [index[name] for name in names if name in index]
    if packages1 is None:
        if reverse:
            packages1 = list(all_packages)
            starts = list(range(len(all_packages)))
        else:
            packages1 = [row["Package"] for row in rows]
            starts = [index[name] for name in packages1]
    else:
        starts = [index[name] for name in packages1 if name in index]
    if reverse:
        flipped = {pos: [] for pos in range(len(all_packages))}
        for src, dests in edges.items():
            for dest in dests:
                flipped[dest].append(src)
        edges = flipped
    pos = []
    for start in starts:
        for dest in edges.get(start, []):
            pos.append((start, dest))
    seen = set(pos)
    while True:
        added = []
        by_dest = {}
        for src, dest in pos:
            by_dest.setdefault(dest, []).append(src)
        for dest, sources in by_dest.items():
            for nxt in edges.get(dest, []):
                for src in sources:
                    pair = (src, nxt)
                    if pair not in seen:
                        seen.add(pair)
                        added.append(pair)
        if not added:
            break
        pos.extend(added)
    grouped = {name: [] for name in packages1}
    for src, dest in pos:
        package = all_packages[src]
        if package in grouped:
            dep = all_packages[dest]
            if dep not in grouped[package]:
                grouped[package].append(dep)
    if packages is None:
        return {name: grouped.get(name, []) for name in packages1}
    wanted = packages if isinstance(packages, list) else [packages]
    return {package: grouped.get(package, []) for package in wanted}
