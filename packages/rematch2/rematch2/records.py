"""The $ selectors for rematch_records and rematch_allrecords."""


def dollar_rematch_records(x, name):
    """Pull match, start, or end from each first-match record."""
    if name not in ("match", "start", "end"):
        raise ValueError("'$' match selector must refer to 'match', 'start' or 'end'")
    return [row[name] for row in x.rows]


def dollar_rematch_allrecords(x, name):
    """Pull match, start, or end from each all-match record."""
    if name not in ("match", "start", "end"):
        raise ValueError("'$' match selector must refer to 'match', 'start' or 'end'")
    return [row[name] for row in x.rows]


class RematchRecords:
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getattr__(self, name):
        if name in ("match", "start", "end"):
            return dollar_rematch_records(self, name)
        raise AttributeError(name)


class RematchAllRecords:
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getattr__(self, name):
        if name in ("match", "start", "end"):
            return dollar_rematch_allrecords(self, name)
        raise AttributeError(name)
