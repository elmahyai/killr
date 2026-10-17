.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()
E <- mk_recorder("uncerPlot")
cases <- list(
  no_truth = function() E$uncerPlot(fx$z),
  with_truth = function() E$uncerPlot(fx$z, truth = fx$truth)
)
proof_run(E, cases, "with_truth", "uncerPlot", out_dir)
