
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
oh <- ts(cbind(Open = c(1, 2, 3, 4, 5), High = c(2, 3, 4, 5, 6), Low = c(0, 1, 2, 3, 4), Close = c(1, 2, 1, 3, 2)), start = 2000, frequency = 1)
time.x <- time(oh)
dt <- min(lag(time.x) - time.x) / 3
n <- NROW(oh)
lab.ind <- round(seq(1, n, length.out = 5))
D <- as.vector(time.x[lab.ind] * 86400) + as.POSIXct("1899-12-30", tz = "GMT")
labs <- format(D, "%Y-%m-%d", tz = "GMT")
rows <- vapply(seq_len(n), function(i) paste(cell(time.x[i]), cell(oh[i, "High"]), cell(oh[i, "Low"]), cell(time.x[i] - dt), cell(oh[i, "Open"]), cell(oh[i, "Close"]), cell(time.x[i] + dt), sep = ","), "")
paste0(paste(rows, collapse = "|"), "#", paste(labs, collapse = ","))
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
