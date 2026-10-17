.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
G <- 6
mod <- list(
  data = as.matrix(read.table(file.path(proof_dir, "clustCombi_data.csv"))),
  z = as.matrix(read.table(file.path(proof_dir, "clustCombi_z.csv"))),
  G = G
)
class(mod) <- "Mclust"

flatten <- function(out) {
  vals <- c()
  for (k in G:1) vals <- c(vals, as.vector(out$combiz[[k]]))
  for (k in (G - 1):1) vals <- c(vals, as.vector(out$combiM[[k]]))
  for (k in G:1) vals <- c(vals, out$classification[[k]])
  vals
}

one <- function() flatten(clustCombi(mod))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
