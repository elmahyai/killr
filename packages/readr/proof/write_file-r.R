
suppressPackageStartupMessages(library(readr))
options(readr.show_col_types = FALSE)
cell <- function(v) {
  if (length(v) == 0) return("")
  if (length(v) != 1) return(paste(vapply(v, cell, ""), collapse = "&"))
  if (inherits(v, "POSIXct")) return(format(v, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"))
  if (inherits(v, "Date")) return(format(v))
  if (inherits(v, "hms")) return(sprintf("%.17g", as.numeric(v)))
  if (is.factor(v)) return(as.character(v))
  if (is.logical(v)) return(if (is.na(v)) "NA" else if (isTRUE(v)) "TRUE" else "FALSE")
  if (is.numeric(v)) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    if (is.infinite(v)) return(if (v > 0) "Inf" else "-Inf")
    return(sprintf("%.17g", v))
  }
  if (is.na(v)) return("NA")
  as.character(v)
}
flatv <- function(x) {
  if (length(x) == 0) return("")
  paste(vapply(seq_along(x), function(i) cell(x[[i]]), ""), collapse = ",")
}
flatdf <- function(x) {
  bits <- paste(names(x), collapse = "|")
  for (col in x) bits <- paste0(bits, ";", flatv(col))
  bits
}
yn <- function(x) if (isTRUE(x)) "TRUE" else "FALSE"

one <- function() {
path <- tempfile()
write_file("hello\n", path)
readChar(path, file.info(path)$size)
}

value <- one()
if (is.null(value)) value <- "NULL"
if (!is.character(value)) value <- as.character(value)
if (length(value) != 1) value <- paste(value, collapse = ",")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":\"%s\",\"median_ms\":%.17g}\n", gsub("\"", "\\\"", value), median(elapsed) * 1000))
