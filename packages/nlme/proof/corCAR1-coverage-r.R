.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# Same inputs as corCAR1-coverage-py.py.
dat <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b"),
  t = c(1, 2, 3, 4, 1, 2, 4)
)
con <- list(Xy = matrix(as.double(1:14), 7, 2), logLik = 0.5)

timed <- function(f) {
  value <- as.numeric(f())
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    f()
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  list(value = value, median_ms = median(elapsed) * 1000)
}
emit <- function(res) {
  parts <- vapply(names(res), function(n) {
    sprintf("\"%s\":{\"value\":[%s],\"median_ms\":%.17g}", n,
            paste(sprintf("%.17g", res[[n]]$value), collapse = ","),
            res[[n]]$median_ms)
  }, "")
  cat("{", paste(parts, collapse = ","), "}\n", sep = "")
}

make_a <- function() Initialize(corCAR1(0.2, form = ~ t | Subject), dat)
make_b <- function() Initialize(corCAR1(0.7, form = ~ t | Subject), dat)

init_fn <- function() {
  a <- make_a()
  b <- make_b()
  c(as.vector(a), as.vector(b))
}
logdet_fn <- function() {
  a <- make_a()
  b <- make_b()
  c(logDet(a), logDet(b))
}
recalc_fn <- function() {
  ra <- recalc(make_a(), con)
  rb <- recalc(make_b(), con)
  c(as.vector(ra$Xy), ra$logLik, as.vector(rb$Xy), rb$logLik)
}

emit(list(
  Initialize = timed(init_fn),
  logDet = timed(logdet_fn),
  recalc = timed(recalc_fn)
))
