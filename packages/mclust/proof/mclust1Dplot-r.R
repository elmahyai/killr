.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()

E <- mk_recorder(c("mclust1Dplot", "vpoints"))
x1 <- fx$data3[, 1]
P1 <- list(mean = matrix(c(0.2, 2.4, 1.1), nrow = 1), pro = fx$pro,
           variance = list(sigmasq = c(0.8, 0.5, 0.6), G = 3))
cases <- list(
  classification = function() E$mclust1Dplot(x1, classification = fx$cls),
  error = function() E$mclust1Dplot(x1, classification = fx$cls, truth = fx$truth,
                                    what = "error"),
  uncertainty = function() E$mclust1Dplot(x1, z = fx$z, what = "uncertainty"),
  density = function() E$mclust1Dplot(x1, parameters = P1, what = "density")
)
proof_run(E, cases, "density", "mclust1Dplot", out_dir)
