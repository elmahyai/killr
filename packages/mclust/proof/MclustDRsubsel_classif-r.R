.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
dr <- list(
  type = readLines(file.path(proof_dir, "MclustDRsubsel_classif_meta.txt"))[3],
  x = as.matrix(read.csv(file.path(proof_dir, "MclustDRsubsel_classif_x.csv"), header = FALSE)),
  dir = as.matrix(read.csv(file.path(proof_dir, "MclustDRsubsel_classif_dir.csv"), header = FALSE)),
  numdir = as.integer(readLines(file.path(proof_dir, "MclustDRsubsel_classif_meta.txt"))[1]),
  lambda = as.numeric(readLines(file.path(proof_dir, "MclustDRsubsel_classif_meta.txt"))[2]),
  classification = read.csv(file.path(proof_dir, "MclustDRsubsel_classif_cl.csv"), header = FALSE)[[1]]
)
class(dr) <- "MclustDR"

one <- function() {
  out <- MclustDRsubsel_classif(dr, G = 1:2, modelNames = c("EEE", "VEI"), verbose = FALSE)
  c(out$numdir, out$lambda, as.vector(out$basisx))
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
