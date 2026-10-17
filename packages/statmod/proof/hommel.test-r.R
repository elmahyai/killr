suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  p1 <- c(
    0.00023889658041298389, 0.0015705542173236609, 0.00394833879545331,
    0.0073341468814760447, 0.0078847387339919806, 0.037431032862514257,
    0.038936491124331951, 0.042988796019926667, 0.082437558099627495,
    0.085612064925953746
  )
  r1 <- as.numeric(hommel.test(p1))
  p2 <- c(0.001, 0.01, 0.04, 0.05, 0.06, 0.5)
  r2 <- as.numeric(hommel.test(p2, alpha = 0.05))
  p3 <- matrix(c(0.02, 0.9, 0.03, 0.8), nrow = 2)
  r3 <- as.numeric(hommel.test(p3, alpha = 0.1))
  r4 <- as.numeric(hommel.test(c(0.05, 0.05, 0.05, 0.05)))
  c(r1, r2, r3, r4)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", value), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
