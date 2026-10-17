.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(data.table))

flat <- function(x) {
  if (is.null(x)) return("null")
  if (is.list(x) && !is.data.frame(x)) {
    if (!length(x)) return("")
    return(paste(vapply(x, flat, ""), collapse = "/"))
  }
  if (length(x) == 0) return("")
  if (is.character(x)) return(paste(ifelse(is.na(x), "NA", x), collapse = "|"))
  if (is.logical(x)) return(paste(ifelse(is.na(x), "NA", ifelse(x, "TRUE", "FALSE")), collapse = "|"))
  paste(vapply(x, function(v) {
    if (identical(v, NaN)) "NaN" else if (is.na(v)) "NA" else sprintf("%.16g", v)
  }, ""), collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\\\", "\\\\\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\\\n", s, fixed = TRUE)
  s <- gsub("\t", "\\\\t", s, fixed = TRUE)
  s <- gsub("\r", "\\\\r", s, fixed = TRUE)
  s
}

one <- function() {
  shift(1:5, n=c(1, -1), fill=0)
}
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
