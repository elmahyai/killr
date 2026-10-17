suppressPackageStartupMessages(library(shiny))

fmt_double <- function(v) {
  if (is.nan(v)) return("NaN")
  if (is.na(v)) return("NA")
  if (is.infinite(v)) return(if (v > 0) "Inf" else "-Inf")
  if (v == 0 && (1 / v) < 0) return("-0")
  if (is.finite(v) && v == floor(v) && abs(v) < 1e15) return(sprintf("%.0f", v))
  formatC(v, format = "g", digits = 15, width = 1)
}

tok <- function(x) {
  if (is.null(x)) return("NULL")
  suffix <- ""
  cls <- attr(x, "class")
  if (!is.null(cls)) suffix <- paste0("{", paste(cls, collapse = ","), "}")
  nms <- names(x)
  if (!is.null(nms)) suffix <- paste0(suffix, "{names:", paste(nms, collapse = "|"), "}")
  kind <- typeof(x)
  data <- x
  attributes(data) <- NULL
  n <- length(data)
  prefix <- paste0("n=", n, " ")
  if (kind == "raw") {
    body <- if (n == 0) "" else paste(sprintf("%02x", as.integer(data)), collapse = "|")
    return(paste0(prefix, "RAW:", body, suffix))
  }
  if (kind == "complex") {
    parts <- vapply(data, function(v) if (is.na(v)) "<NA>" else gsub(" ", "", as.character(v)), character(1))
    return(paste0(prefix, "CPLX:", paste(parts, collapse = "|"), suffix))
  }
  if (kind == "character") {
    parts <- vapply(data, function(s) if (is.na(s)) "<NA>" else s, character(1))
    return(paste0(prefix, "C:", paste(parts, collapse = "|"), suffix))
  }
  if (kind == "logical") {
    parts <- vapply(data, function(s) {
      if (is.na(s)) "NA" else if (isTRUE(s)) "TRUE" else "FALSE"
    }, character(1))
    return(paste0(prefix, "L:", paste(parts, collapse = "|"), suffix))
  }
  if (kind == "integer") {
    parts <- vapply(data, function(s) if (is.na(s)) "NA" else as.character(s), character(1))
    return(paste0(prefix, "I:", paste(parts, collapse = "|"), suffix))
  }
  if (kind == "double") {
    parts <- vapply(data, fmt_double, character(1))
    return(paste0(prefix, "D:", paste(parts, collapse = "|"), suffix))
  }
  "OTHER"
}

grab <- function(expr) {
  tryCatch(
    {
      vis <- withVisible(eval(expr, envir = parent.frame()))
      paste0("OK vis=", if (isTRUE(vis$visible)) "1" else "0", " ", tok(vis$value))
    },
    error = function(e) {
      paste0("ERR ", paste(class(e), collapse = "/"), "|", conditionMessage(e))
    }
  )
}

