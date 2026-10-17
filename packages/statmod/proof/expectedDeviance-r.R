suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

collect <- function(ed) c(ed$mean, ed$variance)

one <- function() {
  parts <- list(
    collect(expectedDeviance(mu = 3, family = "poisson")),
    collect(expectedDeviance(mu = 0.01, family = "binomial", binom.size = 10)),
    collect(expectedDeviance(mu = 10, family = "Gamma", gamma.shape = 5)),
    collect(expectedDeviance(mu = 10, family = "negative.binomial", nbinom.size = 5)),
    collect(expectedDeviance(mu = c(0.5, 2, 7), family = "gaussian")),
    collect(expectedDeviance(mu = c(0, 1.5, 4), family = "inverse.gaussian")),
    collect(
      expectedDeviance(
        mu = exp(seq(log(0.01), log(50), length.out = 30)),
        family = "poisson"
      )
    ),
    collect(
      expectedDeviance(
        mu = seq(0.001, 0.11, length.out = 40),
        family = "binomial",
        binom.size = 10
      )
    ),
    collect(
      expectedDeviance(
        mu = c(0.2, 1, 5, 20, 100),
        family = "negative.binomial",
        nbinom.size = c(0.1, 0.5, 2, 10, 50)
      )
    )
  )
  unlist(parts)
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
