# R reference for MclustDRsubsel (end to end from banknote). Python: MclustDRsubsel-py.py.
#
# Cases A and B: Mclust path (banknote -> Mclust(G = 3, VEI) -> MclustDR(lambda = 0.7)).
# Case C: EDDA classification path (MclustDRsubsel_classif fixture, iris), which the
# Python port now runs without R. Set MCLUST_CASES (e.g. "C") to run a subset.
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDRsubsel-setup.R"))

# Case C input: the EDDA fixture written for MclustDRsubsel_classif.
cl_meta <- readLines(file.path(proof_dir, "MclustDRsubsel_classif_meta.txt"))
dr_classif <- list(
  type = cl_meta[3],
  x = as.matrix(read.csv(file.path(proof_dir, "MclustDRsubsel_classif_x.csv"), header = FALSE)),
  dir = as.matrix(read.csv(file.path(proof_dir, "MclustDRsubsel_classif_dir.csv"), header = FALSE)),
  numdir = as.integer(cl_meta[1]),
  lambda = as.numeric(cl_meta[2]),
  classification = read.csv(file.path(proof_dir, "MclustDRsubsel_classif_cl.csv"), header = FALSE)[[1]]
)
class(dr_classif) <- "MclustDR"
cases$C <- function(...) MclustDRsubsel(dr_classif, G = 1:2, modelNames = c("EEE", "VEI"), verbose = FALSE)

flatten <- function(sub) {
  k <- sub$numdir
  c(k, sub$lambda,
    as.vector(sub$dir[, seq_len(k), drop = FALSE]),
    as.vector(sub$basisx),
    as.vector(sub$std.basisx),
    as.numeric(sub$classification))
}

timed <- function(f) {
  value <- f()                       # untimed call
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    f()
    elapsed[i] <- as.numeric(Sys.time()) - t0
  }
  list(value = value, r_ms = median(elapsed) * 1000)
}

ids <- strsplit(Sys.getenv("MCLUST_CASES", "A,B,C"), ",")[[1]]
for (id in ids) {
  res <- timed(function() cases[[id]]())
  sub <- res$value
  vals <- flatten(sub)
  con <- file.path(proof_dir, sprintf("MclustDRsubsel-%s-r-values.txt", id))
  writeLines(c(sprintf("r_ms %.17g", res$r_ms), sprintf("%.17g", vals)), con)
  cat(id, "numdir", sub$numdir, "groups", paste(table(sub$classification), collapse = "/"),
      "r_ms", res$r_ms, "\n")
  if (id == "A") {
    writeLines(capture.output(print(sub)), file.path(proof_dir, "../docs/output/MclustDRsubsel-r.txt"))
  }
}
