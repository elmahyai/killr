suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
root <- normalizePath(file.path(dirname(script), ".."))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pack <- function(group, y, ...) {
  args <- list(group = group, y = y, ...)
  pdf(NULL)
  do.call(plotGrowthCurves, args)
  usr <- par("usr")
  invisible(dev.off())
  if (is.null(args$levels)) {
    lev <- as.character(sort(unique(group)))
  } else {
    lev <- as.character(args$levels)
  }
  labels <- as.character(group)
  yy <- as.matrix(y)
  if (!is.null(args$times)) yy <- yy[, args$times, drop = FALSE]
  col <- args$col
  if (is.null(col)) col <- seq_along(lev)
  spec <- col[match(labels, lev)]
  rgb <- matrix(NA_real_, length(spec), 3)
  ok <- !is.na(spec)
  if (any(ok)) rgb[ok, ] <- t(col2rgb(spec[ok]))
  legend_rgb <- t(col2rgb(rep_len(col, length(lev))))
  yr <- range(yy, na.rm = TRUE)
  c(usr, 1, yr[2] - diff(yr) / 40, as.numeric(yy), as.numeric(rgb), as.numeric(legend_rgb))
}

curves <- function() {
  matrix(
    c(
      1.0, 1.4, 1.2, 1.1,
      2.0, 2.2, NA, 2.4,
      1.2, 1.0, 1.5, 1.3,
      2.4, 2.1, 2.6, 2.0,
      3.0, 3.3, 2.8, 3.1,
      2.2, 1.9, 2.3, 2.5,
      0.2, 0.4, 0.3, 0.5
    ),
    nrow = 7,
    byrow = TRUE
  )
}

curve_group <- function() c("B", "A", "B", "A", "C", "A", NA)

one <- function() {
  c(
    pack(curve_group(), curves(), times = c(1, 2, 4), col = c(2, 4, "darkgreen")),
    pack(c("A", "A", "B", "B"), cbind(c(5, 5.5, 8, 9))),
    pack(
      c("A", "A", "B", "B"),
      matrix(c(1, 10, 2, 20, 30, 50, 25, 80), nrow = 4, byrow = TRUE),
      log = "y"
    ),
    pack(
      c("A", "A", "B", "B"),
      matrix(c(1, 2, 1.2, 2.2, 3, 4, 3.2, 3.8), nrow = 4, byrow = TRUE),
      col = 2
    ),
    pack(
      c(10, 2, 10, 2),
      matrix(c(1, 2, 4, 5, 1.5, 2.5, 4.2, 5.1), nrow = 4, byrow = TRUE),
      xlim = c(0, 4),
      ylim = c(0, 6)
    )
  )
}

svg(file.path(out_dir, "plotGrowthCurves-r.svg"), width = 7, height = 7)
plotGrowthCurves(curve_group(), curves(), times = c(1, 2, 4), col = c(2, 4, "darkgreen"))
invisible(dev.off())

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
