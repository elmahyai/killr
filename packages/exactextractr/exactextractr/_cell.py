"""Cell traversals and covered-fraction areas.

This is ``cell.cpp``, ``traversal.cpp``, ``measures.cpp``,
``perimeter_distance.cpp``, and ``traversal_areas.cpp``.
"""

from __future__ import annotations

import math
import sys

from ._grid import (
    SIDE_BOTTOM,
    SIDE_LEFT,
    SIDE_NONE,
    SIDE_RIGHT,
    SIDE_TOP,
    Box,
)


class Coordinate:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance(self, other: "Coordinate") -> float:
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx * dx + dy * dy)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Coordinate):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __repr__(self) -> str:
        return f"Coordinate({self.x}, {self.y})"


class Traversal:
    def __init__(self) -> None:
        self.coords: list[Coordinate] = []
        self.entry = SIDE_NONE
        self.exit_side = SIDE_NONE

    def add(self, coord: Coordinate) -> None:
        self.coords.append(coord)

    def empty(self) -> bool:
        return not self.coords

    def enter(self, coord: Coordinate, side: int) -> None:
        if self.coords:
            raise RuntimeError("Traversal already started")
        self.add(coord)
        self.entry = side

    def exit(self, coord: Coordinate, side: int) -> None:
        self.add(coord)
        self.exit_side = side

    def is_closed_ring(self) -> bool:
        return len(self.coords) >= 3 and self.coords[0] == self.coords[-1]

    def entered(self) -> bool:
        return self.entry != SIDE_NONE

    def exited(self) -> bool:
        return self.exit_side != SIDE_NONE

    def multiple_unique_coordinates(self) -> bool:
        first = self.coords[0]
        for i in range(1, len(self.coords)):
            if first != self.coords[i]:
                return True
        return False

    def traversed(self) -> bool:
        return self.entered() and self.exited()

    def last_coordinate(self) -> Coordinate:
        return self.coords[-1]

    def exit_coordinate(self) -> Coordinate:
        if not self.exited():
            raise RuntimeError("Can't get exit coordinate from incomplete traversal.")
        return self.last_coordinate()

    def force_exit(self, side: int) -> None:
        self.exit_side = side


_INSIDE = 0
_OUTSIDE = 1
_BOUNDARY = 2


class Cell:
    def __init__(self, box: Box) -> None:
        self.box = box
        self.traversals: list[Traversal] = []

    def area(self) -> float:
        return self.box.area()

    def _side(self, coord: Coordinate) -> int:
        return self.box.side(coord.x, coord.y)

    def _location(self, coord: Coordinate) -> int:
        if self.box.strictly_contains(coord.x, coord.y):
            return _INSIDE
        if self.box.contains_coord(coord.x, coord.y):
            return _BOUNDARY
        return _OUTSIDE

    def _traversal_in_progress(self) -> Traversal:
        if not self.traversals or self.traversals[-1].exited():
            self.traversals.append(Traversal())
        return self.traversals[-1]

    def last_traversal(self) -> Traversal:
        return self.traversals[-1]

    def force_exit(self) -> None:
        if self.last_traversal().exited():
            return
        last = self.last_traversal().last_coordinate()
        if self._location(last) == _BOUNDARY:
            self.last_traversal().force_exit(self._side(last))

    def take(self, coord: Coordinate, prev_original: Coordinate | None = None) -> bool:
        traversal = self._traversal_in_progress()
        if traversal.empty():
            traversal.enter(coord, self._side(coord))
            return True
        if self._location(coord) != _OUTSIDE:
            traversal.add(coord)
            return True
        if prev_original is not None:
            side, x, y = self.box.crossing(prev_original.x, prev_original.y, coord.x, coord.y)
        else:
            last = traversal.last_coordinate()
            side, x, y = self.box.crossing(last.x, last.y, coord.x, coord.y)
        traversal.exit(Coordinate(x, y), side)
        return False

    def traversal_length(self) -> float:
        total = 0.0
        for traversal in self.traversals:
            total += length(traversal.coords)
        return total

    def covered_fraction(self) -> float:
        if len(self.traversals) == 1 and self.traversals[0].is_closed_ring():
            return area(self.traversals[0].coords) / self.area()
        lists: list[list[Coordinate]] = []
        for traversal in self.traversals:
            if not traversal.traversed() or not traversal.multiple_unique_coordinates():
                continue
            lists.append(traversal.coords)
        return left_hand_area(self.box, lists) / self.area()


