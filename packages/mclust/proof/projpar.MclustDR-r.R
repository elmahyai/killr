suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))

flatten_par <- function(par) {
  c(as.numeric(par$mean), as.numeric(par$variance))
}

one <- function() {
  dr <- MclustDR(mod, lambda = 0.7)
  p1 <- projpar.MclustDR(dr)
  p2 <- projpar.MclustDR(dr, dim = c(1, 2), center = TRUE, raw = FALSE)
  p3 <- projpar.MclustDR(dr, dim = 1, center = FALSE, raw = TRUE)
  c(flatten_par(p1), flatten_par(p2), flatten_par(p3))
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
