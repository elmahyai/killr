suppressPackageStartupMessages(library(iterators))

err <- function(expr) {
  tryCatch({
    force(expr)
    "OK"
  }, error = function(e) conditionMessage(e))
}

take <- function(it, k = 16) {
  out <- character()
  for (i in seq_len(k)) {
    hit <- tryCatch(list(v = nextElem(it)), error = function(e) list(e = conditionMessage(e)))
    if (!is.null(hit$e)) {
      out <- c(out, hit$e)
      break
    }
    out <- c(out, sprintf("%.17g", as.numeric(hit$v)))
  }
  out
}

one <- function() {
  p <- idiv(10, chunks = 3)
  q <- idiv(10, chunks = 3)
  ind <- c(nextElem(p), nextElem(q), nextElem(p))
  base <- idiv(10, chunks = 2)
  same <- if (identical(base, iter(base))) "SAME" else "DIFF"
  paste(c(
    take(idiv(10, chunks = 3)),
    take(idiv(10, chunkSize = 3)),
    take(idiv(10.5, chunks = 3)),
    take(idiv(10, chunks = 2.5)),
    take(idiv(10, chunkSize = 2.5)),
    take(idiv(5, chunks = 4)),
    take(idiv(2.2, chunkSize = 1.1)),
    take(idiv(7, chunkSize = 3)),
    take(idiv(3, chunkSize = 2)),
    take(idiv(9, chunkSize = 4)),
    take(idiv(1, chunks = 3)),
    take(idiv(10, chunkSize = 11)),
    take(idiv(4, chunkSize = 1)),
    take(idiv(10, chunks = 1)),
    take(idiv(0, chunks = 3)),
    take(idiv(-4, chunks = 3)),
    take(idiv(10, chunks = 0)),
    take(idiv(10, chunks = -2)),
    take(idiv(10, chunks = 0.4)),
    take(idiv(1e16 + 3, chunks = 3)),
    take(idiv(Inf, chunks = 3)),
    take(idiv(Inf, chunkSize = 3)),
    take(idiv(10, chunkSize = Inf)),
    take(idiv(NA_real_, chunks = 3)),
    take(idiv(NA_real_, chunkSize = 3)),
    take(idiv(-10, chunkSize = 3)),
    take(idiv(0, chunkSize = 3)),
    take(idiv(-0, chunks = 3)),
    sprintf("%.17g", ind),
    same,
    take(base),
    take(idiv(c(10), chunks = 3)),
    take(idiv(10, chunks = c(3))),
    take(idiv(10, chunkSize = c(3))),
    take(idiv(10, chunks = TRUE)),
    take(idiv(10, chunks = FALSE)),
    take(idiv(10, chunks = "0")),
    take(idiv(10, chunks = "3")),
    take(idiv(10, chunks = NULL)),
    take(idiv(-4, chunks = NULL)),
    take(idiv(10, chunks = numeric(0))),
    take(idiv(-4, chunks = numeric(0))),
    take(idiv(10, chunks = c(3, 4))),
    take(idiv(10, chunks = NA_real_)),
    take(idiv(n = 10, chunkSize = 3)),
    err(idiv(10)),
    err(idiv(10, chunks = 3, chunkSize = 2)),
    err(idiv(10, 3)),
    err(idiv(NULL, chunks = 3)),
    err(idiv(TRUE, chunks = 3)),
    err(idiv("10", chunks = 3)),
    err(idiv(c(1, 2), chunks = 3)),
    err(idiv(c(TRUE), chunks = 3)),
    err(idiv(numeric(0), chunks = 3)),
    err(idiv(10, chunkSize = 0)),
    err(idiv(10, chunkSize = 0.5)),
    err(idiv(10, chunkSize = -1)),
    err(idiv(10, chunkSize = NA_real_)),
    err(idiv(10, chunkSize = NaN)),
    err(idiv(10, chunkSize = NULL)),
    err(idiv(10, chunkSize = "3")),
    err(idiv(10, chunkSize = c(3, 4))),
    err(idiv(10, chunkSize = TRUE)),
    err(idiv(10, chunkSize = -Inf)),
    err(idiv(chunks = 3)),
    err(idiv(10, foo = 1, chunks = 3)),
    err(idiv(10, chunksize = 3)),
    err(idiv(10, chunk = 3)),
    err(idiv(10, n = 11, chunks = 3)),
    err(idiv(10, 1, chunkSize = 0)),
    err(idiv(TRUE, chunkSize = 0)),
    err(idiv("x", chunks = 3, chunkSize = 1))
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
