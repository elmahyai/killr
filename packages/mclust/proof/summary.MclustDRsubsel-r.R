# R reference for summary.MclustDRsubsel (end to end from banknote). Python: summary.MclustDRsubsel-py.py.
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "MclustDRsubsel-setup.R"))

flatten <- function(s) {
  c(as.numeric(s$n), s$G, as.numeric(s$basis), as.numeric(s$std.basis),
    as.numeric(s$evalues), as.numeric(s$evalues.cumperc))
}

for (id in names(cases)) {
  sub <- cases[[id]]()                 # subset fit, outside the timed call
  one <- function() summary(sub)
  s <- one()                           # untimed call
  vals <- flatten(s)
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one()
    elapsed[i] <- as.numeric(Sys.time()) - t0
  }
  r_ms <- median(elapsed) * 1000
  writeLines(c(sprintf("r_ms %.17g", r_ms), sprintf("%.17g", vals)),
             file.path(proof_dir, sprintf("summary.MclustDRsubsel-%s-r-values.txt", id)))
  cat(id, "r_ms", r_ms, "\n")
  if (id == "A") {
    writeLines(capture.output(print(s)), file.path(proof_dir, "../docs/output/summary.MclustDRsubsel-r.txt"))
  }
}
