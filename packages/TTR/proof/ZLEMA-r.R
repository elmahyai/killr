
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({library(TTR); library(xts)})
options(warn = -1)
data(ttrc)
close <- ttrc[1:400, "Close"]
high <- ttrc[1:400, "High"]
low <- ttrc[1:400, "Low"]
volume <- ttrc[1:400, "Volume"]
hl <- as.matrix(ttrc[1:400, c("High", "Low")])
hlc <- as.matrix(ttrc[1:400, c("High", "Low", "Close")])
ohlc <- as.matrix(ttrc[1:400, c("Open", "High", "Low", "Close")])
dates <- as.Date(ttrc$Date)[1:400]
ix <- as.Date("2020-01-01") + 0:4
json_val <- function(x) {
  if (is.character(x)) {
    esc <- gsub("\\\\", "\\\\\\\\", x, fixed = TRUE)
    esc <- gsub("\"", "\\\\\"", esc, fixed = TRUE)
    return(paste0("[\"", esc, "\"]"))
  }
  parts <- ifelse(is.na(as.numeric(x)), "null", sprintf("%.17g", as.numeric(x)))
  paste0("[", paste(parts, collapse = ","), "]")
}
one <- function() {
  as.numeric(ZLEMA(close, 20))
}
value <- one()

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
