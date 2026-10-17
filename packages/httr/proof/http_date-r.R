.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(httr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("httr") == "1.4.9")

show <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.character(x)) {
    vals <- ifelse(is.na(x), "NA", x)
    nm <- if (is.null(names(x))) "" else paste(names(x), collapse = ",")
    body <- if (length(x) == 0) "" else paste(vals, collapse = " | ")
    return(paste0("chr[", body, "] names=", nm))
  }
  paste0("OTHER ", paste(class(x), collapse = "/"))
}

grab <- function(expr) {
  tryCatch(show(eval(expr)), error = function(e) paste("ERR", conditionMessage(e)))
}

gmt <- function(seconds) as.POSIXct(seconds, origin = "1970-01-01", tz = "GMT")

one <- function() {
  named <- gmt(c(0, NA_real_))
  names(named) <- c("a", "b")
  lines <- c(
    show(http_date(gmt(784111777))),
    show(http_date(gmt(0))),
    show(http_date(gmt(-1))),
    show(http_date(gmt(-0.1))),
    show(http_date(gmt(-1.1))),
    show(http_date(gmt(784111777.9))),
    show(http_date(gmt(784111777.999999))),
    show(http_date(gmt(-86400.2))),
    show(http_date(gmt(784129777))),
    show(http_date(gmt(NA_real_))),
    show(http_date(gmt(NaN))),
    show(http_date(gmt(c(Inf, -Inf, NaN)))),
    show(http_date(gmt(c(NA_real_, NaN)))),
    show(http_date(gmt(numeric(0)))),
    show(http_date(NULL)),
    show(http_date(named)),
    grab(quote(http_date("Sun, 06 Nov 1994 08:49:37 GMT"))),
    grab(quote(http_date(1))),
    grab(quote(http_date(as.Date("1994-11-06"))))
  )
  paste(lines, collapse = "\n")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%s,"median_ms":%.17g}\n',
  jsonlite::toJSON(value, auto_unbox = TRUE),
  median(elapsed) * 1000
))
