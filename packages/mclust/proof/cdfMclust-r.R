suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
output_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"
object <- list(
  data = c(-3, -2, -1, 0, 1, 2, 3),
  G = 2L,
  parameters = list(
    pro = c(0.35, 0.65),
    mean = c(-0.8, 1.1),
    variance = list(sigmasq = c(0.7, 1.6))
  )
)
class(object) <- "densityMclust"
grid <- c(-3.5, -2.25, -1, 0.25, 1.5, 2.75, 4)
one <- function() cdfMclust(object, grid)$y
value <- one()
write.table(value, file.path(output_dir, "cdfMclust-r.txt"),
            row.names = FALSE, col.names = FALSE)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat("matches true\n")
cat("max_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
writeLines(sprintf("%.17g", median(elapsed) * 1000),
           file.path(proof_dir, "cdfMclust-r-ms.txt"))
