.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs as in prelim_mix-r.R. The generator is seeded before the draws.
case_b <- function() {
  n <- 50L
  i <- 1:n
  c1 <- (i %% 3) + 1; c1[4] <- NA
  c2 <- ((i^2) %% 2) + 1
  x1 <- ((((i * 11)) %% 37) - 18) / 4; x1[7] <- NA
  x2 <- ((((i^2) + 3) %% 31) - 15) / 16; x2[20] <- NA
  cbind(c1, c2, x1, x2)
}

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

one <- function() {
  s <- mix::prelim.mix(case_b(), p = 2)
  th <- mix::em.mix(s, showits = FALSE)
  mix::rngseed(4242)
  da <- mix::da.mix(s, th, steps = 100, showits = FALSE)
  c(num(da$sigma), num(da$mu), num(da$pi))
}

value <- one()
elapsed <- numeric(20)
for (k in 1:20) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
