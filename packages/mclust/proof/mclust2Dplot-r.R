.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()

E <- mk_recorder(c("mclust2Dplot", "mvn2plot"))
P2 <- list(mean = fx$mu2, variance = list(sigma = fx$sig2))
cases <- list(
  classification = function() E$mclust2Dplot(fx$data2, parameters = P2,
                                             classification = fx$cls),
  classification_fill = function() E$mclust2Dplot(fx$data2, parameters = P2,
                                                  classification = fx$cls,
                                                  fillEllipses = TRUE),
  error = function() E$mclust2Dplot(fx$data2, parameters = P2, classification = fx$cls,
                                    truth = fx$truth, what = "error"),
  uncertainty = function() E$mclust2Dplot(fx$data2, parameters = P2, z = fx$z,
                                          what = "uncertainty")
)
proof_run(E, cases, "classification", "mclust2Dplot", out_dir)

# Figure: the real mclust2Dplot drawing the filled-ellipse case, as an SVG file.
svg(file.path(out_dir, "mclust2Dplot-classification_fill-r.svg"), width = 7, height = 7)
mclust:::mclust2Dplot(fx$data2, parameters = P2, classification = fx$cls,
                      fillEllipses = TRUE)
dev.off()
