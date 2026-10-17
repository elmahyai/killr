suppressPackageStartupMessages(library(mclust))
proof <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof, "MclustDR-export.R"))
one <- function() {
  dr <- MclustDR(mod, lambda = 0.7)
  p <- predict(dr, dim = c(1, 2), newdata = mod$data[1:6, ])
  c(p$density, p$z, p$uncertainty, as.integer(p$classification))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
writeLines(sprintf("%.17g", value), file.path(proof, "predict.MclustDR-r-values.txt"))
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(proof, "predict.MclustDR-r-ms.txt"))
