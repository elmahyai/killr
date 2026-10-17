"""ColorBrewer palettes from RColorBrewer 1.1-3 (R/ColorBrewer.R)."""

import math
import numbers
import warnings


class BrewerPalError(Exception):
    """R stop() from brewer.pal."""


class BrewerPalWarning(UserWarning):
    """R warning() from brewer.pal."""


_MIN_WARNING = (
    "minimal value for n is 3, returning requested palette with 3 different levels\n"
)

# Rows are the palettes for n = 3, 4, ... . The selected row is trunc(n) - 3.
_PALETTES = {
    "Accent": (
        ("#7FC97F", "#BEAED4", "#FDC086"),
        ("#7FC97F", "#BEAED4", "#FDC086", "#FFFF99"),
        ("#7FC97F", "#BEAED4", "#FDC086", "#FFFF99", "#386CB0"),
        ("#7FC97F", "#BEAED4", "#FDC086", "#FFFF99", "#386CB0", "#F0027F"),
        ("#7FC97F", "#BEAED4", "#FDC086", "#FFFF99", "#386CB0", "#F0027F", "#BF5B17"),
        ("#7FC97F", "#BEAED4", "#FDC086", "#FFFF99", "#386CB0", "#F0027F", "#BF5B17", "#666666"),
    ),
    "Blues": (
        ("#DEEBF7", "#9ECAE1", "#3182BD"),
        ("#EFF3FF", "#BDD7E7", "#6BAED6", "#2171B5"),
        ("#EFF3FF", "#BDD7E7", "#6BAED6", "#3182BD", "#08519C"),
        ("#EFF3FF", "#C6DBEF", "#9ECAE1", "#6BAED6", "#3182BD", "#08519C"),
        ("#EFF3FF", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#084594"),
        ("#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#084594"),
        ("#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#08519C", "#08306B"),
    ),
    "BrBG": (
        ("#D8B365", "#F5F5F5", "#5AB4AC"),
        ("#A6611A", "#DFC27D", "#80CDC1", "#018571"),
        ("#A6611A", "#DFC27D", "#F5F5F5", "#80CDC1", "#018571"),
        ("#8C510A", "#D8B365", "#F6E8C3", "#C7EAE5", "#5AB4AC", "#01665E"),
        ("#8C510A", "#D8B365", "#F6E8C3", "#F5F5F5", "#C7EAE5", "#5AB4AC", "#01665E"),
        ("#8C510A", "#BF812D", "#DFC27D", "#F6E8C3", "#C7EAE5", "#80CDC1", "#35978F", "#01665E"),
        ("#8C510A", "#BF812D", "#DFC27D", "#F6E8C3", "#F5F5F5", "#C7EAE5", "#80CDC1", "#35978F", "#01665E"),
        ("#543005", "#8C510A", "#BF812D", "#DFC27D", "#F6E8C3", "#C7EAE5", "#80CDC1", "#35978F", "#01665E", "#003C30"),
        ("#543005", "#8C510A", "#BF812D", "#DFC27D", "#F6E8C3", "#F5F5F5", "#C7EAE5", "#80CDC1", "#35978F", "#01665E", "#003C30"),
    ),
    "BuGn": (
        ("#E5F5F9", "#99D8C9", "#2CA25F"),
        ("#EDF8FB", "#B2E2E2", "#66C2A4", "#238B45"),
        ("#EDF8FB", "#B2E2E2", "#66C2A4", "#2CA25F", "#006D2C"),
        ("#EDF8FB", "#CCECE6", "#99D8C9", "#66C2A4", "#2CA25F", "#006D2C"),
        ("#EDF8FB", "#CCECE6", "#99D8C9", "#66C2A4", "#41AE76", "#238B45", "#005824"),
        ("#F7FCFD", "#E5F5F9", "#CCECE6", "#99D8C9", "#66C2A4", "#41AE76", "#238B45", "#005824"),
        ("#F7FCFD", "#E5F5F9", "#CCECE6", "#99D8C9", "#66C2A4", "#41AE76", "#238B45", "#006D2C", "#00441B"),
    ),
    "BuPu": (
        ("#E0ECF4", "#9EBCDA", "#8856A7"),
        ("#EDF8FB", "#B3CDE3", "#8C96C6", "#88419D"),
        ("#EDF8FB", "#B3CDE3", "#8C96C6", "#8856A7", "#810F7C"),
        ("#EDF8FB", "#BFD3E6", "#9EBCDA", "#8C96C6", "#8856A7", "#810F7C"),
        ("#EDF8FB", "#BFD3E6", "#9EBCDA", "#8C96C6", "#8C6BB1", "#88419D", "#6E016B"),
        ("#F7FCFD", "#E0ECF4", "#BFD3E6", "#9EBCDA", "#8C96C6", "#8C6BB1", "#88419D", "#6E016B"),
        ("#F7FCFD", "#E0ECF4", "#BFD3E6", "#9EBCDA", "#8C96C6", "#8C6BB1", "#88419D", "#810F7C", "#4D004B"),
    ),
    "Dark2": (
        ("#1B9E77", "#D95F02", "#7570B3"),
        ("#1B9E77", "#D95F02", "#7570B3", "#E7298A"),
        ("#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E"),
        ("#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E", "#E6AB02"),
        ("#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E", "#E6AB02", "#A6761D"),
        ("#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E", "#E6AB02", "#A6761D", "#666666"),
    ),
    "GnBu": (
        ("#E0F3DB", "#A8DDB5", "#43A2CA"),
        ("#F0F9E8", "#BAE4BC", "#7BCCC4", "#2B8CBE"),
        ("#F0F9E8", "#BAE4BC", "#7BCCC4", "#43A2CA", "#0868AC"),
        ("#F0F9E8", "#CCEBC5", "#A8DDB5", "#7BCCC4", "#43A2CA", "#0868AC"),
        ("#F0F9E8", "#CCEBC5", "#A8DDB5", "#7BCCC4", "#4EB3D3", "#2B8CBE", "#08589E"),
        ("#F7FCF0", "#E0F3DB", "#CCEBC5", "#A8DDB5", "#7BCCC4", "#4EB3D3", "#2B8CBE", "#08589E"),
        ("#F7FCF0", "#E0F3DB", "#CCEBC5", "#A8DDB5", "#7BCCC4", "#4EB3D3", "#2B8CBE", "#0868AC", "#084081"),
    ),
    "Greens": (
        ("#E5F5E0", "#A1D99B", "#31A354"),
        ("#EDF8E9", "#BAE4B3", "#74C476", "#238B45"),
        ("#EDF8E9", "#BAE4B3", "#74C476", "#31A354", "#006D2C"),
        ("#EDF8E9", "#C7E9C0", "#A1D99B", "#74C476", "#31A354", "#006D2C"),
        ("#EDF8E9", "#C7E9C0", "#A1D99B", "#74C476", "#41AB5D", "#238B45", "#005A32"),
        ("#F7FCF5", "#E5F5E0", "#C7E9C0", "#A1D99B", "#74C476", "#41AB5D", "#238B45", "#005A32"),
        ("#F7FCF5", "#E5F5E0", "#C7E9C0", "#A1D99B", "#74C476", "#41AB5D", "#238B45", "#006D2C", "#00441B"),
    ),
    "Greys": (
        ("#F0F0F0", "#BDBDBD", "#636363"),
        ("#F7F7F7", "#CCCCCC", "#969696", "#525252"),
        ("#F7F7F7", "#CCCCCC", "#969696", "#636363", "#252525"),
        ("#F7F7F7", "#D9D9D9", "#BDBDBD", "#969696", "#636363", "#252525"),
        ("#F7F7F7", "#D9D9D9", "#BDBDBD", "#969696", "#737373", "#525252", "#252525"),
        ("#FFFFFF", "#F0F0F0", "#D9D9D9", "#BDBDBD", "#969696", "#737373", "#525252", "#252525"),
        ("#FFFFFF", "#F0F0F0", "#D9D9D9", "#BDBDBD", "#969696", "#737373", "#525252", "#252525", "#000000"),
    ),
    "Oranges": (
        ("#FEE6CE", "#FDAE6B", "#E6550D"),
        ("#FEEDDE", "#FDBE85", "#FD8D3C", "#D94701"),
        ("#FEEDDE", "#FDBE85", "#FD8D3C", "#E6550D", "#A63603"),
        ("#FEEDDE", "#FDD0A2", "#FDAE6B", "#FD8D3C", "#E6550D", "#A63603"),
        ("#FEEDDE", "#FDD0A2", "#FDAE6B", "#FD8D3C", "#F16913", "#D94801", "#8C2D04"),
        ("#FFF5EB", "#FEE6CE", "#FDD0A2", "#FDAE6B", "#FD8D3C", "#F16913", "#D94801", "#8C2D04"),
        ("#FFF5EB", "#FEE6CE", "#FDD0A2", "#FDAE6B", "#FD8D3C", "#F16913", "#D94801", "#A63603", "#7F2704"),
    ),
    "OrRd": (
        ("#FEE8C8", "#FDBB84", "#E34A33"),
        ("#FEF0D9", "#FDCC8A", "#FC8D59", "#D7301F"),
        ("#FEF0D9", "#FDCC8A", "#FC8D59", "#E34A33", "#B30000"),
        ("#FEF0D9", "#FDD49E", "#FDBB84", "#FC8D59", "#E34A33", "#B30000"),
        ("#FEF0D9", "#FDD49E", "#FDBB84", "#FC8D59", "#EF6548", "#D7301F", "#990000"),
        ("#FFF7EC", "#FEE8C8", "#FDD49E", "#FDBB84", "#FC8D59", "#EF6548", "#D7301F", "#990000"),
        ("#FFF7EC", "#FEE8C8", "#FDD49E", "#FDBB84", "#FC8D59", "#EF6548", "#D7301F", "#B30000", "#7F0000"),
    ),
    "Paired": (
        ("#A6CEE3", "#1F78B4", "#B2DF8A"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#E31A1C"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#E31A1C", "#FDBF6F"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#E31A1C", "#FDBF6F", "#FF7F00"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#E31A1C", "#FDBF6F", "#FF7F00", "#CAB2D6"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#E31A1C", "#FDBF6F", "#FF7F00", "#CAB2D6", "#6A3D9A"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#E31A1C", "#FDBF6F", "#FF7F00", "#CAB2D6", "#6A3D9A", "#FFFF99"),
        ("#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#E31A1C", "#FDBF6F", "#FF7F00", "#CAB2D6", "#6A3D9A", "#FFFF99", "#B15928"),
    ),
    "Pastel1": (
        ("#FBB4AE", "#B3CDE3", "#CCEBC5"),
        ("#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4"),
        ("#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6"),
        ("#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6", "#FFFFCC"),
        ("#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6", "#FFFFCC", "#E5D8BD"),
        ("#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6", "#FFFFCC", "#E5D8BD", "#FDDAEC"),
        ("#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6", "#FFFFCC", "#E5D8BD", "#FDDAEC", "#F2F2F2"),
    ),
    "Pastel2": (
        ("#B3E2CD", "#FDCDAC", "#CBD5E8"),
        ("#B3E2CD", "#FDCDAC", "#CBD5E8", "#F4CAE4"),
        ("#B3E2CD", "#FDCDAC", "#CBD5E8", "#F4CAE4", "#E6F5C9"),
        ("#B3E2CD", "#FDCDAC", "#CBD5E8", "#F4CAE4", "#E6F5C9", "#FFF2AE"),
        ("#B3E2CD", "#FDCDAC", "#CBD5E8", "#F4CAE4", "#E6F5C9", "#FFF2AE", "#F1E2CC"),
        ("#B3E2CD", "#FDCDAC", "#CBD5E8", "#F4CAE4", "#E6F5C9", "#FFF2AE", "#F1E2CC", "#CCCCCC"),
    ),
    "PiYG": (
        ("#E9A3C9", "#F7F7F7", "#A1D76A"),
        ("#D01C8B", "#F1B6DA", "#B8E186", "#4DAC26"),
        ("#D01C8B", "#F1B6DA", "#F7F7F7", "#B8E186", "#4DAC26"),
        ("#C51B7D", "#E9A3C9", "#FDE0EF", "#E6F5D0", "#A1D76A", "#4D9221"),
        ("#C51B7D", "#E9A3C9", "#FDE0EF", "#F7F7F7", "#E6F5D0", "#A1D76A", "#4D9221"),
        ("#C51B7D", "#DE77AE", "#F1B6DA", "#FDE0EF", "#E6F5D0", "#B8E186", "#7FBC41", "#4D9221"),
        ("#C51B7D", "#DE77AE", "#F1B6DA", "#FDE0EF", "#F7F7F7", "#E6F5D0", "#B8E186", "#7FBC41", "#4D9221"),
        ("#8E0152", "#C51B7D", "#DE77AE", "#F1B6DA", "#FDE0EF", "#E6F5D0", "#B8E186", "#7FBC41", "#4D9221", "#276419"),
        ("#8E0152", "#C51B7D", "#DE77AE", "#F1B6DA", "#FDE0EF", "#F7F7F7", "#E6F5D0", "#B8E186", "#7FBC41", "#4D9221", "#276419"),
    ),
    "PRGn": (
        ("#AF8DC3", "#F7F7F7", "#7FBF7B"),
        ("#7B3294", "#C2A5CF", "#A6DBA0", "#008837"),
        ("#7B3294", "#C2A5CF", "#F7F7F7", "#A6DBA0", "#008837"),
        ("#762A83", "#AF8DC3", "#E7D4E8", "#D9F0D3", "#7FBF7B", "#1B7837"),
        ("#762A83", "#AF8DC3", "#E7D4E8", "#F7F7F7", "#D9F0D3", "#7FBF7B", "#1B7837"),
        ("#762A83", "#9970AB", "#C2A5CF", "#E7D4E8", "#D9F0D3", "#A6DBA0", "#5AAE61", "#1B7837"),
        ("#762A83", "#9970AB", "#C2A5CF", "#E7D4E8", "#F7F7F7", "#D9F0D3", "#A6DBA0", "#5AAE61", "#1B7837"),
        ("#40004B", "#762A83", "#9970AB", "#C2A5CF", "#E7D4E8", "#D9F0D3", "#A6DBA0", "#5AAE61", "#1B7837", "#00441B"),
        ("#40004B", "#762A83", "#9970AB", "#C2A5CF", "#E7D4E8", "#F7F7F7", "#D9F0D3", "#A6DBA0", "#5AAE61", "#1B7837", "#00441B"),
    ),
    "PuBu": (
        ("#ECE7F2", "#A6BDDB", "#2B8CBE"),
        ("#F1EEF6", "#BDC9E1", "#74A9CF", "#0570B0"),
        ("#F1EEF6", "#BDC9E1", "#74A9CF", "#2B8CBE", "#045A8D"),
        ("#F1EEF6", "#D0D1E6", "#A6BDDB", "#74A9CF", "#2B8CBE", "#045A8D"),
        ("#F1EEF6", "#D0D1E6", "#A6BDDB", "#74A9CF", "#3690C0", "#0570B0", "#034E7B"),
        ("#FFF7FB", "#ECE7F2", "#D0D1E6", "#A6BDDB", "#74A9CF", "#3690C0", "#0570B0", "#034E7B"),
        ("#FFF7FB", "#ECE7F2", "#D0D1E6", "#A6BDDB", "#74A9CF", "#3690C0", "#0570B0", "#045A8D", "#023858"),
    ),
    "PuBuGn": (
        ("#ECE2F0", "#A6BDDB", "#1C9099"),
        ("#F6EFF7", "#BDC9E1", "#67A9CF", "#02818A"),
        ("#F6EFF7", "#BDC9E1", "#67A9CF", "#1C9099", "#016C59"),
        ("#F6EFF7", "#D0D1E6", "#A6BDDB", "#67A9CF", "#1C9099", "#016C59"),
        ("#F6EFF7", "#D0D1E6", "#A6BDDB", "#67A9CF", "#3690C0", "#02818A", "#016450"),
        ("#FFF7FB", "#ECE2F0", "#D0D1E6", "#A6BDDB", "#67A9CF", "#3690C0", "#02818A", "#016450"),
        ("#FFF7FB", "#ECE2F0", "#D0D1E6", "#A6BDDB", "#67A9CF", "#3690C0", "#02818A", "#016C59", "#014636"),
    ),
    "PuOr": (
        ("#F1A340", "#F7F7F7", "#998EC3"),
        ("#E66101", "#FDB863", "#B2ABD2", "#5E3C99"),
        ("#E66101", "#FDB863", "#F7F7F7", "#B2ABD2", "#5E3C99"),
        ("#B35806", "#F1A340", "#FEE0B6", "#D8DAEB", "#998EC3", "#542788"),
        ("#B35806", "#F1A340", "#FEE0B6", "#F7F7F7", "#D8DAEB", "#998EC3", "#542788"),
        ("#B35806", "#E08214", "#FDB863", "#FEE0B6", "#D8DAEB", "#B2ABD2", "#8073AC", "#542788"),
        ("#B35806", "#E08214", "#FDB863", "#FEE0B6", "#F7F7F7", "#D8DAEB", "#B2ABD2", "#8073AC", "#542788"),
        ("#7F3B08", "#B35806", "#E08214", "#FDB863", "#FEE0B6", "#D8DAEB", "#B2ABD2", "#8073AC", "#542788", "#2D004B"),
        ("#7F3B08", "#B35806", "#E08214", "#FDB863", "#FEE0B6", "#F7F7F7", "#D8DAEB", "#B2ABD2", "#8073AC", "#542788", "#2D004B"),
    ),
    "PuRd": (
        ("#E7E1EF", "#C994C7", "#DD1C77"),
        ("#F1EEF6", "#D7B5D8", "#DF65B0", "#CE1256"),
        ("#F1EEF6", "#D7B5D8", "#DF65B0", "#DD1C77", "#980043"),
        ("#F1EEF6", "#D4B9DA", "#C994C7", "#DF65B0", "#DD1C77", "#980043"),
        ("#F1EEF6", "#D4B9DA", "#C994C7", "#DF65B0", "#E7298A", "#CE1256", "#91003F"),
        ("#F7F4F9", "#E7E1EF", "#D4B9DA", "#C994C7", "#DF65B0", "#E7298A", "#CE1256", "#91003F"),
        ("#F7F4F9", "#E7E1EF", "#D4B9DA", "#C994C7", "#DF65B0", "#E7298A", "#CE1256", "#980043", "#67001F"),
    ),
    "Purples": (
        ("#EFEDF5", "#BCBDDC", "#756BB1"),
        ("#F2F0F7", "#CBC9E2", "#9E9AC8", "#6A51A3"),
        ("#F2F0F7", "#CBC9E2", "#9E9AC8", "#756BB1", "#54278F"),
        ("#F2F0F7", "#DADAEB", "#BCBDDC", "#9E9AC8", "#756BB1", "#54278F"),
        ("#F2F0F7", "#DADAEB", "#BCBDDC", "#9E9AC8", "#807DBA", "#6A51A3", "#4A1486"),
        ("#FCFBFD", "#EFEDF5", "#DADAEB", "#BCBDDC", "#9E9AC8", "#807DBA", "#6A51A3", "#4A1486"),
        ("#FCFBFD", "#EFEDF5", "#DADAEB", "#BCBDDC", "#9E9AC8", "#807DBA", "#6A51A3", "#54278F", "#3F007D"),
    ),
    "RdBu": (
        ("#EF8A62", "#F7F7F7", "#67A9CF"),
        ("#CA0020", "#F4A582", "#92C5DE", "#0571B0"),
        ("#CA0020", "#F4A582", "#F7F7F7", "#92C5DE", "#0571B0"),
        ("#B2182B", "#EF8A62", "#FDDBC7", "#D1E5F0", "#67A9CF", "#2166AC"),
        ("#B2182B", "#EF8A62", "#FDDBC7", "#F7F7F7", "#D1E5F0", "#67A9CF", "#2166AC"),
        ("#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#D1E5F0", "#92C5DE", "#4393C3", "#2166AC"),
        ("#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#F7F7F7", "#D1E5F0", "#92C5DE", "#4393C3", "#2166AC"),
        ("#67001F", "#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#D1E5F0", "#92C5DE", "#4393C3", "#2166AC", "#053061"),
        ("#67001F", "#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#F7F7F7", "#D1E5F0", "#92C5DE", "#4393C3", "#2166AC", "#053061"),
    ),
    "RdGy": (
        ("#EF8A62", "#FFFFFF", "#999999"),
        ("#CA0020", "#F4A582", "#BABABA", "#404040"),
        ("#CA0020", "#F4A582", "#FFFFFF", "#BABABA", "#404040"),
        ("#B2182B", "#EF8A62", "#FDDBC7", "#E0E0E0", "#999999", "#4D4D4D"),
        ("#B2182B", "#EF8A62", "#FDDBC7", "#FFFFFF", "#E0E0E0", "#999999", "#4D4D4D"),
        ("#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#E0E0E0", "#BABABA", "#878787", "#4D4D4D"),
        ("#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#FFFFFF", "#E0E0E0", "#BABABA", "#878787", "#4D4D4D"),
        ("#67001F", "#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#E0E0E0", "#BABABA", "#878787", "#4D4D4D", "#1A1A1A"),
        ("#67001F", "#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#FFFFFF", "#E0E0E0", "#BABABA", "#878787", "#4D4D4D", "#1A1A1A"),
    ),
    "RdPu": (
        ("#FDE0DD", "#FA9FB5", "#C51B8A"),
        ("#FEEBE2", "#FBB4B9", "#F768A1", "#AE017E"),
        ("#FEEBE2", "#FBB4B9", "#F768A1", "#C51B8A", "#7A0177"),
        ("#FEEBE2", "#FCC5C0", "#FA9FB5", "#F768A1", "#C51B8A", "#7A0177"),
        ("#FEEBE2", "#FCC5C0", "#FA9FB5", "#F768A1", "#DD3497", "#AE017E", "#7A0177"),
        ("#FFF7F3", "#FDE0DD", "#FCC5C0", "#FA9FB5", "#F768A1", "#DD3497", "#AE017E", "#7A0177"),
        ("#FFF7F3", "#FDE0DD", "#FCC5C0", "#FA9FB5", "#F768A1", "#DD3497", "#AE017E", "#7A0177", "#49006A"),
    ),
    "Reds": (
        ("#FEE0D2", "#FC9272", "#DE2D26"),
        ("#FEE5D9", "#FCAE91", "#FB6A4A", "#CB181D"),
        ("#FEE5D9", "#FCAE91", "#FB6A4A", "#DE2D26", "#A50F15"),
        ("#FEE5D9", "#FCBBA1", "#FC9272", "#FB6A4A", "#DE2D26", "#A50F15"),
        ("#FEE5D9", "#FCBBA1", "#FC9272", "#FB6A4A", "#EF3B2C", "#CB181D", "#99000D"),
        ("#FFF5F0", "#FEE0D2", "#FCBBA1", "#FC9272", "#FB6A4A", "#EF3B2C", "#CB181D", "#99000D"),
        ("#FFF5F0", "#FEE0D2", "#FCBBA1", "#FC9272", "#FB6A4A", "#EF3B2C", "#CB181D", "#A50F15", "#67000D"),
    ),
    "RdYlBu": (
        ("#FC8D59", "#FFFFBF", "#91BFDB"),
        ("#D7191C", "#FDAE61", "#ABD9E9", "#2C7BB6"),
        ("#D7191C", "#FDAE61", "#FFFFBF", "#ABD9E9", "#2C7BB6"),
        ("#D73027", "#FC8D59", "#FEE090", "#E0F3F8", "#91BFDB", "#4575B4"),
        ("#D73027", "#FC8D59", "#FEE090", "#FFFFBF", "#E0F3F8", "#91BFDB", "#4575B4"),
        ("#D73027", "#F46D43", "#FDAE61", "#FEE090", "#E0F3F8", "#ABD9E9", "#74ADD1", "#4575B4"),
        ("#D73027", "#F46D43", "#FDAE61", "#FEE090", "#FFFFBF", "#E0F3F8", "#ABD9E9", "#74ADD1", "#4575B4"),
        ("#A50026", "#D73027", "#F46D43", "#FDAE61", "#FEE090", "#E0F3F8", "#ABD9E9", "#74ADD1", "#4575B4", "#313695"),
        ("#A50026", "#D73027", "#F46D43", "#FDAE61", "#FEE090", "#FFFFBF", "#E0F3F8", "#ABD9E9", "#74ADD1", "#4575B4", "#313695"),
    ),
    "RdYlGn": (
        ("#FC8D59", "#FFFFBF", "#91CF60"),
        ("#D7191C", "#FDAE61", "#A6D96A", "#1A9641"),
        ("#D7191C", "#FDAE61", "#FFFFBF", "#A6D96A", "#1A9641"),
        ("#D73027", "#FC8D59", "#FEE08B", "#D9EF8B", "#91CF60", "#1A9850"),
        ("#D73027", "#FC8D59", "#FEE08B", "#FFFFBF", "#D9EF8B", "#91CF60", "#1A9850"),
        ("#D73027", "#F46D43", "#FDAE61", "#FEE08B", "#D9EF8B", "#A6D96A", "#66BD63", "#1A9850"),
        ("#D73027", "#F46D43", "#FDAE61", "#FEE08B", "#FFFFBF", "#D9EF8B", "#A6D96A", "#66BD63", "#1A9850"),
        ("#A50026", "#D73027", "#F46D43", "#FDAE61", "#FEE08B", "#D9EF8B", "#A6D96A", "#66BD63", "#1A9850", "#006837"),
        ("#A50026", "#D73027", "#F46D43", "#FDAE61", "#FEE08B", "#FFFFBF", "#D9EF8B", "#A6D96A", "#66BD63", "#1A9850", "#006837"),
    ),
    "Set1": (
        ("#E41A1C", "#377EB8", "#4DAF4A"),
        ("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3"),
        ("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00"),
        ("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#FFFF33"),
        ("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#FFFF33", "#A65628"),
        ("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#FFFF33", "#A65628", "#F781BF"),
        ("#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#FFFF33", "#A65628", "#F781BF", "#999999"),
    ),
    "Set2": (
        ("#66C2A5", "#FC8D62", "#8DA0CB"),
        ("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3"),
        ("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854"),
        ("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F"),
        ("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F", "#E5C494"),
        ("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F", "#E5C494", "#B3B3B3"),
    ),
    "Set3": (
        ("#8DD3C7", "#FFFFB3", "#BEBADA"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69", "#FCCDE5"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69", "#FCCDE5", "#D9D9D9"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69", "#FCCDE5", "#D9D9D9", "#BC80BD"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69", "#FCCDE5", "#D9D9D9", "#BC80BD", "#CCEBC5"),
        ("#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69", "#FCCDE5", "#D9D9D9", "#BC80BD", "#CCEBC5", "#FFED6F"),
    ),
    "Spectral": (
        ("#FC8D59", "#FFFFBF", "#99D594"),
        ("#D7191C", "#FDAE61", "#ABDDA4", "#2B83BA"),
        ("#D7191C", "#FDAE61", "#FFFFBF", "#ABDDA4", "#2B83BA"),
        ("#D53E4F", "#FC8D59", "#FEE08B", "#E6F598", "#99D594", "#3288BD"),
        ("#D53E4F", "#FC8D59", "#FEE08B", "#FFFFBF", "#E6F598", "#99D594", "#3288BD"),
        ("#D53E4F", "#F46D43", "#FDAE61", "#FEE08B", "#E6F598", "#ABDDA4", "#66C2A5", "#3288BD"),
        ("#D53E4F", "#F46D43", "#FDAE61", "#FEE08B", "#FFFFBF", "#E6F598", "#ABDDA4", "#66C2A5", "#3288BD"),
        ("#9E0142", "#D53E4F", "#F46D43", "#FDAE61", "#FEE08B", "#E6F598", "#ABDDA4", "#66C2A5", "#3288BD", "#5E4FA2"),
        ("#9E0142", "#D53E4F", "#F46D43", "#FDAE61", "#FEE08B", "#FFFFBF", "#E6F598", "#ABDDA4", "#66C2A5", "#3288BD", "#5E4FA2"),
    ),
    "YlGn": (
        ("#F7FCB9", "#ADDD8E", "#31A354"),
        ("#FFFFCC", "#C2E699", "#78C679", "#238443"),
        ("#FFFFCC", "#C2E699", "#78C679", "#31A354", "#006837"),
        ("#FFFFCC", "#D9F0A3", "#ADDD8E", "#78C679", "#31A354", "#006837"),
        ("#FFFFCC", "#D9F0A3", "#ADDD8E", "#78C679", "#41AB5D", "#238443", "#005A32"),
        ("#FFFFE5", "#F7FCB9", "#D9F0A3", "#ADDD8E", "#78C679", "#41AB5D", "#238443", "#005A32"),
        ("#FFFFE5", "#F7FCB9", "#D9F0A3", "#ADDD8E", "#78C679", "#41AB5D", "#238443", "#006837", "#004529"),
    ),
    "YlGnBu": (
        ("#EDF8B1", "#7FCDBB", "#2C7FB8"),
        ("#FFFFCC", "#A1DAB4", "#41B6C4", "#225EA8"),
        ("#FFFFCC", "#A1DAB4", "#41B6C4", "#2C7FB8", "#253494"),
        ("#FFFFCC", "#C7E9B4", "#7FCDBB", "#41B6C4", "#2C7FB8", "#253494"),
        ("#FFFFCC", "#C7E9B4", "#7FCDBB", "#41B6C4", "#1D91C0", "#225EA8", "#0C2C84"),
        ("#FFFFD9", "#EDF8B1", "#C7E9B4", "#7FCDBB", "#41B6C4", "#1D91C0", "#225EA8", "#0C2C84"),
        ("#FFFFD9", "#EDF8B1", "#C7E9B4", "#7FCDBB", "#41B6C4", "#1D91C0", "#225EA8", "#253494", "#081D58"),
    ),
    "YlOrBr": (
        ("#FFF7BC", "#FEC44F", "#D95F0E"),
        ("#FFFFD4", "#FED98E", "#FE9929", "#CC4C02"),
        ("#FFFFD4", "#FED98E", "#FE9929", "#D95F0E", "#993404"),
        ("#FFFFD4", "#FEE391", "#FEC44F", "#FE9929", "#D95F0E", "#993404"),
        ("#FFFFD4", "#FEE391", "#FEC44F", "#FE9929", "#EC7014", "#CC4C02", "#8C2D04"),
        ("#FFFFE5", "#FFF7BC", "#FEE391", "#FEC44F", "#FE9929", "#EC7014", "#CC4C02", "#8C2D04"),
        ("#FFFFE5", "#FFF7BC", "#FEE391", "#FEC44F", "#FE9929", "#EC7014", "#CC4C02", "#993404", "#662506"),
    ),
    "YlOrRd": (
        ("#FFEDA0", "#FEB24C", "#F03B20"),
        ("#FFFFB2", "#FECC5C", "#FD8D3C", "#E31A1C"),
        ("#FFFFB2", "#FECC5C", "#FD8D3C", "#F03B20", "#BD0026"),
        ("#FFFFB2", "#FED976", "#FEB24C", "#FD8D3C", "#F03B20", "#BD0026"),
        ("#FFFFB2", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#B10026"),
        ("#FFFFCC", "#FFEDA0", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#B10026"),
        ("#FFFFCC", "#FFEDA0", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#BD0026", "#800026"),
    ),
}

_MAX = {name: len(rows) + 2 for name, rows in _PALETTES.items()}

_DIVLIST = (
    "BrBG",
    "PiYG",
    "PRGn",
    "PuOr",
    "RdBu",
    "RdGy",
    "RdYlBu",
    "RdYlGn",
    "Spectral",
)
_QUALLIST = (
    "Accent",
    "Dark2",
    "Paired",
    "Pastel1",
    "Pastel2",
    "Set1",
    "Set2",
    "Set3",
)
_QUALMAX = (8, 8, 12, 9, 8, 9, 8, 12)
_SEQLIST = (
    "Blues",
    "BuGn",
    "BuPu",
    "GnBu",
    "Greens",
    "Greys",
    "Oranges",
    "OrRd",
    "PuBu",
    "PuBuGn",
    "PuRd",
    "Purples",
    "RdPu",
    "Reds",
    "YlGn",
    "YlGnBu",
    "YlOrBr",
    "YlOrRd",
)
_COLORBLIND = frozenset(
    {
        "BrBG",
        "PiYG",
        "PRGn",
        "PuOr",
        "RdBu",
        "RdYlBu",
        "Dark2",
        "Paired",
        "Set2",
        *_SEQLIST,
    }
)


class BrewerPalInfoRow:
    """One row of brewer.pal.info."""

    __slots__ = ("maxcolors", "category", "colorblind")

    def __init__(self, maxcolors=None, category=None, colorblind=None):
        self.maxcolors = maxcolors
        self.category = category
        self.colorblind = colorblind


class BrewerPalInfo:
    """Palette metadata table from RColorBrewer brewer.pal.info."""

    def __init__(self, order, rows):
        self._order = tuple(order)
        self._rows = dict(rows)

    def row_names(self):
        return list(self._order)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            key = key[0]
        row = self._rows.get(key)
        if row is None:
            return BrewerPalInfoRow(None, None, None)
        return BrewerPalInfoRow(row.maxcolors, row.category, row.colorblind)

    @property
    def maxcolors(self):
        return [self._rows[name].maxcolors for name in self._order]

    @property
    def category(self):
        return [self._rows[name].category for name in self._order]

    @property
    def colorblind(self):
        return [self._rows[name].colorblind for name in self._order]


def _format_brewer_pal_info_table(info, names):
    names = tuple(names)
    if len(names) == len(info._order):
        name_width = 16
        header_pad = 9
    else:
        name_width = max(max(len(name) for name in names), 5) + 5
        header_pad = 6
    lines = [f"{'':>{header_pad}} maxcolors category colorblind"]
    for name in names:
        row = info._rows[name] if name in info._rows else BrewerPalInfoRow(None, None, None)
        if row.maxcolors is None:
            maxcolors = "NA"
            category = "<NA>"
            colorblind = "NA"
        else:
            maxcolors = str(row.maxcolors)
            category = row.category
            colorblind = "TRUE" if row.colorblind else "FALSE"
        lines.append(
            f"{name:<{name_width}}{maxcolors:>2}{' ' * 6}{category:<4}{' ' * 6}{colorblind:>4}"
        )
    return "\n".join(lines) + "\n"


def format_brewer_pal_info(info):
    """Print brewer.pal.info like R's default data.frame printer."""

    return _format_brewer_pal_info_table(info, info._order)


def format_brewer_pal_info_row(info, name):
    return _format_brewer_pal_info_table(info, (name,))


def _build_brewer_pal_info():
    order = []
    rows = {}
    for name in _DIVLIST:
        order.append(name)
        rows[name] = BrewerPalInfoRow(11, "div", name in _COLORBLIND)
    for name, limit in zip(_QUALLIST, _QUALMAX, strict=True):
        order.append(name)
        rows[name] = BrewerPalInfoRow(limit, "qual", name in _COLORBLIND)
    for name in _SEQLIST:
        order.append(name)
        rows[name] = BrewerPalInfoRow(9, "seq", True)
    return BrewerPalInfo(order, rows)


brewer_pal_info = _build_brewer_pal_info()


def _max_warning(name, limit):
    return (
        f"n too large, allowed maximum for palette {name} is {limit}\n"
        "Returning the palette you asked for with that many colors\n"
    )


def _shown(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    return str(value)


def _as_name(name):
    if isinstance(name, (list, tuple)):
        if len(name) == 0:
            raise BrewerPalError("argument is of length zero")
        if len(name) > 1:
            raise BrewerPalError("the condition has length > 1")
        name = name[0]
    if name is None:
        raise BrewerPalError("argument is of length zero")
    if not isinstance(name, str):
        raise BrewerPalError(
            f"{_shown(name)} is not a valid palette name for brewer.pal\n"
        )
    if name not in _MAX:
        raise BrewerPalError(
            f"{name} is not a valid palette name for brewer.pal\n"
        )
    return name


def _as_n(n):
    if isinstance(n, (list, tuple)):
        if len(n) == 0:
            raise BrewerPalError("argument is of length zero")
        if len(n) > 1:
            raise BrewerPalError("the condition has length > 1")
        n = n[0]
    if n is None:
        raise BrewerPalError("argument is of length zero")
    if isinstance(n, str) or not isinstance(n, numbers.Real):
        raise BrewerPalError("non-numeric argument to binary operator")
    value = float(n)
    if math.isnan(value):
        raise BrewerPalError("missing value where TRUE/FALSE needed")
    return value


def _colors(name, n):
    row = math.trunc(n) - 3
    return list(_PALETTES[name][row])


def brewer_pal(n, name):
    """Return the ColorBrewer hex colors for palette `name` and count `n`."""

    checked = _as_name(name)
    number = _as_n(n)
    if number < 3.0:
        warnings.warn(_MIN_WARNING, BrewerPalWarning, stacklevel=2)
        return _colors(checked, 3)
    limit = _MAX[checked]
    if number > limit:
        warnings.warn(_max_warning(checked, limit), BrewerPalWarning, stacklevel=2)
        return _colors(checked, limit)
    return _colors(checked, number)


_DISPLAY_MIN_WARNING = (
    "minimal value for n is 3, displaying requested palette with 3 different levels\n"
)


def _display_max_warning(name, limit):
    return (
        f"n too large, allowed maximum for palette {name} is {limit}\n"
        "Displaying the palette you asked for with that many colors\n"
    )


def _palette_attr(name):
    if name in _QUALLIST:
        return "(qualitative)"
    if name in _DIVLIST:
        return "(divergent)"
    return "(sequential)"


def _hex_to_rgb01(colors):
    values = []
    for item in colors:
        text = item[1:] if item.startswith("#") else item
        values.extend(
            (
                int(text[0:2], 16) / 255.0,
                int(text[2:4], 16) / 255.0,
                int(text[4:6], 16) / 255.0,
            )
        )
    return values


def display_brewer_pal(n, name, ax=None, *, draw=True):
    """Draw a ColorBrewer palette strip like R ``display.brewer.pal``."""

    checked = _as_name(name)
    number = _as_n(n)
    if number < 3.0:
        warnings.warn(_DISPLAY_MIN_WARNING, BrewerPalWarning, stacklevel=2)
        return display_brewer_pal(3, checked, ax=ax, draw=draw)
    limit = _MAX[checked]
    if number > limit:
        warnings.warn(_display_max_warning(checked, limit), BrewerPalWarning, stacklevel=2)
        return display_brewer_pal(limit, checked, ax=ax, draw=draw)

    colors = brewer_pal(number, checked)
    shown = int(math.trunc(number))
    xlab = f"{checked} {_palette_attr(checked)}"
    usr = (0.5, shown + 0.5, 0.6, 1.4)
    metadata = {
        "colors": colors,
        "rgb": _hex_to_rgb01(colors),
        "usr": list(usr),
        "n": shown,
        "xlab": xlab,
        "figure": None,
        "axes": None,
    }
    if not draw:
        return metadata

    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import BoundaryNorm, ListedColormap

    if ax is None:
        figure, ax = plt.subplots(figsize=(max(shown * 0.5, 3.0), 1.2))
    else:
        figure = ax.figure

    bounds = np.arange(0.5, shown + 1.5)
    data = np.arange(1, shown + 1, dtype=float).reshape(1, shown)
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(bounds, cmap.N)
    ax.imshow(
        data,
        aspect="auto",
        origin="lower",
        extent=list(usr),
        cmap=cmap,
        norm=norm,
        interpolation="nearest",
    )
    ax.set_xlabel(xlab)
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    metadata["figure"] = figure
    metadata["axes"] = ax
    return metadata


_COLORBLINDLIST = frozenset(
    {
        "BrBG",
        "PiYG",
        "PRGn",
        "PuOr",
        "RdBu",
        "RdYlBu",
        "Dark2",
        "Paired",
        "Set2",
        "Blues",
        "BuGn",
        "BuPu",
        "GnBu",
        "Greens",
        "Greys",
        "Oranges",
        "OrRd",
        "PuBu",
        "PuBuGn",
        "PuRd",
        "Purples",
        "RdPu",
        "Reds",
        "YlGn",
        "YlGnBu",
        "YlOrBr",
        "YlOrRd",
    }
)

_DIVNUM = (11,) * len(_DIVLIST)
_SEQNUM = (9,) * len(_SEQLIST)


def _brewer_all_lists(type_):
    if type_ == "div":
        keys = list(_DIVLIST)
        palettes = list(_DIVLIST)
        maxnums = list(_DIVNUM)
    elif type_ == "qual":
        keys = list(_QUALLIST)
        palettes = list(_QUALLIST)
        maxnums = list(_QUALMAX)
    elif type_ == "seq":
        keys = list(_SEQLIST)
        palettes = list(_SEQLIST)
        maxnums = list(_SEQNUM)
    elif type_ == "all":
        gapnum = max(max(_DIVNUM), max(_QUALMAX), max(_SEQNUM))
        keys = (
            list(_DIVLIST)
            + ["gap1"]
            + list(_QUALLIST)
            + ["gap2"]
            + list(_SEQLIST)
        )
        palettes = (
            list(_DIVLIST)
            + [""]
            + list(_QUALLIST)
            + [""]
            + list(_SEQLIST)
        )
        maxnums = list(_DIVNUM) + [gapnum] + list(_QUALMAX) + [gapnum] + list(_SEQNUM)
    else:
        raise BrewerPalError(f"{type_} is not a valid name for a color list\n")
    return keys, palettes, maxnums


def _brewer_all_layout(
    n=None,
    type_="all",
    select=None,
    exact_n=True,
    colorblind_friendly=False,
):
    keys, palettes, maxnums = _brewer_all_lists(type_)
    if select is not None:
        if isinstance(select, str):
            select = [select]
        lookup = {key: idx for idx, key in enumerate(keys)}
        chosen = []
        missing = []
        for name in select:
            idx = lookup.get(name)
            if idx is None:
                missing.append(name)
                chosen.append(None)
            else:
                chosen.append(idx)
        if any(item is None for item in chosen):
            bad = " ".join(str(name) for name, idx in zip(select, chosen, strict=True) if idx is None)
            raise BrewerPalError(f"Illegal value(s) of select:  {bad}")
        keys = [keys[idx] for idx in chosen]
        palettes = [palettes[idx] for idx in chosen]
        maxnums = [maxnums[idx] for idx in chosen]
    if colorblind_friendly:
        keep = [
            idx
            for idx, key in enumerate(keys)
            if key in _COLORBLINDLIST or key in ("gap1", "gap2")
        ]
        keys = [keys[idx] for idx in keep]
        palettes = [palettes[idx] for idx in keep]
        maxnums = [maxnums[idx] for idx in keep]
    if n is None:
        n = list(maxnums)
    elif isinstance(n, (int, float)):
        n = [n]
    else:
        n = list(n)
    if len(n) == 1:
        n = n * len(palettes)
    warned = False
    if exact_n:
        keep = [idx for idx, (count, limit) in enumerate(zip(n, maxnums, strict=True)) if count <= limit]
        keys = [keys[idx] for idx in keep]
        palettes = [palettes[idx] for idx in keep]
        maxnums = [maxnums[idx] for idx in keep]
        n = [n[idx] for idx in keep]
    if (
        any(count < 3 for count in n)
        or (exact_n and any(count > limit for count, limit in zip(n, maxnums, strict=True)))
        or len(n) != len(palettes)
    ):
        warnings.warn("Illegal vector of color numbers", UserWarning, stacklevel=3)
        warned = True
    clamped = []
    for count, limit in zip(n, maxnums, strict=True):
        value = count
        if value < 3:
            value = 3
        elif value > limit:
            value = limit
        clamped.append(int(math.trunc(value)))
    n = clamped
    nr = len(palettes)
    nc = max(n) if n else 0
    rgb = []
    rows = []
    for palette, count in zip(palettes, n, strict=True):
        if palette == "":
            rows.append([])
            continue
        colors = brewer_pal(count, palette)
        rows.append(colors)
        rgb.extend(_hex_to_rgb01(colors))
    usr = _brewer_all_usr(nc, nr)
    return {
        "keys": keys,
        "palettes": palettes,
        "n": n,
        "maxnums": maxnums,
        "nr": nr,
        "nc": nc,
        "rgb": rgb,
        "rows": rows,
        "usr": usr,
        "warned": warned,
    }


def _brewer_all_usr(nc, nr):
    pad_x = 0.04 * nc
    pad_y = 0.04 * nr
    return [-pad_x, nc + pad_x, -pad_y, nr + pad_y]


def display_brewer_all(
    n=None,
    type="all",
    select=None,
    exact_n=True,
    colorblind_friendly=False,
    ax=None,
    *,
    draw=True,
):
    """Draw ColorBrewer palettes like R ``display.brewer.all``."""

    layout = _brewer_all_layout(
        n=n,
        type_=type,
        select=select,
        exact_n=exact_n,
        colorblind_friendly=colorblind_friendly,
    )
    palettes = layout["palettes"]
    counts = layout["n"]
    rows = layout["rows"]
    nr = layout["nr"]
    nc = layout["nc"]
    usr = layout["usr"]
    metadata = {
        "rgb": layout["rgb"],
        "usr": usr,
        "nr": nr,
        "nc": nc,
        "n": counts,
        "palettes": palettes,
        "figure": None,
        "axes": None,
    }
    if not draw:
        return metadata

    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    if ax is None:
        figure, ax = plt.subplots(figsize=(max(nc * 0.45, 6.0), max(nr * 0.22, 4.0)))
    else:
        figure = ax.figure

    ax.set_xlim(usr[0], usr[1])
    ax.set_ylim(usr[2], usr[3])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    for spine in ax.spines.values():
        spine.set_visible(False)

    for index, (palette, colors) in enumerate(zip(palettes, rows, strict=True), start=1):
        if palette == "":
            continue
        for slot, color in enumerate(colors):
            ax.add_patch(
                Rectangle(
                    (slot, index - 1),
                    1.0,
                    0.8,
                    facecolor=color,
                    edgecolor="lightgrey",
                    linewidth=0.5,
                )
            )
        ax.text(
            -0.1,
            index - 0.6,
            palette,
            ha="right",
            va="center",
            transform=ax.transData,
            clip_on=False,
        )

    metadata["figure"] = figure
    metadata["axes"] = ax
    return metadata
