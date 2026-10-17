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
  x <- as.zooreg.default(1:5)
  y <- as.zooreg.default(1:4, frequency = 4)
  warns <- character()
  irreg <- withCallingHandlers(
    as.zooreg.default(zoo(c(1, 2, 4), c(1, 2, 3.3))),
    warning = function(w) {
      warns <<- c(warns, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  )
  big <- as.zooreg.default(1:20000)
  flagged <- if (length(warns) && grepl("underlying regularity", warns[[1]], fixed = TRUE)) 1 else 0
  c(
    as.numeric(coredata(x)), as.numeric(index(x)), frequency(x),
    as.numeric(index(y)), frequency(y),
    as.numeric(coredata(irreg)), as.numeric(index(irreg)), frequency(irreg),
    flagged,
    sum(as.numeric(index(big)))
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
