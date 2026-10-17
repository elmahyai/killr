suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

collect <- function(out) {
  c(
    as.numeric(out$CI),
    if (!is.null(out$test.difference)) as.numeric(out$test.difference) else numeric(0),
    if (!is.null(out$test.slope.wald)) {
      c(
        out$test.slope.wald,
        out$test.slope.lr,
        out$test.slope.score.logdose,
        out$test.slope.score.dose
      )
    } else {
      numeric(0)
    }
  )
}

one <- function() {
  dose <- c(50, 100, 200, 400, 800)
  responses <- c(2, 6, 9, 15, 21)
  tested <- c(24, 24, 24, 24, 24)
  g1 <- collect(elda(responses, dose, tested, test.unit.slope = TRUE))
  responses2 <- c(responses, c(1, 3, 5, 8, 12))
  dose2 <- c(dose, dose)
  tested2 <- c(tested, tested)
  group2 <- c(rep(1, 5), rep(2, 5))
  g2 <- collect(elda(responses2, dose2, tested2, group = group2, test.unit.slope = TRUE))
  g3 <- collect(
    elda(
      c(0, 2, 6, 9, 15),
      c(50, 100, 200, 400, 800),
      c(24, 24, 24, 24, 24),
      test.unit.slope = FALSE
    )
  )
  c(g1, g2, g3)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
