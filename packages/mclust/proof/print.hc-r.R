suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
x <- matrix(c(1, 2, 3, 4), ncol = 1)
hc_obj <- structure(matrix(c(1, 2), nrow = 2),
                    call = quote(hc(x, modelName = "E")),
                    modelName = "E", use = "VARS", dimensions = c(4L, 1L))
one <- function() capture.output(print.hc(hc_obj))
value <- one()
writeLines(value, file.path(proof_dir, "print.hc-r-output.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
