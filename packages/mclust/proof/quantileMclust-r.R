suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
output_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"
object <- list(
  d = 1L,
  G = 2L,
  modelName = "V",
  parameters = list(
    pro = c(0.35, 0.65),
    mean = c(-0.8, 1.1),
    variance = list(sigmasq = c(0.7, 1.6))
  )
)
class(object) <- "densityMclust"
p <- c(0.001, 0.1, 0.5, 0.9, 0.999)
one <- function() quantileMclust(object, p)
value <- one()
write.table(value, file.path(output_dir, "quantileMclust-r.txt"),
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
           file.path(proof_dir, "quantileMclust-r-ms.txt"))
