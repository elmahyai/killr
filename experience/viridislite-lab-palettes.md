# ViridisLite palettes

viridisLite's palette functions interpolate the bundled 256-colour maps with
`grDevices::colorRamp(..., space = "Lab", interpolate = "spline")`; the map
table itself contains eight options, A through H, with 256 rows each.
