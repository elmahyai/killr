suppressPackageStartupMessages(library(iterators))

err <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e))
}

one <- function() {
  it <- icount(3)
  a <- c(nextElem(it), nextElem(it), nextElem(it))
  e1 <- err(nextElem(it))
  it <- icount(2.5)
  b <- c(nextElem(it), nextElem(it), nextElem(it))
  e2 <- err(nextElem(it))
  it <- icount()
  c0 <- c(nextElem(it), nextElem(it))
  e3 <- err(icount(NULL))
  e4 <- err(icount(c(1, 2)))
  e5 <- err(icount(TRUE))
  it <- icount(NA_real_)
  e6 <- err(nextElem(it))
  it <- icount(0)
  e7 <- err(nextElem(it))
  it <- icount(-3)
  e8 <- err(nextElem(it))
  it <- icount(1)
  onev <- nextElem(it)
  e9 <- err(nextElem(it))
  p <- icount(2)
  q <- icount(2)
  ind <- c(nextElem(p), nextElem(q), nextElem(p))
  paste(c(
    sprintf("%.17g", a), e1,
    sprintf("%.17g", b), e2,
    sprintf("%.17g", c0),
    e3, e4, e5, e6, e7, e8,
    sprintf("%.17g", onev), e9,
    sprintf("%.17g", ind)
  ), collapse = "|")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
