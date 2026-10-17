.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()

E <- mk_recorder("surfacePlot")
PS <- list(pro = fx$pro, mean = fx$mu2, variance = list(sigma = fx$sig2))
PS2 <- list(pro = c(0.4, 0.6), mean = fx$mu2[, 1:2],
            variance = list(sigma = fx$sig2[, , 1:2]))
# A fixed two-colour palette, so the image colours can be compared exactly.
pal <- function(n) rep_len(c("#1E90FF", "#FFA500"), n)
cases <- list(
  contour_density = function() {
    r <- E$surfacePlot(fx$data2, PS); E$value("x", r$x); E$value("y", r$y); E$value("z", r$z)
  },
  contour_uncertainty = function() {
    r <- E$surfacePlot(fx$data2, PS, what = "uncertainty")
    E$value("x", r$x); E$value("y", r$y); E$value("z", r$z)
  },
  hdr_density = function() {
    r <- E$surfacePlot(fx$data2, PS, type = "hdr")
    E$value("x", r$x); E$value("y", r$y); E$value("z", r$z)
  },
  image_density = function() {
    r <- E$surfacePlot(fx$data2, PS, type = "image", col.palette = pal)
    E$value("x", r$x); E$value("y", r$y); E$value("z", r$z)
  },
  persp_density = function() {
    r <- E$surfacePlot(fx$data2, PS, type = "persp", grid = 25, nlevels = 1)
    E$value("x", r$x); E$value("y", r$y); E$value("z", r$z)
  },
  swap_axes = function() {
    r <- E$surfacePlot(fx$data2, PS2, swapAxes = TRUE, grid = 25)
    E$value("x", r$x); E$value("y", r$y); E$value("z", r$z)
  }
)
proof_run(E, cases, "contour_density", "surfacePlot", out_dir)
for (nm in names(cases)) {
  ms <- time_median_ms(E, cases[[nm]])
  writeLines(sprintf("%.17g", ms),
             file.path(out_dir, paste0("surfacePlot-", nm, "-r-time.txt")))
}
