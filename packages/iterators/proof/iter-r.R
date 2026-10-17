suppressPackageStartupMessages(library(iterators))

num <- function(x) {
  if (is.matrix(x)) x <- as.vector(x)
  if (is.data.frame(x)) x <- as.numeric(unlist(x, use.names = FALSE))
  if (is.list(x)) x <- unlist(x, use.names = FALSE)
  paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
}

err <- function(expr) {
  tryCatch({
    force(expr)
    "OK"
  }, error = function(e) conditionMessage(e))
}

one <- function() {
  it <- iter(c(1, 2, 3))
  v <- c(nextElem(it), nextElem(it), nextElem(it))
  e <- err(nextElem(it))

  it <- iter(1:6, checkFunc = function(i) i %% 2 == 0)
  ev <- c(nextElem(it), nextElem(it), nextElem(it))

  it <- iter(c(10, 20), recycle = TRUE)
  rc <- c(nextElem(it), nextElem(it), nextElem(it))

  it <- iter(c(1.5, 2.5))
  db <- c(nextElem(it), nextElem(it))

  it <- iter(list(4, c(8, 9)))
  l1 <- nextElem(it)
  l2 <- nextElem(it)

  it <- iter(integer(0))
  empty <- err(nextElem(it))

  it <- iter(1:3, checkFunc = function(i) i < 0)
  none <- err(nextElem(it))

  m <- matrix(1:6, nrow = 2)
  it <- iter(m, by = "column", chunksize = 2)
  ch1 <- nextElem(it)
  ch2 <- nextElem(it)
  ch.end <- err(nextElem(it))

  it <- iter(m, by = "cell")
  cells <- sapply(1:6, function(k) nextElem(it))

  it <- iter(m, by = "row")
  row1 <- nextElem(it)

  it <- iter(m, "ce")
  cell1 <- nextElem(it)

  it <- iter(m, by = "column", recycle = TRUE)
  mr <- c(
    as.vector(nextElem(it)), as.vector(nextElem(it)),
    as.vector(nextElem(it)), as.vector(nextElem(it))
  )

  x <- matrix(1:10, ncol = 2)
  it <- iter(x, by = "column", checkFunc = function(i) i[5] %% 10 == 0)
  kept <- nextElem(it)

  w <- ""
  it <- withCallingHandlers(
    iter(m, by = "cell", chunksize = 2),
    warning = function(w0) {
      w <<- conditionMessage(w0)
      invokeRestart("muffleWarning")
    }
  )
  wcell <- nextElem(it)
  wtext <- gsub("\n", " / ", w, fixed = TRUE)

  bad <- err(iter(m, by = "c"))
  bad.df <- err(iter(data.frame(a = 1:2), by = "cell"))

  df <- data.frame(x = 1:3, y = c(10, 20, 30))
  it <- iter(df)
  cx <- nextElem(it)
  cy <- nextElem(it)
  it <- iter(df, by = "row")
  r1 <- nextElem(it)
  r2 <- nextElem(it)
  it <- iter(df, by = "row", recycle = TRUE)
  for (k in 1:3) nextElem(it)
  rwrap <- nextElem(it)

  it <- iter(data.frame(z = c("a", "b", "c")))
  letters <- paste(nextElem(it), collapse = ",")

  it <- iter(data.frame(x = 1:4), by = "row", checkFunc = function(i) i[[1]][1] %% 2 == 0)
  evrow <- c(as.numeric(unlist(nextElem(it))), as.numeric(unlist(nextElem(it))))

  it <- iter(data.frame(x = c(5, 6)), "row")
  pos <- as.numeric(unlist(nextElem(it)))

  it <- iter(function(i) i * 10)
  f <- c(nextElem(it), nextElem(it), nextElem(it))
  it <- iter(function() 7)
  f0 <- c(nextElem(it), nextElem(it))

  it <- iter(function(i) if (i > 2) stop("StopIteration") else i, recycle = TRUE)
  fr <- c(nextElem(it), nextElem(it), nextElem(it), nextElem(it))

  it <- iter(function(i) if (i > 2) stop("too high") else i)
  fh <- c(nextElem(it), nextElem(it))
  fherr <- err(nextElem(it))

  base <- iter(c(9, 8))
  same <- if (identical(base, iter(base))) "SAME" else "DIFF"
  same.v <- c(nextElem(base), nextElem(base))

  paste(c(
    num(v), e, num(ev), num(rc), num(db), num(l1), num(l2), empty, none,
    num(ch1), num(ch2), ch.end, num(cells), num(row1), num(cell1), num(mr), num(kept),
    wtext, num(wcell), bad, bad.df,
    num(cx), num(cy), num(r1), num(r2), num(rwrap), letters, num(evrow), num(pos),
    num(f), num(f0), num(fr), num(fh), fherr, same, num(same.v)
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
