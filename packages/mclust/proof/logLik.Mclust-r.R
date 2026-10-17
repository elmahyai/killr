.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))

one <- function() {
  ll <- logLik(mod)
  c(as.numeric(ll), attr(ll, "df"), attr(ll, "nobs"))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
