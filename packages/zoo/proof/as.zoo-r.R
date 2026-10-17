.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")
json_num <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- character(length(x))
  for (i in seq_along(x)) {
    parts[[i]] <- if (is.na(x[[i]])) "null" else sprintf("%.17g", x[[i]])
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
one <- function() {
  x <- as.zoo(c(2, 4, 6))
  m <- as.zoo(matrix(1:6, ncol = 2))
  d <- as.zoo(data.frame(a = c(1, 2), b = c(1.5, 3)))
  f <- as.zoo(factor(c("b", "a", "b"), levels = c("a", "b", "c")))
  tser <- as.zoo(ts(1:10, start = c(1959, 2), frequency = 4))
  q <- as.zoo(1:4, frequency = 4)
  big <- as.zoo(1:100000)
  dropped <- as.zoo(zooreg(1:4, frequency = 4, calendar = FALSE))
  msg <- tryCatch(
    withCallingHandlers(
      as.zoo(matrix(1:3, ncol = 1), order.by = c(1L, 2L, 4L), frequency = 2.5),
      warning = function(w) invokeRestart("muffleWarning")
    ),
    error = function(e) conditionMessage(e)
  )
  bad <- if (identical(msg, "missing value where TRUE/FALSE needed")) 1 else 0
  c(
    as.numeric(coredata(x)), as.numeric(index(x)),
    as.numeric(coredata(m)), as.numeric(coredata(d)), as.numeric(coredata(f)),
    as.numeric(index(tser)), frequency(tser),
    as.numeric(index(q)), frequency(q),
    sum(as.numeric(coredata(big))),
    if (is.null(attr(dropped, "frequency"))) 0 else 1,
    if (inherits(dropped, "zooreg")) 1 else 0,
    bad
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
