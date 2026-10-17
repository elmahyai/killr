.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()
E <- mk_recorder("mvn2plot")
cases <- list(
  default = function() {
    E$plot(c(-2, 2), c(-2, 2), type = "n")
    E$mvn2plot(mu = fx$mu2[, 1], sigma = fx$sig2[, , 1])
  },
  fill = function() {
    E$plot(c(-2, 2), c(-2, 2), type = "n")
    E$mvn2plot(mu = fx$mu2[, 2], sigma = fx$sig2[, , 2], fillEllipse = TRUE)
  },
  alone = function() E$mvn2plot(mu = fx$mu2[, 3], sigma = fx$sig2[, , 3], alone = TRUE)
)
proof_run(E, cases, "default", "mvn2plot", out_dir)
