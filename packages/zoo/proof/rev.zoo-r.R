.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
if (!isTRUE(packageVersion("zoo") == "1.9-1")) stop("zoo version is not 1.9-1")
flat <- function(x) {
  if (is.null(x) || length(x) == 0) return("")
  if (is.logical(x)) {
    return(paste(vapply(x, function(v) if (is.na(v)) "NA" else if (isTRUE(v)) "1" else "0", ""), collapse = "|"))
  }
  x <- as.numeric(x)
  paste(vapply(x, function(v) if (is.na(v)) "NA" else sprintf("%.16g", v), ""), collapse = "|")
}
emit <- function(obj) {
  if (is.zoo(obj)) list(value = flat(coredata(obj)), index = flat(index(obj)))
  else list(value = flat(obj), index = "")
}
one <- function() rev(zoo(c(1, NA, 3), c(1, 2, 3)))

result <- emit(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","index":"%s","median_ms":%.17g}\n', result$value, result$index, median(elapsed) * 1000))
