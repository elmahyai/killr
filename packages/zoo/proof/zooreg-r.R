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
  q <- zooreg(1:4, start = c(1959, 2), frequency = 4)
  nocal <- zooreg(1:4, frequency = 4, start = 1, calendar = FALSE)
  mon <- zooreg(1:4, start = 2000, frequency = 12)
  both <- zooreg(1:4, frequency = 4, deltat = 1)
  near <- zooreg(1:3, frequency = 4 + 1e-7)
  daily <- zooreg(1:3, start = as.Date("2000-01-01"), frequency = 1)
  ints <- zooreg(c(1.2, 2.8), start = 5L, frequency = 1)
  empty <- zooreg()
  big <- zooreg(1:20000, frequency = 4, calendar = FALSE)
  msg <- tryCatch(zooreg(1:3, start = 5, end = 1), error = function(e) conditionMessage(e))
  bad <- if (identical(msg, "start cannot be after end")) 1 else 0
  c(
    as.numeric(index(q)), frequency(q),
    as.numeric(index(nocal)),
    as.numeric(index(mon)), frequency(mon),
    as.numeric(index(both)),
    as.numeric(index(near)), frequency(near),
    as.numeric(index(daily)),
    as.numeric(coredata(ints)), as.numeric(index(ints)),
    if (is.integer(index(ints))) 1 else 0,
    if (is.logical(coredata(empty)) && is.na(coredata(empty))) 1 else 0,
    as.numeric(index(empty)), frequency(empty),
    sum(as.numeric(index(big))),
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
