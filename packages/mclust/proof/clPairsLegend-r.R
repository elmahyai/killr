.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()
E <- mk_recorder("clPairsLegend")
cases <- list(
  legend = function() {
    E$plot(c(0, 1), c(0, 1), type = "n")
    E$clPairsLegend(0.1, 0.9, class = c("1", "2", "3"),
                    col = c("black", "red", "blue"), pch = c(1, 2, 3), cex = 1)
  }
)
proof_run(E, cases, "legend", "clPairsLegend", out_dir)
