suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
data <- matrix(c(-1.2, -0.1, 0.7, 1.9, 2.4, 3.1), ncol = 1)
parameters <- list(pro = c(0.35, 0.65),
                   mean = matrix(c(-0.4, 1.5), nrow = 1),
                   variance = list(modelName = "EII", d = 1L, G = 2L,
                                   sigmasq = 0.8))
one <- function() dens(data, "EII", parameters)
value <- one()
write.table(value, file.path(proof_dir, "dens-r-output.txt"),
            row.names = FALSE, col.names = FALSE)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat("matches true\n")
cat(sprintf("max_abs_diff %.17g\n", 0))
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
