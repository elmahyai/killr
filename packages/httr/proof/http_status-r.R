.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(httr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("httr") == "1.4.9")
options(warnPartialMatchDollar = FALSE)

show <- function(x) {
  paste0(
    "category=", x$category,
    "|reason=", x$reason,
    "|message=", x$message
  )
}

grab <- function(expr) {
  tryCatch(show(eval(expr)), error = function(e) paste("ERR", conditionMessage(e)))
}

std <- function(code) {
  structure(
    list(
      url = "http://example.test/status/404",
      status_code = code,
      headers = list()
    ),
    class = "response"
  )
}

codes <- c(
  100, 101, 102,
  200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
  300, 301, 302, 303, 304, 305, 306, 307, 308,
  400, 401, 402, 403, 404, 405, 406, 407, 408, 409,
  410, 411, 412, 413, 414, 415, 416, 417, 418, 420,
  422, 423, 424, 425, 426, 428, 429, 431, 444, 449,
  450, 451, 499,
  500, 501, 502, 503, 504, 505, 506, 507, 508, 509,
  510, 511, 598, 599
)
installed <- as.numeric(unique(names(getFromNamespace("http_statuses", "httr"))))
stopifnot(identical(codes, installed))

one <- function() {
  lines <- character()
  for (code in codes) lines <- c(lines, show(http_status(code)))
  lines <- c(
    lines,
    show(http_status(200L)),
    show(http_status(424L)),
    show(http_status(c(a = 404))),
    show(http_status(structure(404, comment = "hi"))),
    show(http_status(structure(404, names = "code"))),
    show(http_status(matrix(404))),
    show(http_status(array(404, c(1, 1, 1)))),
    show(http_status(structure(404, class = "numeric"))),
    show(http_status(structure(404L, class = c("integer", "numeric")))),
    show(http_status(std(404L))),
    show(http_status(std(200))),
    show(http_status(structure(list(status_codes = 404L), class = "response"))),
    show(http_status(structure(
      list(status_code = 404L, status_code = 200L),
      class = "response"
    ))),
    show(http_status(199.99999999999997)),
    show(http_status(200.00000000000003)),
    grab(quote(http_status(320))),
    grab(quote(http_status(0))),
    grab(quote(http_status(99))),
    grab(quote(http_status(103))),
    grab(quote(http_status(404.5))),
    grab(quote(http_status(600))),
    grab(quote(http_status(-1))),
    grab(quote(http_status(NA_real_))),
    grab(quote(http_status(NA_integer_))),
    grab(quote(http_status(NaN))),
    grab(quote(http_status(Inf))),
    grab(quote(http_status(-Inf))),
    grab(quote(http_status(-0))),
    grab(quote(http_status(NULL))),
    grab(quote(http_status("404"))),
    grab(quote(http_status(TRUE))),
    grab(quote(http_status(FALSE))),
    grab(quote(http_status(c(404, 200)))),
    grab(quote(http_status(c(404L, 200L)))),
    grab(quote(http_status(numeric(0)))),
    grab(quote(http_status(integer(0)))),
    grab(quote(http_status(matrix(c(404, 200), nrow = 1)))),
    grab(quote(http_status(99.99999999999999))),
    grab(quote(http_status(std(NULL)))),
    grab(quote(http_status(std("404")))),
    grab(quote(http_status(std("320")))),
    grab(quote(http_status(std("")))),
    grab(quote(http_status(std(NA_real_)))),
    grab(quote(http_status(std(NA_integer_)))),
    grab(quote(http_status(std(NaN)))),
    grab(quote(http_status(std(c(404, 200))))),
    grab(quote(http_status(structure(
      list(status_code_a = 1L, status_code_b = 2L),
      class = "response"
    )))),
    grab(quote(http_status(structure(list(), class = "response")))),
    grab(quote(http_status(structure(list(status = 404L), class = "response")))),
    grab(quote(http_status(structure(list(Status_code = 404L), class = "response")))),
    grab(quote(http_status(structure(
      list(5L),
      class = "response",
      names = NA_character_
    )))),
    grab(quote(http_status(std(list(404))))),
    grab(quote(http_status(std(TRUE)))),
    grab(quote(http_status(std(200 + 0i)))),
    grab(quote(http_status(std(character(0))))),
    grab(quote(http_status(list(404)))),
    grab(quote(http_status(factor(404)))),
    grab(quote(http_status(NA)))
  )
  paste(lines, collapse = "\n")
}

example <- capture.output({
  print(http_status(100))
  print(http_status(404))
})
writeLines(
  example,
  "/home/ahmed/killr_projects/killr/packages/httr/docs/output/http_status-r.txt"
)

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
