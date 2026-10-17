"""GEOS 3.13.1 through ``libgeos_c.so.1``.

Pointers use ``c_void_p``. The default restype of ``c_int`` would truncate them.
"""

from __future__ import annotations

import ctypes

from ._grid import Box

_LIB = "/usr/lib/x86_64-linux-gnu/libgeos_c.so.1"

GEOS_POINT = 0
GEOS_LINESTRING = 1
GEOS_LINEARRING = 2
GEOS_POLYGON = 3
GEOS_MULTIPOINT = 4
GEOS_MULTILINESTRING = 5
GEOS_MULTIPOLYGON = 6
GEOS_GEOMETRYCOLLECTION = 7

_P = ctypes.c_void_p


class GEOSError(RuntimeError):
    pass


class Geom:
    """A GEOS geometry. Borrowed rings are not destroyed."""

    def __init__(self, ctx: "Context", ptr: int | None, owned: bool) -> None:
        self.ctx = ctx
        self.ptr = ptr
        self.owned = owned

    def close(self) -> None:
        if self.owned and self.ptr:
            self.ctx.lib.GEOSGeom_destroy_r(self.ctx.handle, self.ptr)
            self.ptr = None
            self.owned = False

    def __del__(self) -> None:
        self.close()


class Prepared:
    def __init__(self, ctx: "Context", polygon: Geom, prepared) -> None:
        self.ctx = ctx
        self.polygon = polygon
        self.prepared = prepared

    def contains(self, x: float, y: float) -> bool:
        point = self.ctx.lib.GEOSGeom_createPointFromXY_r(self.ctx.handle, x, y)
        if not point:
            raise GEOSError("GEOSGeom_createPointFromXY_r failed")
        try:
            code = self.ctx.lib.GEOSPreparedContains_r(self.ctx.handle, self.prepared, point)
        finally:
            self.ctx.lib.GEOSGeom_destroy_r(self.ctx.handle, point)
        if code == 2:
            raise GEOSError("GEOSPreparedContains_r failed")
        return code == 1

    def close(self) -> None:
        if self.prepared:
            self.ctx.lib.GEOSPreparedGeom_destroy_r(self.ctx.handle, self.prepared)
            self.prepared = None
        self.polygon.close()

    def __del__(self) -> None:
        self.close()