def area_signed(ring: list[Coordinate]) -> float:
    if len(ring) < 3:
        return 0.0
    total = 0.0
    x0 = ring[0].x
    for i in range(1, len(ring) - 1):
        x = ring[i].x - x0
        y1 = ring[i + 1].y
        y2 = ring[i - 1].y
        total += x * (y2 - y1)
    return total / 2.0


def area(ring: list[Coordinate]) -> float:
    return abs(area_signed(ring))


def length(coords: list[Coordinate]) -> float:
    total = 0.0
    for i in range(1, len(coords)):
        total += coords[i - 1].distance(coords[i])
    return total


def perimeter_distance(box: Box, x: float, y: float) -> float:
    if x == box.xmin:
        return y - box.ymin
    if y == box.ymax:
        return (box.ymax - box.ymin) + x - box.xmin
    if x == box.xmax:
        return (box.xmax - box.xmin) + (box.ymax - box.ymin) + box.ymax - y
    if y == box.ymin:
        return (box.xmax - box.xmin) + 2.0 * (box.ymax - box.ymin) + (box.xmax - x)
    raise RuntimeError("Never get here")


def perimeter_distance_ccw(measure1: float, measure2: float, perimeter: float) -> float:
    if measure2 <= measure1:
        return measure1 - measure2
    return perimeter + measure1 - measure2


class _Chain:
    def __init__(self, start: float, stop: float, coordinates: list[Coordinate]) -> None:
        self.start = start
        self.stop = stop
        self.coordinates = coordinates
        self.visited = False


def _next_chain(chains: list[_Chain], chain: _Chain, kill: _Chain, perimeter: float) -> _Chain | None:
    best: _Chain | None = None
    best_distance = sys.float_info.max
    for candidate in chains:
        if candidate.visited and candidate is not kill:
            continue
        distance = perimeter_distance_ccw(chain.stop, candidate.start, perimeter)
        if distance < best_distance:
            best_distance = distance
            best = candidate
    return best


def left_hand_area(box: Box, coord_lists: list[list[Coordinate]]) -> float:
    chains: list[_Chain] = []
    for coords in coord_lists:
        start = perimeter_distance(box, coords[0].x, coords[0].y)
        stop = perimeter_distance(box, coords[-1].x, coords[-1].y)
        chains.append(_Chain(start, stop, coords))

    height = box.height()
    width = box.width()
    perimeter = box.perimeter()
    bottom_left = [Coordinate(box.xmin, box.ymin)]
    top_left = [Coordinate(box.xmin, box.ymax)]
    top_right = [Coordinate(box.xmax, box.ymax)]
    bottom_right = [Coordinate(box.xmax, box.ymin)]
    chains.append(_Chain(0.0, 0.0, bottom_left))
    chains.append(_Chain(height, height, top_left))
    chains.append(_Chain(height + width, height + width, top_right))
    chains.append(_Chain(2.0 * height + width, 2.0 * height + width, bottom_right))

    total = 0.0
    for chain_ref in chains:
        if chain_ref.visited or len(chain_ref.coordinates) == 1:
            continue
        coords: list[Coordinate] = []
        chain = chain_ref
        first = chain
        while True:
            chain.visited = True
            coords.extend(chain.coordinates)
            nxt = _next_chain(chains, chain, first, perimeter)
            if nxt is None:
                raise RuntimeError("Never get here")
            chain = nxt
            if chain is first:
                break
        coords.append(coords[0])
        total += area(coords)
    return total