one <- function() {
  btn <- function(n) structure(n, class = "shinyActionButtonValue")
  parts <- c(
    grab(quote(need())),
    grab(quote(need(1 + 1))),
    grab(quote(need(NULL))),
    grab(quote(need(NULL, label = "input$x"))),
    grab(quote(need(1, label = "input$x"))),
    grab(quote(need(NULL, message = "custom message"))),
    grab(quote(need(1, message = "custom message"))),
    grab(quote(need(NULL, message = "explicit", label = "ignored"))),
    grab(quote(need(NULL, FALSE))),
    grab(quote(need(TRUE, FALSE))),
    grab(quote(need(FALSE, FALSE))),
    grab(quote(need("", FALSE))),
    grab(quote(need(character(0), FALSE))),
    grab(quote(need(logical(0), FALSE))),
    grab(quote(need(numeric(0), FALSE))),
    grab(quote(need(integer(0), FALSE))),
    grab(quote(need(complex(0), FALSE))),
    grab(quote(need(raw(0), FALSE))),
    grab(quote(need(matrix(), FALSE))),
    grab(quote(need(matrix(FALSE, 1, 1), FALSE))),
    grab(quote(need(NA, FALSE))),
    grab(quote(need(NA_integer_, FALSE))),
    grab(quote(need(NA_real_, FALSE))),
    grab(quote(need(NA_complex_, FALSE))),
    grab(quote(need(NA_character_, FALSE))),
    grab(quote(need(c(NA, NA, FALSE), FALSE))),
    grab(quote(need(c(FALSE), FALSE))),
    grab(quote(need(try(stop("boom"), silent = TRUE), FALSE))),
    grab(quote(need(0, FALSE))),
    grab(quote(need(0L, FALSE))),
    grab(quote(need(-0, FALSE))),
    grab(quote(need(1:10, FALSE))),
    grab(quote(need(LETTERS, FALSE))),
    grab(quote(need("NA", FALSE))),
    grab(quote(need(" ", FALSE))),
    grab(quote(need(c(NA, NA, TRUE), FALSE))),
    grab(quote(need(c(FALSE, FALSE, TRUE), FALSE))),
    grab(quote(need(NULL, label = c("a", "b")))),
    grab(quote(need(NULL, label = 1))),
    grab(quote(need(NULL, label = 1L))),
    grab(quote(need(NULL, label = TRUE))),
    grab(quote(need(NULL, label = FALSE))),
    grab(quote(need(NULL, label = NA))),
    grab(quote(need(NULL, label = NA_character_))),
    grab(quote(need(NULL, label = NULL))),
    grab(quote(need(NULL, label = character(0)))),
    grab(quote(need(NULL, label = numeric(0)))),
    grab(quote(need(NULL, label = c(NA, "x")))),
    grab(quote(need(NULL, label = 1.5))),
    grab(quote(need(NULL, label = Inf))),
    grab(quote(need(NULL, label = NaN))),
    grab(quote(need(NULL, label = -0))),
    grab(quote(need(NULL, label = 0+1i))),
    grab(quote(need(NULL, label = as.raw(65)))),
    grab(quote(need(NULL, "hello", "ignored"))),
    grab(quote(need(NULL, c("a", "b")))),
    grab(quote(need(NULL, character(0)))),
    grab(quote(need(NULL, ""))),
    grab(quote(need(NULL, "  "))),
    grab(quote(need(NULL, NA))),
    grab(quote(need(NULL, NA_character_))),
    grab(quote(need(NULL, NA_integer_))),
    grab(quote(need(NULL, NA_real_))),
    grab(quote(need(NULL, NaN))),
    grab(quote(need(NULL, message = NULL))),
    grab(quote(need(1, message = NULL))),
    grab(quote(need(NULL, c(a = "x", b = "y")))),
    grab(quote(need(NULL, label = c(aa = "field", bb = "other")))),
    grab(quote(need(NULL, label = factor(c("field", NA, "field"))))),
    grab(quote(need(NULL, c(FALSE, TRUE)))),
    grab(quote(need(NULL, 3.5))),
    grab(quote(need(NULL, 3L))),
    grab(quote(need(NULL, 0))),
    grab(quote(need(NULL, 0L))),
    grab(quote(need(NULL, -0))),
    grab(quote(need(NULL, 0+1i))),
    grab(quote(need(NULL, as.raw(65)))),
    grab(quote(need(NULL, raw(0)))),
    grab(quote(need(" ", "space"))),
    grab(quote(need(NaN, "nan"))),
    grab(quote(need(Inf, "inf"))),
    grab(quote(need(-Inf, "ninf"))),
    grab(quote(need(list(), "list"))),
    grab(quote(need(list(FALSE), "listfalse"))),
    grab(quote(need(data.frame(), "df"))),
    grab(quote(need(c("", ""), "blank"))),
    grab(quote(need(c(NA_character_, "a"), "mixc"))),
    grab(quote(need(c("  ", NA_character_), "ws"))),
    grab(quote(need(as.raw(0), "raw"))),
    grab(quote(need(raw(0), "rawe"))),
    grab(quote(need(0+0i, "c0"))),
    grab(quote(need(factor("a"), "fac"))),
    grab(quote(need(factor(NA), "facna"))),
    grab(quote(need(factor(character(0)), "fac0"))),
    grab(quote(need(btn(0L), "btn"))),
    grab(quote(need(btn(1L), "btn"))),
    grab(quote(need(btn(0), "btn"))),
    grab(quote(need(btn("0"), "btn"))),
    grab(quote(need(btn("a"), "btn"))),
    grab(quote(need(btn("0.0"), "btn"))),
    grab(quote(need(btn(NA_integer_), "btn"))),
    grab(quote(need(btn(c(0L, 1L)), "btn"))),
    grab(quote(need(NULL, label = c(1e-4, 100000, 10000, 0.00012, 99999, -1.25, -100000, Inf, -Inf, NaN, NA_real_)))),
    grab(quote(need(NULL, label = c(0+1i, 1-2i, 1e-4+1e5i, NA_complex_, NaN+1i, -0-0i, 2-0i, 0-1i)))),
    grab(quote(need(NULL, label = as.raw(c(0, 10, 65, 255))))),
    grab(quote(need(NULL, label = list("a", NA, 1L, FALSE, NULL, character(0), numeric(0), integer(0), logical(0), complex(0), raw(0))))),
    grab(quote(need(NULL, label = c(TRUE, FALSE, NA)))),
    grab(quote(need(NULL, label = ""))),
    grab(quote(need(NULL, label = " "))),
    grab(quote(need(NULL, label = 2147483647L))),
    grab(quote(need(NULL, structure("z", class = "foo")))),
    grab(quote(need(NULL, label = structure("z", class = "foo")))),
    grab(quote(need(1, expr = NULL))),
    grab(quote(need(NULL, lab = "field"))),
    grab(quote(need(NULL, mes = "hello"))),
    grab(quote(need(NULL, m = "hello"))),
    grab(quote(need(NULL, l = "field"))),
    grab(quote(need(e = NULL, message = "z"))),
    grab(quote(need(NULL, me = "A", la = "B"))),
    grab(quote(need(NULL, message = "a", m = "b"))),
    grab(quote(need(NULL, "a", "b", "c"))),
    grab(quote(need(NULL, "a", "b", "c", "d"))),
    grab(quote(need(NULL, "a", "b", 4))),
    grab(quote(need(foo = "bar"))),
    grab(quote(need(message = "x"))),
    grab(quote(need(label = "L"))),
    grab(quote(need(NULL, c("a", NA_character_))))
  )

  hits <- 0
  res <- grab(quote(need({hits <- hits + 1; TRUE}, message = {hits <- hits + 10; "m"})))
  parts <- c(parts, paste0(res, " hit=", hits))
  hits <- 0
  res <- grab(quote(need({hits <- hits + 1; FALSE}, message = stop("nope"))))
  parts <- c(parts, paste0(res, " hit=", hits))
  hits <- 0
  res <- grab(quote(need({hits <- hits + 1; NULL}, label = {hits <- hits + 10; "L"})))
  parts <- c(parts, paste0(res, " hit=", hits))
  hits <- 0
  res <- grab(quote(need({hits <- hits + 1; 1})))
  parts <- c(parts, paste0(res, " hit=", hits))
  hits <- 0
  res <- grab(quote(need(TRUE, message = "explicit", label = {hits <- hits + 1; stop("no")})))
  parts <- c(parts, paste0(res, " hit=", hits))
  hits <- 0
  res <- grab(quote(need(TRUE, label = {hits <- hits + 1; "L"})))
  parts <- c(parts, paste0(res, " hit=", hits))
  hits <- 0
  res <- grab(quote(need(FALSE, message = {hits <- hits + 1; "m"})))
  parts <- c(parts, paste0(res, " hit=", hits))
  hits <- 0
  res <- grab(quote(need({hits <- hits + 1; TRUE}, label = stop("lab"))))
  parts <- c(parts, paste0(res, " hit=", hits))
  paste(parts, collapse = "\n")
}

value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
shown <- gsub("\n", " / ", value, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
