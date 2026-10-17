.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  simulate.lme(
    list(
      fixed = distance ~ age,
      data = Orthodont,
      random = ~1 | Subject
    ),
    nsim = 3,
    seed = 42,
    m2 = list(random = ~age | Subject)
  )
}

fingerprint <- function(sim) {
  c(
    attr(sim, "df"),
    as.numeric(attr(sim, "useGen")),
    attr(sim, "seed"),
    as.vector(t(sim$null$REML)),
    as.vector(t(sim$null$ML)),
    as.vector(t(sim$alt$REML)),
    as.vector(t(sim$alt$ML))
  )
}

value <- fingerprint(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  fingerprint(one())
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
