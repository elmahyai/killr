.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
source(file.path(here, "plot_object_io.R"))
source(file.path(here, "plot_mclust_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

E <- mk_mclust_recorder("densityMclust.diagnostic")
d1 <- read_mclust_object(file.path(here, "plot_object_density1d.json"))
d2 <- read_mclust_object(file.path(here, "plot_object_density2d.json"))

cases <- list(
  cdf_qq_1d = function() E$densityMclust.diagnostic(d1),
  cdf_only_1d = function() E$densityMclust.diagnostic(d1, type = "cdf"),
  qq_only_1d = function() E$densityMclust.diagnostic(d1, type = "qq"),
  multivariate_no_draw = function() suppressWarnings(E$densityMclust.diagnostic(d2))
)
proof_run(E, cases, "cdf_qq_1d", "densityMclust.diagnostic", out_dir)
cat("ok densityMclust.diagnostic\n")
