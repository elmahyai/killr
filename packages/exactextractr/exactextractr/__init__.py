"""Python translation of the R package exactextractr."""

from exactextractr.coverage_fraction import coverage_fraction
from exactextractr.exact_extract import exact_extract
from exactextractr.exact_resample import exact_resample
from exactextractr.rasterize_polygons import rasterize_polygons

__all__ = [
    "coverage_fraction",
    "exact_extract",
    "exact_resample",
    "rasterize_polygons",
]
