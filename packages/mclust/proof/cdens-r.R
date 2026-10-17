.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "cdens-fixtures.R"))

one <- function() list(
  mclust:::cdens(x1, "E", pars_E, logarithm = TRUE),
  mclust:::cdens(x1, "X", pars_E, logarithm = TRUE),
  mclust:::cdens(X, "EII", pars_EII, logarithm = TRUE),
  mclust:::cdens(X, "XII", pars_EII, logarithm = FALSE),
  mclust:::cdens(X, "EEI", pars_EEI, logarithm = TRUE),
  mclust:::cdens(X, "XXI", pars_EEI, logarithm = FALSE),
  mclust:::cdens(X, "EVI", pars_EVI, logarithm = TRUE),
  mclust:::cdens(X, "EEV", pars_EEV, logarithm = TRUE),
  mclust:::cdens(X, "EEE", pars_EEE, logarithm = TRUE),
  mclust:::cdens(X, "XXX", pars_EEE, logarithm = FALSE)
)

value <- one()
print_values(unlist(lapply(value, emit)))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
