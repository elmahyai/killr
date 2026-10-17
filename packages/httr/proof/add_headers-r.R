.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(httr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("httr") == "1.4.9")

enc <- function(x) encodeString(x, quote = "\"")
show_headers <- function(h) {
  if (is.null(h)) return("NULL")
  if (length(h) == 0) return("character(0)")
  nms <- names(h)
  paste(vapply(seq_along(h), function(i) {
    nm <- if (is.na(nms[[i]])) "<NA>" else enc(nms[[i]])
    val <- if (is.na(h[[i]])) "<NA>" else enc(h[[i]])
    paste0(nm, "=", val)
  }, ""), collapse = "|")
}
line <- function(expr) {
  tryCatch({
    x <- eval(expr, parent.frame())
    paste0(
      "class=", paste(class(x), collapse = "/"),
      "|method=", if (is.null(x$method)) "NULL" else "SET",
      "|url=", if (is.null(x$url)) "NULL" else "SET",
      "|fields=", if (is.null(x$fields)) "NULL" else "SET",
      "|options=", if (is.null(x$options)) "NULL" else "SET",
      "|auth=", if (is.null(x$auth_token)) "NULL" else "SET",
      "|output=", if (is.null(x$output)) "NULL" else "SET",
      "|headers=", show_headers(x$headers)
    )
  }, error = function(e) paste("ERR", conditionMessage(e)))
}

