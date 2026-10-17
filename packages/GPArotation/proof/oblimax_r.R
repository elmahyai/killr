# R reference for GPArotation::oblimax (cran_version 2026.8-2).
# Writes one CSV row per case: case, median_ms, iterations, criterion, loadings (column-major), Phi (column-major).
# Run from the repository root:  Rscript packages/GPArotation/proof/oblimax_r.R
library(GPArotation)
stopifnot(as.character(packageVersion("GPArotation")) == "2026.8.2")

A <- matrix(c(.8,.1,.2, .2,.7,.1, .1,.2,.9, .6,.2,.3, .2,.8,.4), 5, 3, byrow = TRUE)
Tm <- matrix(c(1,.1,0, 0,1,.2, .1,0,1), 3, 3, byrow = TRUE)

cases <- list(
  default   = function() GPArotation:::oblimax(A),
  normalize = function() GPArotation:::oblimax(A, normalize = TRUE),
  tmat      = function() GPArotation:::oblimax(A, Tmat = Tm)
)

rows <- character()
for (nm in names(cases)) {
  r <- cases[[nm]]()                       # untimed call
  z <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    cases[[nm]]()
    z[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  iters <- r$Table[nrow(r$Table), "iter"]
  f     <- r$Table[nrow(r$Table), "f"]
  vals  <- c(as.numeric(r$loadings), as.numeric(r$Phi))
  rows  <- c(rows, paste(c(nm, sprintf("%.10f", median(z)), sprintf("%d", iters),
                           sprintf("%.17g", f), sprintf("%.17g", vals)), collapse = ","))
}
writeLines(rows, "packages/GPArotation/docs/output/oblimax_r.csv")
cat(rows, sep = "\n")
