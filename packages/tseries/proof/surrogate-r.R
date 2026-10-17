
suppressPackageStartupMessages(library(tseries))
options(warn = -1)
cell <- function(v) {
  if (is.logical(v)) return(if (isTRUE(v)) "TRUE" else "FALSE")
  if (is.numeric(v)) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    return(sprintf("%.17g", v))
  }
  as.character(v)
}
join <- function(x) paste(vapply(as.vector(x), cell, ""), collapse = ",")
series_text <- function(name) {
  data(list = name, package = "tseries", envir = environment())
  x <- get(name, inherits = FALSE)
  tp <- tsp(x)
  nm <- colnames(x)
  if (is.null(nm)) nm <- ""
  finite <- x[is.finite(x)]
  paste(length(x), cell(tp[1]), cell(tp[2]), cell(tp[3]), paste(nm, collapse = ","),
        cell(finite[1]), cell(finite[length(finite)]), sum(!is.finite(x)), sep = "|")
}

one <- function() {
z <- sin((1:8)/3)
set.seed(1); a <- surrogate(z, fft = FALSE)
set.seed(1); b <- surrogate(z, fft = TRUE)
set.seed(1); c <- surrogate(z, fft = TRUE, amplitude = TRUE)
set.seed(4); d <- surrogate(sin((1:10)/3), ns = 2, statistic = function(v) v[1])
paste(join(a), join(b), join(c), cell(d$orig.statistic), cell(d$bias), join(d$statistic), sep = "|")
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
cat(value, "\n", sprintf("%.17g", median(elapsed) * 1000), "\n", sep = "")
