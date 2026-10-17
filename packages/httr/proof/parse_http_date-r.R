.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(httr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("httr") == "1.4.9")

show <- function(x) {
  if (is.null(x)) return("NULL")
  if (inherits(x, "POSIXct")) {
    vals <- vapply(as.numeric(x), function(z) if (is.na(z)) "NA" else sprintf("%.17g", z), "")
    nm <- if (is.null(names(x))) "" else paste(names(x), collapse = ",")
    tz <- paste(attr(x, "tzone"), collapse = ",")
    return(paste0("POSIXct[", paste(vals, collapse = ","), "] tz=", tz, " names=", nm))
  }
  if (inherits(x, "Date")) {
    vals <- vapply(as.numeric(x), function(z) if (is.na(z)) "NA" else sprintf("%.17g", z), "")
    return(paste0("Date[", paste(vals, collapse = ","), "]"))
  }
  if (is.character(x)) {
    vals <- ifelse(is.na(x), "NA", x)
    nm <- if (is.null(names(x))) "" else paste(names(x), collapse = ",")
    body <- if (length(x) == 0) "" else paste(vals, collapse = " | ")
    return(paste0("chr[", body, "] names=", nm))
  }
  paste0("OTHER ", paste(class(x), collapse = "/"))
}

one <- function() {
  failure2 <- structure(c(NA_real_, 3), class = "Date")
  named <- c(a = "Sun, 06 Nov 1994 08:49:37 GMT", b = "Mon, 07 Nov 1994 00:00:00 GMT")
  lines <- c(
    show(parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT")),
    show(parse_http_date("Sunday, 06-Nov-94 08:49:37 GMT")),
    show(parse_http_date("Sun Nov  6 08:49:37 1994")),
    show(parse_http_date(c("Sun, 06 Nov 1994 08:49:37 GMT", "Mon, 07 Nov 1994 00:00:00 GMT"))),
    show(parse_http_date(c("Sun, 06 Nov 1994 08:49:37 GMT", "Sunday, 06-Nov-94 08:49:37 GMT"))),
    show(parse_http_date("not a date")),
    show(parse_http_date(c("Sun, 06 Nov 1994 08:49:37 GMT", NA))),
    show(parse_http_date("")),
    show(parse_http_date(character(0))),
    show(parse_http_date(NULL)),
    show(parse_http_date("nope", failure = "bad")),
    show(parse_http_date(c("nope", "x"), failure = failure2)),
    show(parse_http_date("Monday, 06 Nov 1994 08:49:37 GMT")),
    show(parse_http_date("sun, 06 nov 1994 08:49:37 gmt")),
    show(parse_http_date("SUN, 06 NOVEMBER 1994 08:49:37 GMT")),
    show(parse_http_date("Sun, 6 Nov 1994 8:9:7 GMT")),
    show(parse_http_date("Sun,  06 Nov 1994 08:49:37 GMT")),
    show(parse_http_date("Sun,06Nov1994 08:49:37 GMT")),
    show(parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT extra")),
    show(parse_http_date(" Sun, 06 Nov 1994 08:49:37 GMT")),
    show(parse_http_date("Monday, 01-Jan-68 00:00:00 GMT")),
    show(parse_http_date("Thursday, 01-Jan-69 00:00:00 GMT")),
    show(parse_http_date("Saturday, 01-Jan-00 00:00:00 GMT")),
    show(parse_http_date("Sunday, 06-Nov-4 08:49:37 GMT")),
    show(parse_http_date("Sun, 06 Nov 1994 24:00:00 GMT")),
    show(parse_http_date("Sun, 06 Nov 1994 24:01:00 GMT")),
    show(parse_http_date("Sun, 06 Nov 1994 08:59:60 GMT")),
    show(parse_http_date("Sun, 06 Nov 1994 23:59:60 GMT")),
    show(parse_http_date("Sun, 06 Nov 1994 08:49:61 GMT")),
    show(parse_http_date("Tue, 29 Feb 2000 00:00:00 GMT")),
    show(parse_http_date("Thu, 29 Feb 1900 00:00:00 GMT")),
    show(parse_http_date("Sun, 31 Apr 1994 00:00:00 GMT")),
    show(parse_http_date("Mon, 31 Jan 1994 24:00:00 GMT")),
    show(parse_http_date("Sat, 31 Dec 1994 24:00:00 GMT")),
    show(parse_http_date("Sun Nov  6 08:49:37 19945")),
    show(parse_http_date("Sun, 06 Nov 999 08:49:37 GMT")),
    show(parse_http_date("Sun, 06 Nov 0 00:00:00 GMT")),
    show(parse_http_date("Wed, 31 Dec 1969 23:59:59 GMT")),
    show(parse_http_date(1)),
    show(parse_http_date(named)),
    show(parse_http_date("nope", failure = NULL))
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
