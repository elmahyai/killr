suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "plot_trace.R"))

# Fixtures: written once so the Python proof reads the same numbers.
X3 <- matrix(c(1,2,3, 2,1,4, 4,3,2, 5,4,1, 6,2,3, 7,5,2), 6, 3, byrow = TRUE)
cl3 <- c("a", "a", "b", "b", "c", "c")
set.seed(2026)
X4 <- matrix(rnorm(40 * 4), 40, 4)
cl4 <- rep(c("w", "x", "y", "z"), each = 10)
cl2 <- rep(c("p", "q"), each = 20)
write.table(X3, file.path(proof_dir, "plot.crimcoords_X3.csv"), sep = ",", row.names = FALSE, col.names = FALSE)
write.table(X4, file.path(proof_dir, "plot.crimcoords_X4.csv"), sep = ",", row.names = FALSE, col.names = FALSE)
writeLines(c(cl3), file.path(proof_dir, "plot.crimcoords_cl3.txt"))
writeLines(c(cl4), file.path(proof_dir, "plot.crimcoords_cl4.txt"))
writeLines(c(cl2), file.path(proof_dir, "plot.crimcoords_cl2.txt"))

cases <- list(
  d2_three_classes = list(X = X3, cl = cl3),
  pairs_d3_four_classes = list(X = X4, cl = cl4),
  hist_numdir1_two_classes = list(X = X4, cl = cl2)
)

out <- character(0)
pdf(NULL)
for (nm in names(cases)) {
  obj <- crimcoords(cases[[nm]]$X, cases[[nm]]$cl)
  cat(nm, "numdir", ncol(obj$projection), "\n")
  trace_start()
  plot.crimcoords(obj)
  trace_stop()
  out <- c(out, paste0("#CASE\t", nm), .LOG$out)
}
dev.off()
writeLines(out, file.path(proof_dir, "plot.crimcoords-r-log.txt"))

# Timing: the data computation of the one-direction plot. That is the
# breaks from pretty(nclass.Sturges(...)) and the histogram densities for
# each class. The drawing is not timed.
obj1 <- crimcoords(X4, cl2)
one <- function() {
  proj <- obj1$projection
  br <- pretty(proj, n = nclass.Sturges(proj))
  x <- split(proj[, 1], obj1$classification)
  lapply(x, function(v) hist(v, breaks = br, plot = FALSE)$density)
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(proof_dir, "plot.crimcoords-r-ms.txt"))
cat("ok\n")
