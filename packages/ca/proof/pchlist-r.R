# Proof for pchlist (ca 0.72), R side.
#
# pchlist() calls plot() once and box() once. This script runs the real ca
# function with its environment replaced by a shim: plot() calls the real
# graphics::plot on a null pdf device (7 x 7 in, the default size) and records
# its x, y, pch, the device's par("usr") limits, par("col") and par("cex");
# box() is counted. Writes:
#   docs/output/pchlist-r-values.txt  (recorded plot call, limits, box count)
#   docs/output/pchlist-r-ms.txt      (median of 20 timed calls after 1 untimed)
# Run from the repository root.

library(ca)

out_dir <- "packages/ca/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pdf(NULL, width = 7, height = 7)

rec <- new.env()
rec$plot <- NULL
rec$box <- 0L
shim <- new.env(parent = asNamespace("ca"))
shim$plot <- function(x, y = NULL, ...) {
  a <- list(...)
  graphics::plot(x, y, ...)
  rec$plot <- list(
    x = as.numeric(x), y = as.numeric(y), pch = as.numeric(a$pch),
    usr = par("usr"), col = par("col"), cex = par("cex")
  )
  invisible(NULL)
}
shim$box <- function(...) {
  rec$box <- rec$box + 1L
  graphics::box(...)
  invisible(NULL)
}
pl <- ca::pchlist
environment(pl) <- shim

pl()
p <- rec$plot
fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = "\t")
lines <- c(
  "function\tpchlist",
  "tolerance\t1e-8",
  paste0("plot.x\t", fmt(p$x)),
  paste0("plot.y\t", fmt(p$y)),
  paste0("plot.pch\t", fmt(p$pch)),
  paste0("plot.usr\t", fmt(p$usr)),
  paste0("plot.col\t", p$col),
  paste0("plot.cex\t", fmt(p$cex)),
  paste0("box.count\t", rec$box)
)
writeLines(lines, file.path(out_dir, "pchlist-r-values.txt"))
cat("wrote", file.path(out_dir, "pchlist-r-values.txt"), "\n")
dev.off()

# Data that pchlist draws: 256 points on a 16 x 16 grid, symbol codes 1:256, and
# the plot-region limits from xaxs / yaxs "r" (4% extension). Each timed call runs
# the expression 1000 times; the reported figure is per computation.
points_r <- function() {
  x <- rep(1:16, each = 16)
  y <- rep(1:16, 16)
  pch <- 1:256
  lim <- extendrange(c(1, 16), f = 0.04)
  list(x = x, y = y, pch = pch, lim = lim)
}
inner <- function(f, k = 1000L) {
  for (i in seq_len(k)) f()
  invisible(NULL)
}
time_ms <- function(f, repeats = 20L) {
  f()
  t <- numeric(repeats)
  for (i in seq_len(repeats)) {
    t0 <- Sys.time()
    inner(f)
    # seconds to ms, then divided by the 1000 computations in one timed call
    t[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000 / 1000
  }
  median(t)
}
med <- time_ms(points_r)
writeLines(c(
  "function\tpchlist",
  "timing\tpoints, symbol codes and limits that pchlist draws; 1000 computations per timed call, 1 untimed + 20 timed; reported per computation",
  paste0("median_ms\t", sprintf("%.17g", med))
), file.path(out_dir, "pchlist-r-ms.txt"))
cat("median_ms", med, "\n")
