.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()
E <- mk_recorder("clPairs")
cases <- list(
  d3 = function() E$clPairs(fx$data3, classification = fx$cls),
  d2 = function() E$clPairs(fx$data2, classification = fx$cls)
)
proof_run(E, cases, "d3", "clPairs", out_dir)