one <- function() {
  p <- as.POSIXct("2000-01-01", tz = "UTC")
  d <- as.Date("2000-01-01")
  cases <- list(
  quote(add_headers(a = 1, b = 2)),
  quote(add_headers(.headers = c(a = "1", b = "2"))),
  quote(add_headers()),
  quote(add_headers(x = 1, x = 2)),
  quote(add_headers(b = 1, a = 2, b = 3)),
  quote(add_headers(x = 1, .headers = c(x = "9", y = "3"))),
  quote(add_headers(a = 1, .headers = c(b = "2"), c = 3)),
  quote(add_headers("hello")),
  quote(add_headers("hello", "world")),
  quote(add_headers(a = 1, 2, b = 3)),
  quote(add_headers(a = 1, 2, 4, b = 3)),
  quote(add_headers(c(a = "1", b = "2"))),
  quote(add_headers(foo = c(a = "1", b = "2"))),
  quote(add_headers(foo = c("1", "2"))),
  quote(add_headers(foo = "1")),
  quote(add_headers(a = NULL, b = "2")),
  quote(add_headers(a = character(), b = "2")),
  quote(add_headers(a = NULL)),
  quote(add_headers(.headers = NULL)),
  quote(add_headers(.headers = character())),
  quote(add_headers(.headers = numeric(0))),
  quote(add_headers(numeric(0))),
  quote(add_headers(.headers = c(a = 1))),
  quote(add_headers(a = 1L, b = 2.5)),
  quote(add_headers(a = TRUE, b = FALSE, c = NA)),
  quote(add_headers(a = NA_integer_, b = NA_real_, c = NA_character_, d = NaN, e = Inf, f = -Inf)),
  quote(add_headers(a = -0)),
  quote(add_headers(a = 1e-4, b = 1e5, c = 100000, d = 0.0001, e = 9999999, f = 1e6, g = 1.23e-10, h = 1e20, i = 1e-20)),
  quote(add_headers(a = 1.1, b = pi, c = 1/3, d = 2/3, e = 2^53, f = 2^53 + 1)),
  quote(add_headers(a = 1+2i)),
  quote(add_headers(a = 0+1i, b = 1-2i, c = -1-2i, d = NA_complex_, e = NaN+0i, f = Inf+1i, g = 1.5+2.5i, h = 1e-4+1e5i, i = -0+0i, j = 0i)),
  quote(add_headers(a = factor("b", levels = c("a", "b")))),
  quote(add_headers(a = c(TRUE, FALSE, NA))),
  quote(add_headers(a = 1:3)),
  quote(add_headers(a = 1:0)),
  quote(add_headers(.headers = structure(c("1", "2"), names = c("a", NA)))),
  quote(add_headers(.headers = structure(c("1", "2", "3"), names = c("a", NA, NA)))),
  quote(add_headers(.headers = structure(c("1", "2"), names = c(NA, "NA")))),
  quote(add_headers(a = "", b = "x")),
  quote(add_headers(.head = "x")),
  quote(add_headers(headers = "x")),
  quote(add_headers(.headers = c(.headers = "x"))),
  quote(add_headers(a = list(1))),
  quote(add_headers(.headers = list(a = "1"))),
  quote(add_headers(a = as.raw(65))),
  quote(add_headers(a = as.raw(c(0, 10, 65, 255)))),
  quote(add_headers(.headers = as.raw(65))),
  quote(add_headers(Accept = "")),
  quote(add_headers(A = "1", a = "2", A = "3")),
  quote(add_headers(a = 1, a = 2, a = 3, b = 4, a = 5)),
  quote(add_headers(.headers = matrix(c("a", "b"), nrow = 1))),
  quote(add_headers(a = "z", .headers = matrix(c("a", "b"), nrow = 1, dimnames = list("r", c("x", "y"))))),
  quote(add_headers(a = quote(foo))),
  quote(add_headers(.headers = c(a = "1", b = "2", a = "3"))),
  quote(add_headers(1, a = 2)),
  quote(add_headers(a = c(x = 1, y = 2))),
  quote(add_headers(A = c(x = 1))),
  quote(add_headers(.headers = structure(c("p", "q"), names = c("", "b")))),
  quote(add_headers(.headers = structure(character(0), names = character(0)))),
  quote(add_headers(a = 1e-4 / 1000^-2)),
  quote(add_headers(a = .Machine$double.eps, b = .Machine$double.xmin, c = .Machine$double.xmax)),
  quote(add_headers(a = 123456789012345, b = 1.23456789012345e-7, c = 0.000123456789012345, d = 9.99e-5)),
  quote(add_headers(n = c(1, NA, 3))),
  quote(add_headers(.headers = c(a = NA_character_, b = "ok"))),
  quote(add_headers(a = "na", .headers = c(a = "nb", c = "nc"), b = "xx")),
  quote(add_headers(A = structure(c("1", "2", "3"), names = c("", "b", NA)))),
  quote(add_headers(A = structure(c("1", "2"), names = c(NA, NA)))),
  quote(add_headers(foo = 1:10)),
  quote(add_headers(A = structure(c("1", "2"), names = c("x", "")))),
  quote(add_headers(.headers = structure(c("1", "2", "3"), names = c("", "", "")))),
  quote(add_headers(.headers = structure(c("1", "2", "3"), names = c("", "", " ")))),
  quote(add_headers(`a b` = "c", `ü` = "d", `a:b` = "e")),
  quote(add_headers(a = "x\ny")),
  quote(add_headers(.headers = structure(c(a = "1", b = "2"), class = "foo"))),
  quote(add_headers(.headers = c(a = TRUE))),
  quote(add_headers(a = 1, .headers = NULL)),
  quote(add_headers(a = "1", .headers = NULL)),
  quote(add_headers(a = "1", .headers = c(b = 2))),
  quote(add_headers(c(x = 1, x = 2, y = 3))),
  quote(add_headers(A = c(x = 1, x = 2))),
  quote(add_headers(a = "z", 1, 2)),
  quote(add_headers(1, 2, 3)),
  quote(add_headers(a = p)),
  quote(add_headers(a = p, b = "1")),
  quote(add_headers(a = "1", b = p)),
  quote(add_headers(a = NULL, b = p)),
  quote(add_headers(a = character(), b = p)),
  quote(add_headers(a = d)),
  quote(add_headers(a = d, b = "1")),
  quote(add_headers(a = "1", b = d)),
  quote(add_headers(a = p, b = "2000-01-01")),
  quote(add_headers(a = p, b = "2000-01-01 extra")),
  quote(add_headers(a = p, b = "nope")),
  quote(add_headers(.headers = factor(c("a", "b")))),
  quote(add_headers(a = factor(c("x", "y")))),
  quote(add_headers(raw(0))),
  quote(add_headers(a = list())),
  quote(add_headers(A = structure("1", names = ""))),
  quote(add_headers(A = structure("1", names = NA_character_))),
  quote(add_headers(.headers = c(a = "1", "2")))
)
  out <- character(length(cases))
  for (i in seq_along(cases)) out[[i]] <- line(cases[[i]])
  paste(out, collapse = "\n")
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
