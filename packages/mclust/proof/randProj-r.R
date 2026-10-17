.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))
fx <- make_fixtures()

E <- mk_recorder(c("randProj", "mvn2plot"))
P3 <- list(mean = fx$mu3, variance = list(sigma = fx$sig3))

# Logs the projection the function returns, column-major, after its drawing.
values_of <- function(res) {
  E$value("basis", res$basis)
  E$value("data", res$data)
  E$value("mu", res$mu)
  E$value("sigma", res$sigma)
}
cases <- list(
  classification = function() {
    res <- E$randProj(fx$data3, seeds = 42, parameters = P3, classification = fx$cls)
    values_of(res)
  },
  error = function() {
    res <- E$randProj(fx$data3, seeds = c(42, 7), parameters = P3, classification = fx$cls,
                      truth = fx$truth, what = "error")
    values_of(res)
  },
  uncertainty = function() {
    res <- E$randProj(fx$data3, seeds = 3, parameters = P3, z = fx$z, what = "uncertainty")
    values_of(res)
  },
  scale = function() {
    res <- E$randProj(fx$data3, seeds = 42, parameters = P3, classification = fx$cls,
                      scale = TRUE)
    values_of(res)
  }
)
proof_run(E, cases, "classification", "randProj", out_dir)
