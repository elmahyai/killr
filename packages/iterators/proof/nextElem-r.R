suppressPackageStartupMessages(library(iterators))

one <- function() {
  it <- iter(c("a", "b", "c"))
  ch <- c(nextElem(it), nextElem(it), nextElem(it))
  e <- tryCatch(nextElem(it), error = function(e) conditionMessage(e))
  it <- iter(c(4, 5, 6))
  n <- c(nextElem(it), nextElem(it), nextElem(it))
  it <- icount(2)
  k <- c(nextElem(it), nextElem(it))
  ek <- tryCatch(nextElem(it), error = function(e) conditionMessage(e))
  m <- matrix(1:6, nrow = 2)
  it <- iter(m, by = "column", chunksize = 2)
  p1 <- as.vector(nextElem(it))
  p2 <- as.vector(nextElem(it))
  it <- iter(function(i) i * 10)
  f <- c(nextElem(it), nextElem(it))
  it <- iter(1:5, checkFunc = function(i) i != 3)
  sk <- c(nextElem(it), nextElem(it), nextElem(it), nextElem(it))
  paste(c(
    ch, e,
    sprintf("%.17g", n),
    sprintf("%.17g", k), ek,
    sprintf("%.17g", p1),
    sprintf("%.17g", p2),
    sprintf("%.17g", f),
    sprintf("%.17g", sk)
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
