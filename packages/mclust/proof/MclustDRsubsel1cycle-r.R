.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))
dr <- MclustDR(mod, lambda = 0.7)
dr$dir <- as.matrix(read.csv(file.path(proof_dir, "MclustDRsubsel_dir.csv"), header = FALSE))
dr$numdir <- ncol(dr$dir)
colnames(dr$dir) <- paste0("Dir", seq_len(dr$numdir))

flatten <- function(out) {
  tab <- out$tab
  c(out$subset, as.numeric(tab$G), as.numeric(tab$BIC), as.numeric(tab$`BIC.dif`))
}

one <- function() flatten(MclustDRsubsel1cycle(dr, G = 1:3, modelNames = c("VEI", "EEE"), verbose = FALSE))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
