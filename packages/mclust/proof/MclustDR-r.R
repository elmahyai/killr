suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDR-export.R"))

# Fields compared with the translated MclustDR. The classification field is
# R's factor of per-observation labels; as.integer() gives its codes.
values_of <- function(dr) {
  c(
    as.numeric(dr$numdir),
    as.numeric(dr$lambda),
    as.numeric(dr$evalues),
    as.numeric(dr$dir),
    as.numeric(dr$basis),
    as.numeric(dr$std.basis),
    as.numeric(dr$M),
    as.numeric(dr$M.I),
    as.numeric(dr$M.II),
    as.numeric(dr$pro),
    as.numeric(dr$class2mixcomp),
    as.numeric(dr$mixcomp),
    as.numeric(as.integer(dr$classification))
  )
}

one <- function() {
  dr <- MclustDR(mod, lambda = 0.7)
  values_of(dr)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", value), file.path(proof_dir, "MclustDR-r-values.txt"))
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(proof_dir, "MclustDR-r-ms.txt"))
writeLines(sprintf("%.17g", value), file.path(proof_dir, "../docs/output/MclustDR-r.txt"))
cat("n_values", length(value), "\n")
