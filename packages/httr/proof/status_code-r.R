.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(httr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("httr") == "1.4.9")
options(warnPartialMatchDollar = FALSE)

fmt_one <- function(z, kind) {
  if (kind == "double") {
    if (is.nan(z)) return("NaN")
    if (is.na(z)) return("NA")
    if (is.infinite(z)) return(if (z > 0) "Inf" else "-Inf")
    if (z == 0 && sign(1 / z) < 0) return("-0")
    return(sprintf("%.17g", z))
  }
  if (kind == "integer") {
    if (is.na(z)) return("NA")
    return(sprintf("%d", z))
  }
  if (kind == "character") {
    if (is.na(z)) return("NA")
    return(z)
  }
  if (kind == "logical") {
    if (is.na(z)) return("NA")
    return(if (z) "TRUE" else "FALSE")
  }
  sprintf("%.17g", as.numeric(z))
}

show <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.list(x)) {
    nms <- names(x)
    parts <- character(length(x))
    for (i in seq_along(x)) {
      body <- show(x[[i]])
      if (is.null(nms)) {
        parts[[i]] <- body
      } else if (is.na(nms[[i]])) {
        parts[[i]] <- paste0("NA_NAME=", body)
      } else if (!nzchar(nms[[i]])) {
        parts[[i]] <- body
      } else {
        parts[[i]] <- paste0(nms[[i]], "=", body)
      }
    }
    extra <- ""
    if ("class" %in% names(attributes(x))) {
      extra <- paste0(" class=", paste(class(x), collapse = "/"))
    }
    return(paste0("list[", paste(parts, collapse = ","), "]", extra))
  }
  kind <- typeof(x)
  vals <- character(length(x))
  if (length(x)) {
    for (i in seq_along(x)) vals[[i]] <- fmt_one(x[[i]], kind)
  }
  extra <- ""
  if (!is.null(names(x))) extra <- paste0(extra, " names=", paste(names(x), collapse = "|"))
  if (!is.null(dim(x))) extra <- paste0(extra, " dim=", paste(dim(x), collapse = ","))
  if (!is.null(dimnames(x))) {
    bits <- vapply(dimnames(x), function(one) {
      if (is.null(one)) "" else paste(one, collapse = "|")
    }, "")
    extra <- paste0(extra, " dimnames=", paste(bits, collapse = ";"))
  }
  if (!is.null(comment(x))) extra <- paste0(extra, " comment=", comment(x))
  if ("class" %in% names(attributes(x))) {
    extra <- paste0(extra, " class=", paste(class(x), collapse = "/"))
  }
  paste0(kind, "[", paste(vals, collapse = ","), "]", extra)
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

one <- function() {
  named <- c(a = 200, b = 404)
  kept <- structure(404L, comment = "kept")
  mat <- matrix(c(200, 404), nrow = 1)
  dimnames(mat) <- list("row", c("a", "b"))
  imat <- matrix(c(200L, 404L), nrow = 1)
  arr <- array(c(1, 2, 3, 4), c(1, 2, 2))
  dim1 <- structure(1:3, dim = 3L)
  commented <- structure(200L, comment = "hi")
  classed_num <- structure(7, class = "numeric")
  classed_int <- structure(1L, class = c("integer", "numeric"))
  num_first <- structure(list(status_code = 9), class = c("numeric", "response"))
  resp_first <- structure(list(status_code = 3L), class = c("response", "numeric"))
  foo_resp <- structure(list(status_code = 201L), class = c("foo", "response"))
  na_name <- structure(list(5L), class = "response", names = NA_character_)
  na_partial <- structure(
    list(1L, 6L),
    names = c(NA, "status_code_x"),
    class = "response"
  )
  lines <- c(
    show(status_code(std(404L))),
    show(status_code(std(404))),
    show(status_code(std(200.5))),
    show(status_code(std(NA_integer_))),
    show(status_code(std(NA_real_))),
    show(status_code(std(NaN))),
    show(status_code(std(-0))),
    show(status_code(std(kept))),
    show(status_code(std(named))),
    show(status_code(std(list(1, 2)))),
    show(status_code(std("404"))),
    show(status_code(std(NULL))),
    show(status_code(structure(list(url = "http://example.test/status/404", headers = list()), class = "response"))),
    show(status_code(structure(list(), class = "response"))),
    show(status_code(structure(list(status_code_extra = 222L), class = "response"))),
    show(status_code(structure(list(status_code_a = 1L, status_code_b = 2L), class = "response"))),
    show(status_code(structure(list(status_code = 10L, status_code_extra = 11L), class = "response"))),
    show(status_code(structure(list(status_code_extra = 1L, status_code = 2L), class = "response"))),
    show(status_code(structure(list(status_code = 1L, status_code = 2L), class = "response"))),
    show(status_code(structure(list(status = 33L), class = "response"))),
    show(status_code(structure(list(Status_code = 3L), class = "response"))),
    show(status_code(structure(list(status_codes = 5L), class = "response"))),
    show(status_code(na_name)),
    show(status_code(na_partial)),
    show(status_code(200)),
    show(status_code(200L)),
    show(status_code(c(200, 404, NA))),
    show(status_code(c(a = 200, b = 404.5))),
    show(status_code(numeric(0))),
    show(status_code(integer(0))),
    show(status_code(NA_real_)),
    show(status_code(NaN)),
    show(status_code(c(Inf, -Inf))),
    show(status_code(-0)),
    show(status_code(commented)),
    show(status_code(mat)),
    show(status_code(imat)),
    show(status_code(arr)),
    show(status_code(dim1)),
    show(status_code(classed_num)),
    show(status_code(classed_int)),
    show(status_code(num_first)),
    show(status_code(resp_first)),
    show(status_code(foo_resp)),
    grab(quote(status_code(NA))),
    grab(quote(status_code(NULL))),
    grab(quote(status_code("404"))),
    grab(quote(status_code(TRUE))),
    grab(quote(status_code(list(status_code = 200)))),
    grab(quote(status_code(factor("404")))),
    grab(quote(status_code(as.raw(200)))),
    grab(quote(status_code(200 + 0i))),
    grab(quote(status_code(ts(200)))),
    grab(quote(status_code(structure(200, class = "integer")))),
    grab(quote(status_code(structure(1, class = "double")))),
    grab(quote(status_code(structure(matrix(1), class = "matrix")))),
    grab(quote(status_code(structure(1, class = c("foo", "bar"))))),
    grab(quote(status_code(matrix("a")))),
    grab(quote(status_code(structure(404L, class = "response"))))
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
