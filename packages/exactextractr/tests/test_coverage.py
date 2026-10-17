"""Checks taken from the exactextractr 0.10.1 tests and the man page."""

import math
import unittest

from exactextractr.coverage_fraction import coverage_fraction
from exactextractr.exact_extract import exact_extract
from exactextractr.exact_resample import exact_resample
from exactextractr.rasterize_polygons import rasterize_polygons

SQUARE = "POLYGON ((0.5 0.5, 2.5 0.5, 2.5 2.5, 0.5 2.5, 0.5 0.5))"
TRIANGLE = "POLYGON ((2 2, 7 6, 4 9, 2 2))"


def _grid(values, xmin, xmax, ymin, ymax):
    return {"values": values, "xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax}


class CoverageTests(unittest.TestCase):
    def test_axis_aligned_square(self):
        grid = {"xmin": 0, "xmax": 3, "ymin": 0, "ymax": 3, "nrows": 3, "ncols": 3}
        got = coverage_fraction(grid, SQUARE)[0]["values"]
        self.assertEqual(got, [[0.25, 0.5, 0.25], [0.5, 1.0, 0.5], [0.25, 0.5, 0.25]])

    def test_crop_shrinks_to_processed_cells(self):
        grid = {"xmin": 0, "xmax": 10, "ymin": 0, "ymax": 10, "nrows": 10, "ncols": 10}
        got = coverage_fraction(grid, SQUARE, crop=True)[0]
        self.assertEqual(got["xmin"], 0.0)
        self.assertEqual(got["xmax"], 3.0)
        self.assertEqual(got["ymin"], 0.0)
        self.assertEqual(got["ymax"], 3.0)
        self.assertEqual(got["values"], [[0.25, 0.5, 0.25], [0.5, 1.0, 0.5], [0.25, 0.5, 0.25]])

    def test_uncropped_writes_zero_outside(self):
        grid = {"xmin": 0, "xmax": 10, "ymin": 0, "ymax": 10, "nrows": 10, "ncols": 10}
        got = coverage_fraction(grid, SQUARE, crop=False)[0]
        self.assertEqual(len(got["values"]), 10)
        self.assertEqual(len(got["values"][0]), 10)
        self.assertTrue(all(cell == 0.0 or cell > 0.0 for row in got["values"] for cell in row))
        self.assertEqual(got["values"][7], [0.25, 0.5, 0.25, 0, 0, 0, 0, 0, 0, 0])


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.values = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        self.grid = _grid(self.values, 0, 3, 0, 3)

    def test_cell_table(self):
        got = exact_extract(self.grid, SQUARE)[0]
        self.assertEqual(got["value"], [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(
            got["coverage_fraction"],
            [0.25, 0.5, 0.25, 0.5, 1.0, 0.5, 0.25, 0.5, 0.25],
        )

    def test_named_stats(self):
        self.assertEqual(exact_extract(self.grid, SQUARE, "count"), [4.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "mean"), [5.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "sum"), [20.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "min"), [1.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "max"), [9.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "median"), [5.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "mode"), [5.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "majority"), [5.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "minority"), [1.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "variety"), [9.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "variance"), [5.0])
        self.assertEqual(exact_extract(self.grid, SQUARE, "stdev"), [float(np_stdev())])
        several = exact_extract(self.grid, SQUARE, ["min", "max", "mode"])
        self.assertEqual(several, [{"min": 1.0, "max": 9.0, "mode": 5.0}])

    def test_two_features(self):
        got = exact_extract(self.grid, [SQUARE, SQUARE], ["min", "max"])
        self.assertEqual(got, [{"min": 1.0, "max": 9.0}, {"min": 1.0, "max": 9.0}])

    def test_weighted_bottom_row(self):
        weights = _grid([[0, 0, 0], [0, 0, 0], [1, 1, 1]], 0, 3, 0, 3)
        got = exact_extract(self.grid, SQUARE, "weighted_mean", weights=weights)
        self.assertEqual(got, [8.0])
        got = exact_extract(self.grid, SQUARE, "weighted_sum", weights=weights)
        self.assertEqual(got, [8.0])


def np_stdev():
    import numpy as np

    return np.float32(math.sqrt(5.0))


class ResampleTests(unittest.TestCase):
    def test_identity_mean_and_sum(self):
        src = _grid([[1.0, 2.0], [3.0, 4.0]], 0, 2, 0, 2)
        dst = {"xmin": 0, "xmax": 2, "ymin": 0, "ymax": 2, "nrows": 1, "ncols": 1}
        self.assertEqual(exact_resample(src, dst, "mean")["values"], [[2.5]])
        self.assertEqual(exact_resample(src, dst, "sum")["values"], [[10.0]])


class RasterizeTests(unittest.TestCase):
    def test_index_lands_on_the_southern_cells(self):
        grid = {"xmin": 0, "xmax": 10, "ymin": 0, "ymax": 10, "nrows": 10, "ncols": 10}
        got = rasterize_polygons(SQUARE, grid)["values"]
        self.assertEqual(got[7][0:3], [1, 1, 1])
        self.assertIsNone(got[0][0])

    def test_northwest_cell_keeps_its_value(self):
        values = [[row * 4 + col + 1 for col in range(4)] for row in range(4)]
        grid = _grid(values, 0, 4, 0, 4)
        poly = "POLYGON ((0 3, 1 3, 1 4, 0 4, 0 3))"
        got = exact_extract(grid, poly)[0]
        self.assertEqual(got["value"], [1.0])
        self.assertEqual(got["coverage_fraction"], [1.0])
        located = exact_extract(grid, poly, include_xy=True, include_cell=True, include_area=True)[0]
        self.assertEqual(located["cell"], [1])
        self.assertEqual(located["x"], [0.5])
        self.assertEqual(located["y"], [3.5])
        self.assertEqual(located["area"], [1.0])

    def test_tie_keeps_first_index(self):
        left = "POLYGON ((0 0, 1 0, 1 2, 0 2, 0 0))"
        whole = "POLYGON ((0 0, 2 0, 2 2, 0 2, 0 0))"
        grid = {"xmin": 0, "xmax": 2, "ymin": 0, "ymax": 2, "nrows": 2, "ncols": 2}
        got = rasterize_polygons([left, whole], grid)
        self.assertEqual(got["values"], [[1, 2], [1, 2]])


def _box(xmin, ymin, xmax, ymax, dx, dy):
    return {
        "xmin": xmin,
        "xmax": xmax,
        "ymin": ymin,
        "ymax": ymax,
        "nrows": round((ymax - ymin) / dy),
        "ncols": round((xmax - xmin) / dx),
    }


class AlgorithmTests(unittest.TestCase):
    def _check(self, grid, wkt, expected):
        import numpy as np

        got = np.array(coverage_fraction(grid, wkt, crop=True)[0]["values"], dtype=np.float32)
        exp = np.array(expected, dtype=np.float32)
        if got.shape != exp.shape or not np.array_equal(got, exp):
            self.fail(f"\ngot\n{got}\nexpected\n{exp}")

    def test_cpp_cases(self):
        g3 = _box(0, 0, 3, 3, 1, 1)
        self._check(
            g3,
            "POLYGON ((0.5 0.5, 2.5 0.5, 2.5 2.0, 2.0 2.0, 2.0 2.5, 0.5 2.5, 0.5 0.5))",
            [[0.25, 0.5, 0.00], [0.50, 1.0, 0.50], [0.25, 0.5, 0.25]],
        )
        self._check(
            g3,
            "LINESTRING (0.5 0.5, 2.5 0.5, 2.5 2.5, 0.5 2.5)",
            [[0.50, 1.00, 1.00], [0, 0, 1.00], [0.50, 1.00, 1.00]],
        )
        self._check(
            g3,
            "POLYGON ((1.5 0.5, 2.5 1.5, 1.5 2.5, 0.5 1.5, 1.5 0.5))",
            [[0.00, 0.25, 0.00], [0.25, 1.00, 0.25], [0.00, 0.25, 0.00]],
        )
        self._check(
            _box(0, 0, 2, 2, 1, 1),
            "POLYGON ((1 1.5, 1.5 1.5, 1.5 0.5, 0.5 0.5, 0.5 1.5, 1 1.5))",
            [[0.25, 0.25], [0.25, 0.25]],
        )
        self._check(
            _box(0, -1, 2, 2, 1, 1),
            "POLYGON ((0.5 1.5, 0.5 0.5, 0.5 0, 1.5 0.5, 1.5 1.5, 0.5 1.5))",
            [[0.25, 0.25], [0.4375, 0.3125]],
        )
        self._check(
            g3,
            "POLYGON ((0.5 0.5, 2 0.5, 2 1.5, 2 2.5, 0.5 2.5, 0.5 0.5))",
            [[0.25, 0.5], [0.50, 1.0], [0.25, 0.5]],
        )
        self._check(
            _box(0, 0, 3, 5, 1, 1),
            "POLYGON ((0.5 0.2, 2.2 0.2, 2.2 0.4, 0.7 0.4, 0.7 2.2, 2.2 2.2, 2.2 0.6, 2.4 0.6, 2.4 4.8, 0.5 4.8, 0.5 0.2))",
            [
                [0.40, 0.80, 0.32],
                [0.50, 1.00, 0.40],
                [0.44, 0.80, 0.36],
                [0.20, 0.00, 0.20],
                [0.22, 0.20, 0.12],
            ],
        )
        self._check(
            _box(0, 0, 3, 4, 1, 1),
            "POLYGON ((2.5 3, 0.5 3, 0.5 3.5, 0.25 3.5, 0.25 0.5, 2.5 0.5, 2.5 3))",
            [
                [0.125, 0.00, 0.00],
                [0.750, 1.00, 0.50],
                [0.750, 1.00, 0.50],
                [0.375, 0.50, 0.25],
            ],
        )
        small = coverage_fraction(_box(0, 0, 10, 10, 10, 10), "POLYGON ((3 3, 4 3, 4 4, 3 4, 3 3))", crop=True)[0]
        import numpy as np

        self.assertEqual(np.float32(small["values"][0][0]), np.float32(0.01))
        self._check(
            g3,
            "POLYGON ((0.5 0.5, 2.5 0.5, 2.5 2.5, 0.5 2.5, 0.5 0.5), (1 1, 2 1, 2 2, 1 2, 1 1))",
            [[0.25, 0.5, 0.25], [0.5, 0.0, 0.5], [0.25, 0.5, 0.25]],
        )
        self._check(
            _box(0, 3, 3, 6, 1, 1),
            "POLYGON ((0.5 0.5, 4.5 0.5, 4.5 5.5, 0.5 5.5, 0.5 0.5))",
            [[0.25, 0.5, 0.5], [0.50, 1.0, 1.0], [0.50, 1.0, 1.0]],
        )
        outside = coverage_fraction(
            _box(-3, -3, 0, 0, 1, 1),
            "POLYGON ((1.5 0.5, 2.5 1.5, 1.5 2.5, 0.5 1.5, 1.5 0.5))",
            crop=True,
        )[0]
        self.assertEqual(outside["values"], [])
        tiny = coverage_fraction(g3, "POLYGON ((0.5 0.5, 0.6 0.5, 0.6 0.6, 0.5 0.5))", crop=True)[0]
        self.assertEqual([tiny["xmin"], tiny["xmax"], tiny["ymin"], tiny["ymax"]], [0.0, 1.0, 0.0, 1.0])
        self.assertEqual(np.float32(tiny["values"][0][0]), np.float32(0.005))

    def test_indexed_extent(self):
        got = coverage_fraction(
            _box(-20, -15, 40, 30, 0.5, 1),
            "POLYGON ((0.25 0.20, 2.75 0.20, 2.75 4.5, 0.25 4.5, 0.25 0.20))",
            crop=True,
        )[0]
        self._check(
            _box(-20, -15, 40, 30, 0.5, 1),
            "POLYGON ((0.25 0.20, 2.75 0.20, 2.75 4.5, 0.25 4.5, 0.25 0.20))",
            [
                [0.25, 0.50, 0.50, 0.50, 0.50, 0.25],
                [0.50, 1.00, 1.00, 1.00, 1.00, 0.50],
                [0.50, 1.00, 1.00, 1.00, 1.00, 0.50],
                [0.50, 1.00, 1.00, 1.00, 1.00, 0.50],
                [0.40, 0.80, 0.80, 0.80, 0.80, 0.40],
            ],
        )
        self.assertEqual(got["xmin"], 0.0)
        self.assertEqual(got["ymax"], 5.0)


class TriangleTests(unittest.TestCase):
    def test_coverage_sums_to_area(self):
        grid = {"xmin": 0, "xmax": 10, "ymin": 0, "ymax": 10, "nrows": 10, "ncols": 10}
        cov = coverage_fraction(grid, TRIANGLE, crop=True)[0]["values"]
        total = sum(cell for row in cov for cell in row)
        self.assertAlmostEqual(total, 13.5, places=5)

    def test_man_page_mean(self):
        values = [[col * 10 + row + 1 for col in range(10)] for row in range(10)]
        grid = _grid(values, 0, 10, 0, 10)
        got = exact_extract(grid, TRIANGLE, "mean")[0]
        self.assertEqual(got, 43.16666793823242)


if __name__ == "__main__":
    unittest.main()
