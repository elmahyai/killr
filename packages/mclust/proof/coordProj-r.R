.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()

E <- mk_recorder(c("coordProj", "mvn2plot"))
P3 <- list(mean = fx$mu3, variance = list(sigma = fx$sig3))
cases <- list(
  classification = function() E$coordProj(fx$data3, dimens = c(1, 2), parameters = P3,
                                          classification = fx$cls),
  error = function() E$coordProj(fx$data3, dimens = c(2, 3), parameters = P3,
                                 classification = fx$cls, truth = fx$truth, what = "error"),
  uncertainty = function() E$coordProj(fx$data3, dimens = c(1, 3), parameters = P3,
                                       z = fx$z, what = "uncertainty")
)
proof_run(E, cases, "classification", "coordProj", out_dir)
