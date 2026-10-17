.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
source(file.path(here, "plot_object_io.R"))
source(file.path(here, "plot_mclust_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

E <- mk_mclust_recorder(c("plot.Mclust", "plot.mclustBIC", "mclust1Dplot", "vpoints",
                          "mclust2Dplot", "mvn2plot", "surfacePlot", "coordProj",
                          "plotDensityMclust1", "plotDensityMclustd"), rug = FALSE)
o2 <- read_mclust_object(file.path(here, "plot_object_mclust2d.json"))
o1 <- read_mclust_object(file.path(here, "plot_object_mclust1d.json"))
o3 <- read_mclust_object(file.path(here, "plot_object_mclust3d.json"))

cases <- list(
  all_default_2d = function() E$plot.Mclust(o2),
  bic_2d = function() E$plot.Mclust(o2, what = "BIC"),
  classification_2d = function() E$plot.Mclust(o2, what = "classification"),
  classification_2d_no_ellipses = function()
    E$plot.Mclust(o2, what = "classification", addEllipses = FALSE),
  uncertainty_2d = function() E$plot.Mclust(o2, what = "uncertainty"),
  density_2d = function() E$plot.Mclust(o2, what = "density"),
  classification_1d = function() E$plot.Mclust(o1, what = "classification"),
  uncertainty_1d = function() E$plot.Mclust(o1, what = "uncertainty"),
  classification_3d = function() E$plot.Mclust(o3, what = "classification"),
  classification_3d_no_ellipses = function()
    E$plot.Mclust(o3, what = "classification", addEllipses = FALSE),
  uncertainty_3d = function() E$plot.Mclust(o3, what = "uncertainty"),
  density_1d = function() E$plot.Mclust(o1, what = "density"),
  density_3d = function() E$plot.Mclust(o3, what = "density")
)
# Inside plotDensityMclustd (the d > 2 density panel) the recorder logs what that
# function's own proof logs: the layout, the diagonal labels, the panel axis sides and
# the contour window. Elsewhere these hooks keep the mk_mclust_recorder behaviour.
in_pdm <- function() any(vapply(sys.calls(), function(cl)
  identical(cl[[1]], as.name("plotDensityMclustd")), TRUE))
put2 <- function(tag, ...) {
  E$log <- c(E$log, paste(c(tag, rec_fields(...)), collapse = " "))
  invisible(NULL)
}
base_axis <- E$axis
base_contour <- E$contour
E$par <- function(...) {
  args <- list(...)
  r <- graphics::par(...)
  if (E$mode != "time" && in_pdm() && "mfrow" %in% names(args)) {
    cur <- graphics::par(c("mfrow", "mar", "oma"))
    put2("V", "layout", cur$mfrow, cur$mar, cur$oma)
  }
  invisible(r)
}
E$axis <- function(side, at = NULL, ...) {
  if (E$mode != "time" && in_pdm()) {
    fr <- parent.frame()
    put2("V", "axis", c(get("i", envir = fr), get("j", envir = fr), side))
  } else base_axis(side, at = at, ...)
  invisible(NULL)
}
E$text <- function(x, y = NULL, labels = NULL, ...) {
  if (E$mode != "time" && in_pdm()) put2("T", x, y, labels)
  invisible(NULL)
}
E$contour <- function(x, y, z, levels = NULL, ...) {
  if (E$mode == "time" || !in_pdm()) return(base_contour(x, y, z, levels = levels, ...))
  graphics::contour(x = x, y = y, z = z, levels = levels, ...)
  put2("W", as.numeric(par("usr")))
  put2("C", x, y, as.numeric(z), levels)
  invisible(NULL)
}
proof_run(E, cases, "density_2d", "plot.Mclust", out_dir)
cat("ok plot.Mclust\n")
