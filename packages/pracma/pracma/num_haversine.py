"""Haversine distance on a sphere."""

from __future__ import annotations

import math
import re

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, r_length

_COORD = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d*)\s*(\w?)\s*$")


def _check_coords(text):
    match = _COORD.match(str(text))
    if match is None:
        raise PracmaError("Coordinate input not in correct format.")
    degrees = float(match.group(1))
    minutes = float(match.group(2))
    seconds_text = match.group(3)
    if seconds_text == "":
        raise PracmaError("missing value where TRUE/FALSE needed")
    seconds = float(seconds_text)
    if degrees > 180 or minutes >= 60 or seconds >= 60 or math.isnan(seconds):
        raise PracmaError("Coordinate input not in correct format.")
    value = degrees + minutes / 60.0 + seconds / 3600.0
    letter = match.group(4)
    if letter in ("S", "W"):
        value = -value
    elif letter not in ("N", "E"):
        raise PracmaError("Coordinate input not in correct format.")
    return value


def _location(loc, numeric_message):
    if isinstance(loc, str):
        parts = loc.split(",")
        if len(parts) < 2:
            raise PracmaError("Coordinate input not in correct format.")
        lat = _check_coords(parts[0]) * math.pi / 180.0
        lon = _check_coords(parts[1]) * math.pi / 180.0
        return lat, lon
    if is_r_numeric(loc):
        values = np.asarray(loc, dtype=float).reshape(-1)
        if values.size != 2:
            raise PracmaError("Coordinate input not in correct format.")
        lat, lon = float(values[0]), float(values[1])
        if abs(lat) > 90 or abs(lon) > 180:
            raise PracmaError("Coordinate input not in correct format.")
        return lat * math.pi / 180.0, lon * math.pi / 180.0
    raise PracmaError(numeric_message)


def haversine(loc1, loc2, R=6371.0):
    lat1, lon1 = _location(loc1, "Location must be given as string 'lat lon'.")
    lat2, lon2 = _location(loc2, "Location must be given as string 'lat, lon'.")
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return float(R) * c
