# Proof for plotDensityMclustd: the pairwise density panels of a densityMclust fit with d > 2.
# R's own densityMclust fits (d = 3 and d = 4) are dumped to JSON, and both sides read
# those files. R draws each panel through plotDensityMclustd; the recorder logs the drawn
# data: the diagonal windows and labels, the contour window, grid and levels, the points,
# the axis sides, and the layout. plotDensityMclustd-py.py logs the same records.
.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
source(file.path(here, "plot_object_io.R"))
fx <- make_fixtures()
i <- 1:60
g3 <- (i - 1) %% 3

X3 <- fx$data3
colnames(X3) <- c("x1", "x2", "x3")
X4 <- cbind(X3, x4 = 0.6 * cos(1.1 * i) + 0.5 * g3 - 0.3 * sin(0.4 * i))

d3 <- densityMclust(X3, G = 2, modelNames = "VVV", plot = FALSE, verbose = FALSE)
d4 <- densityMclust(X4, G = 2, modelNames = "VVV", plot = FALSE, verbose = FALSE)
dump_mclust_object(d3, file.path(here, "plot_object_density3d.json"))
dump_mclust_object(d4, file.path(here, "plot_object_density4d.json"))
obj3 <- read_mclust_object(file.path(here, "plot_object_density3d.json"))
obj4 <- read_mclust_object(file.path(here, "plot_object_density4d.json"))

E <- mk_recorder(c("plotDensityMclustd", "surfacePlot"))
put <- function(tag, ...) {
  E$log <- c(E$log, paste(c(tag, rec_fields(...)), collapse = " "))
  invisible(NULL)
}
usr <- function() as.numeric(par("usr"))

# par(): the layout that plotDensityMclustd sets (mfrow, mar, oma), read back from R.
E$par <- function(...) {
  args <- list(...)
  r <- graphics::par(...)
  if (E$mode != "time" && "mfrow" %in% names(args)) {
    cur <- graphics::par(c("mfrow", "mar", "oma"))
    put("V", "layout", cur$mfrow, cur$mar, cur$oma)
  }
  invisible(r)
}
# axis(): the side, with the panel (i, j) read from plotDensityMclustd's frame.
E$axis <- function(side, ...) {
  if (E$mode != "time") {
    fr <- parent.frame()
    put("V", "axis", c(get("i", envir = fr), get("j", envir = fr), side))
  }
  invisible(NULL)
}
# text(): the diagonal label at the centre of the panel's usr box.
E$text <- function(x, y = NULL, labels = NULL, ...) {
  if (E$mode != "time") put("T", x, y, labels)
  invisible(NULL)
}
# contour(): draws, then logs the window R set and the grid and levels it drew.
E$contour <- function(x, y, z, levels = NULL, ...) {
  if (E$mode == "time") return(invisible(NULL))
  graphics::contour(x = x, y = y, z = z, levels = levels, ...)
  put("W", usr())
  put("C", x, y, as.numeric(z), levels)
  invisible(NULL)
}

E$obj3 <- obj3
E$obj4 <- obj4
E$pts <- obj3$data[1:30, , drop = FALSE]

cases <- list(
  d3_contour = function() evalq(plotDensityMclustd(obj3), E),
  d3_points = function() evalq(plotDensityMclustd(obj3, data = pts, points.col = "black"), E),
  d4_contour = function() evalq(plotDensityMclustd(obj4), E)
)

out_dir <- file.path(here, "..", "docs", "output")
ms <- proof_run(E, cases, timed = "d3_contour", stem = "plotDensityMclustd", out_dir = out_dir)

pdf(NULL)
ms4 <- time_median_ms(E, cases$d4_contour)
dev.off()
writeLines(sprintf("%.17g", ms4), file.path(out_dir, "plotDensityMclustd-d4-r-time.txt"))
cat(sprintf("r_ms=%.17g\nr_ms_d4=%.17g\n", ms, ms4))
