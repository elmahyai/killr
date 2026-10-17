.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "sim-core-fixtures.R"))

# Each case is a draw, then runif(2) from the stream the call left behind.
step <- function(res) c(emit(res), runif(2))

one <- function() {
  out <- numeric(0)
  out <- c(out, step(suppressWarnings(mclust:::sim("E", pars_E, 60, seed = 42))))
  out <- c(out, step(suppressWarnings(mclust:::sim("X", pars_E_nopro, 45, seed = 7))))
  out <- c(out, step(suppressWarnings(mclust:::sim("V", pars_V, 300, seed = 2024))))
  out <- c(out, step(suppressWarnings(mclust:::sim("XII", pars_EII, 60, seed = 42))))
  out <- c(out, step(suppressWarnings(mclust:::sim("XXI", pars_EEI, 45, seed = 7))))
  out <- c(out, step(suppressWarnings(mclust:::sim("XXX", pars_EEE, 300, seed = 2024))))
  out <- c(out, step(suppressWarnings(mclust:::sim("EEV", pars_EEV, 60, seed = 42))))
  out <- c(out, step(suppressWarnings(mclust:::sim("EVI", pars_EVI, 45, seed = 7))))
  out <- c(out, step(suppressWarnings(mclust:::sim("VEI", pars_VEI, 300, seed = 2024))))
  out <- c(out, step(suppressWarnings(mclust:::sim("EEE", pars_EEE_missing, 10, seed = 1))))
  out
}

value <- one()
print_values(value)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