class Context:
    def __init__(self) -> None:
        self.lib = ctypes.CDLL(_LIB)
        self._bind()
        self.handle = self.lib.GEOS_init_r()
        if not self.handle:
            raise GEOSError("GEOS_init_r failed")

    def _bind(self) -> None:
        lib = self.lib
        lib.GEOS_init_r.argtypes = []
        lib.GEOS_init_r.restype = _P
        lib.GEOS_finish_r.argtypes = [_P]
        lib.GEOS_finish_r.restype = None

        lib.GEOSGeomFromWKT_r.argtypes = [_P, ctypes.c_char_p]
        lib.GEOSGeomFromWKT_r.restype = _P
        lib.GEOSGeom_destroy_r.argtypes = [_P, _P]
        lib.GEOSGeom_destroy_r.restype = None

        lib.GEOSisEmpty_r.argtypes = [_P, _P]
        lib.GEOSisEmpty_r.restype = ctypes.c_byte
        lib.GEOSGeom_getDimensions_r.argtypes = [_P, _P]
        lib.GEOSGeom_getDimensions_r.restype = ctypes.c_int
        lib.GEOSGeomTypeId_r.argtypes = [_P, _P]
        lib.GEOSGeomTypeId_r.restype = ctypes.c_int

        lib.GEOSGetExteriorRing_r.argtypes = [_P, _P]
        lib.GEOSGetExteriorRing_r.restype = _P
        lib.GEOSGetNumInteriorRings_r.argtypes = [_P, _P]
        lib.GEOSGetNumInteriorRings_r.restype = ctypes.c_int
        lib.GEOSGetInteriorRingN_r.argtypes = [_P, _P, ctypes.c_int]
        lib.GEOSGetInteriorRingN_r.restype = _P

        lib.GEOSGetNumGeometries_r.argtypes = [_P, _P]
        lib.GEOSGetNumGeometries_r.restype = ctypes.c_int
        lib.GEOSGetGeometryN_r.argtypes = [_P, _P, ctypes.c_int]
        lib.GEOSGetGeometryN_r.restype = _P

        lib.GEOSGeom_getCoordSeq_r.argtypes = [_P, _P]
        lib.GEOSGeom_getCoordSeq_r.restype = _P
        lib.GEOSCoordSeq_getSize_r.argtypes = [_P, _P, ctypes.POINTER(ctypes.c_uint)]
        lib.GEOSCoordSeq_getSize_r.restype = ctypes.c_int
        lib.GEOSCoordSeq_copyToBuffer_r.argtypes = [
            _P,
            _P,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.c_int,
        ]
        lib.GEOSCoordSeq_copyToBuffer_r.restype = ctypes.c_int
        lib.GEOSCoordSeq_isCCW_r.argtypes = [_P, _P, ctypes.POINTER(ctypes.c_byte)]
        lib.GEOSCoordSeq_isCCW_r.restype = ctypes.c_int

        for name in (
            "GEOSGeom_getXMin_r",
            "GEOSGeom_getYMin_r",
            "GEOSGeom_getXMax_r",
            "GEOSGeom_getYMax_r",
        ):
            fn = getattr(lib, name)
            fn.argtypes = [_P, _P, ctypes.POINTER(ctypes.c_double)]
            fn.restype = ctypes.c_int

        lib.GEOSGeom_clone_r.argtypes = [_P, _P]
        lib.GEOSGeom_clone_r.restype = _P
        lib.GEOSGeom_createPolygon_r.argtypes = [_P, _P, _P, ctypes.c_uint]
        lib.GEOSGeom_createPolygon_r.restype = _P
        lib.GEOSPrepare_r.argtypes = [_P, _P]
        lib.GEOSPrepare_r.restype = _P
        lib.GEOSPreparedGeom_destroy_r.argtypes = [_P, _P]
        lib.GEOSPreparedGeom_destroy_r.restype = None
        lib.GEOSPreparedContains_r.argtypes = [_P, _P, _P]
        lib.GEOSPreparedContains_r.restype = ctypes.c_byte
        lib.GEOSGeom_createPointFromXY_r.argtypes = [_P, ctypes.c_double, ctypes.c_double]
        lib.GEOSGeom_createPointFromXY_r.restype = _P

    def from_wkt(self, wkt: str) -> Geom:
        ptr = self.lib.GEOSGeomFromWKT_r(self.handle, wkt.encode("utf-8"))
        if not ptr:
            raise GEOSError("invalid WKT")
        return Geom(self, ptr, True)

    def _borrow(self, ptr) -> Geom:
        if not ptr:
            raise GEOSError("GEOS returned a null geometry")
        return Geom(self, ptr, False)

    def is_empty(self, geom: Geom) -> bool:
        code = self.lib.GEOSisEmpty_r(self.handle, geom.ptr)
        if code == 2:
            raise GEOSError("GEOSisEmpty_r failed")
        return code == 1

    def dimensions(self, geom: Geom) -> int:
        return int(self.lib.GEOSGeom_getDimensions_r(self.handle, geom.ptr))

    def type_id(self, geom: Geom) -> int:
        return int(self.lib.GEOSGeomTypeId_r(self.handle, geom.ptr))

    def exterior_ring(self, geom: Geom) -> Geom:
        return self._borrow(self.lib.GEOSGetExteriorRing_r(self.handle, geom.ptr))

    def num_interior_rings(self, geom: Geom) -> int:
        return int(self.lib.GEOSGetNumInteriorRings_r(self.handle, geom.ptr))

    def interior_ring(self, geom: Geom, index: int) -> Geom:
        return self._borrow(self.lib.GEOSGetInteriorRingN_r(self.handle, geom.ptr, index))

    def num_geometries(self, geom: Geom) -> int:
        return int(self.lib.GEOSGetNumGeometries_r(self.handle, geom.ptr))

    def geometry_n(self, geom: Geom, index: int) -> Geom:
        return self._borrow(self.lib.GEOSGetGeometryN_r(self.handle, geom.ptr, index))

    def box(self, geom: Geom) -> Box:
        xmin = ctypes.c_double()
        ymin = ctypes.c_double()
        xmax = ctypes.c_double()
        ymax = ctypes.c_double()
        ok = (
            self.lib.GEOSGeom_getXMin_r(self.handle, geom.ptr, ctypes.byref(xmin))
            and self.lib.GEOSGeom_getYMin_r(self.handle, geom.ptr, ctypes.byref(ymin))
            and self.lib.GEOSGeom_getXMax_r(self.handle, geom.ptr, ctypes.byref(xmax))
            and self.lib.GEOSGeom_getYMax_r(self.handle, geom.ptr, ctypes.byref(ymax))
        )
        if not ok:
            raise GEOSError("Error getting geometry extent.")
        return Box(xmin.value, ymin.value, xmax.value, ymax.value)

    def component_boxes(self, geom: Geom) -> list[Box]:
        count = self.num_geometries(geom)
        return [self.box(self.geometry_n(geom, i)) for i in range(count)]

    def _coord_seq(self, geom: Geom):
        seq = self.lib.GEOSGeom_getCoordSeq_r(self.handle, geom.ptr)
        if not seq:
            raise GEOSError("geometry has no coordinate sequence")
        return seq

    def read_coords(self, geom: Geom) -> list[tuple[float, float]]:
        seq = self._coord_seq(geom)
        size = ctypes.c_uint()
        if not self.lib.GEOSCoordSeq_getSize_r(self.handle, seq, ctypes.byref(size)):
            raise GEOSError("Error calling GEOSCoordSeq_getSize.")
        n = int(size.value)
        buf = (ctypes.c_double * (n * 2))()
        if not self.lib.GEOSCoordSeq_copyToBuffer_r(
            self.handle, seq, ctypes.cast(buf, ctypes.POINTER(ctypes.c_double)), 0, 0
        ):
            raise GEOSError("Error reading coordinates.")
        return [(buf[2 * i], buf[2 * i + 1]) for i in range(n)]

    def is_ccw(self, geom: Geom) -> bool:
        seq = self._coord_seq(geom)
        result = ctypes.c_byte()
        if not self.lib.GEOSCoordSeq_isCCW_r(self.handle, seq, ctypes.byref(result)):
            raise GEOSError("Error calling GEOSCoordSeq_isCCW_r.")
        return result.value != 0

    def prepare_ring(self, ring: Geom) -> Prepared:
        clone = self.lib.GEOSGeom_clone_r(self.handle, ring.ptr)
        if not clone:
            raise GEOSError("GEOSGeom_clone_r failed")
        polygon = self.lib.GEOSGeom_createPolygon_r(self.handle, clone, None, 0)
        if not polygon:
            raise GEOSError("GEOSGeom_createPolygon_r failed")
        prepared = self.lib.GEOSPrepare_r(self.handle, polygon)
        if not prepared:
            self.lib.GEOSGeom_destroy_r(self.handle, polygon)
            raise GEOSError("GEOSPrepare_r failed")
        return Prepared(self, Geom(self, polygon, True), prepared)


_CONTEXT: Context | None = None


def geos() -> Context:
    global _CONTEXT
    if _CONTEXT is None:
        _CONTEXT = Context()
    return _CONTEXT
