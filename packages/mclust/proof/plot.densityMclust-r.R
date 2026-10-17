.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
source(file.path(here, "plot_object_io.R"))
source(file.path(here, "plot_mclust_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

E <- mk_mclust_recorder(c("plot.densityMclust", "plot.mclustBIC", "densityMclust.diagnostic",
                          "plotDensityMclust1", "plotDensityMclust2", "surfacePlot"))
d1 <- read_mclust_object(file.path(here, "plot_object_density1d.json"))
d2 <- read_mclust_object(file.path(here, "plot_object_density2d.json"))

cases <- list(
  bic_1d = function() E$plot.densityMclust(d1, what = "BIC"),
  diagnostic_1d = function() E$plot.densityMclust(d1, what = "diagnostic"),
  bic_and_diagnostic_1d = function() E$plot.densityMclust(d1, what = c("BIC", "diagnostic")),
  density_1d = function() E$plot.densityMclust(d1, what = "density"),
  density_2d = function() E$plot.densityMclust(d2, what = "density")
)
proof_run(E, cases, "diagnostic_1d", "plot.densityMclust", out_dir)
cat("ok plot.densityMclust\n")
