.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "cdens-fixtures.R"))

one <- function() list(
  mclust:::cdensE(x1, logarithm = TRUE, parameters = pars_E),
  mclust:::cdensE(x1, logarithm = FALSE, parameters = pars_E),
  mclust:::cdensE(x1, logarithm = TRUE, parameters = pars_E_missing),
  mclust:::cdensE(x1, logarithm = TRUE, parameters = pars_E_vanish)
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
