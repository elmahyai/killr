# RNG check for the sim translations: R's stream for rnorm, runif, rexp, and sample(prob = ).
# The Python twin is sim-rng-py.py. Each value is printed one per line, then the median time in ms.

# Each block is one seed, drawn with the same generator call in both languages.
one <- function() {
  out <- numeric(0)
  for (s in c(42L, 1L, 2024L)) {
    set.seed(s); out <- c(out, rnorm(500))
    set.seed(s); out <- c(out, runif(500))
    set.seed(s); out <- c(out, rexp(500))
    set.seed(s); out <- c(out, sample(1:3, 300, replace = TRUE, prob = c(0.2, 0.3, 0.5)))
    # Equal probabilities are ties, so the revsort order decides which category is picked.
    set.seed(s); out <- c(out, sample(1:3, 300, replace = TRUE, prob = rep(1 / 3, 3)))
    set.seed(s); out <- c(out, sample(1:5, 200, replace = TRUE, prob = c(0.1, 0.4, 0.1, 0.4, 0)))
    # rnorm with sd = 0 returns the mean and consumes no uniform, so the next runif is unchanged.
    set.seed(s); z <- rnorm(3, mean = 0, sd = 0); out <- c(out, runif(2))
  }
  out
}

value <- one()
cat(sprintf("%.17g\n", value), sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
