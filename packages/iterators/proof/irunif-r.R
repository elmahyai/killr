suppressPackageStartupMessages(library(iterators))
stopifnot(packageVersion("iterators") == "1.0.14")

fmt_num <- function(x) {
  if (length(x) == 0) return("EMPTY")
  paste(vapply(seq_along(x), function(i) {
    v <- x[[i]]
    if (is.nan(v)) "NaN"
    else if (is.na(v)) "NA"
    else if (is.infinite(v)) {
      if (v > 0) "Inf" else "-Inf"
    } else sprintf("%.17g", v)
  }, ""), collapse = ",")
}

step <- function(it) {
  w <- character()
  v <- withCallingHandlers(
    tryCatch(nextElem(it), error = function(e) structure(conditionMessage(e), class = "err")),
    warning = function(w0) {
      w <<- c(w, conditionMessage(w0))
      invokeRestart("muffleWarning")
    }
  )
  if (inherits(v, "err")) {
    text <- paste0("ERR:", gsub("\n", "<NL>", v, fixed = TRUE))
  } else {
    text <- paste0("NUM:", fmt_num(v))
  }
  if (length(w)) text <- paste0("W:", paste(w, collapse = ","), ";", text)
  text
}

build <- function(expr) {
  tryCatch({
    force(expr)
    "OK"
  }, error = function(e) paste0("ERR:", gsub("\n", "<NL>", conditionMessage(e), fixed = TRUE)))
}

one <- function() {
  parts <- character()
  add <- function(...) {
    parts <<- c(parts, as.character(unlist(list(...), recursive = TRUE, use.names = FALSE)))
  }

  set.seed(1)
  it <- irunif(5)
  add(step(it), step(it))

  set.seed(1)
  it <- irunif(1, count = 3)
  add(step(it), step(it), step(it), step(it))

  set.seed(1)
  it <- irunif(1, min = 2, max = 5, count = 2)
  add(step(it), step(it), step(it))

  set.seed(1)
  add(step(irunif(2, min = c(0, 10), max = c(1, 11))))

  set.seed(1)
  add(step(irunif(3, min = c(0, 5, 0), max = 1)))

  set.seed(1)
  add(step(irunif(3, min = c(0, 4, 0), max = c(1, 4, 1))))

  set.seed(1)
  add(step(irunif(2, min = 3, max = 3)), step(irunif(1)))

  set.seed(1)
  add(step(irunif(2, min = 5, max = 1)), step(irunif(1)))

  set.seed(1)
  add(step(irunif(2, min = numeric(0))), step(irunif(1)))

  add(step(irunif(0, min = 5, max = 1)))
  add(step(irunif(0, min = numeric(0))))
  add(step(irunif(numeric(0))))
  add(step(irunif(0.9)))
  add(step(irunif(-0)))
  add(step(irunif(FALSE)))
  add(step(irunif(0, min = "a")))

  add(step(irunif(-1)))
  add(step(irunif(-0.1)))
  add(step(irunif(NA_real_)))
  add(step(irunif(NaN)))
  add(step(irunif(Inf)))
  add(step(irunif(-Inf)))
  add(step(irunif(NULL)))
  add(step(irunif("a")))
  add(step(irunif("a", min = NULL)))
  add(step(irunif("")))
  add(step(irunif("-1")))
  add(step(irunif("1e20")))
  add(step(irunif(2^52 + 1)))

  set.seed(1)
  add(step(irunif("3")))
  set.seed(1)
  add(step(irunif(" 2")))
  set.seed(1)
  add(step(irunif("1.9")))
  set.seed(1)
  add(step(irunif(2.2)))
  set.seed(1)
  add(step(irunif(1.9)))
  set.seed(1)
  add(step(irunif(c(1, 2, 3))))
  set.seed(1)
  add(step(irunif(TRUE)))
  set.seed(1)
  add(step(irunif(c(TRUE, FALSE, TRUE))))
  set.seed(1)
  add(step(irunif(c("a", "b"))))
  set.seed(1)
  add(step(irunif(2.9 + 1i)))
  add(step(irunif(-1 + 2i)))
  add(step(irunif(1 + NaN * 1i)))
  add(step(irunif(NaN + 0i)))
  add(step(irunif(as.raw(1))))
  set.seed(1)
  add(step(irunif(as.raw(c(1, 2, 3)))))
  add(step(irunif(raw(0))))

  set.seed(1)
  add(step(irunif(4, min = c(0, 10), max = c(1, 20, 30))))
  set.seed(1)
  add(step(irunif(2, min = c(0, 1, 2), max = 10)))
  set.seed(1)
  add(step(irunif(2, min = TRUE, max = FALSE)))
  add(step(irunif(1, min = NULL)))
  add(step(irunif(1, min = "0")))
  add(step(irunif(1, min = 1 + 0i)))
  set.seed(1)
  add(step(irunif(1, min = NA_real_)))
  set.seed(1)
  add(step(irunif(1, max = Inf)))
  set.seed(1)
  add(step(irunif(1, min = -0, max = -0)))
  set.seed(1)
  add(step(irunif(1, mi = 2, ma = 5)))
  set.seed(1)
  add(step(irunif(n = 5)))

  add(step(irunif(1, m = 0)))
  add(step(irunif(m = 0)))
  add(step(irunif(1, max = 2, ma = 3)))
  add(step(irunif(1, foo = 1, bar = 2)))
  add(step(irunif(1, 0, 1, 5, 6)))
  add(step(irunif()))
  add(step(irunif(min = 0)))
  add(step(irunif(1, minimum = 0)))

  add(build(irunif(1, count = "a")))
  add(build(irunif(1, count = c(1, 2))))
  add(build(irunif(1, count = TRUE)))
  add(build(irunif(1, count = FALSE)))
  add(build(irunif(1, count = NULL)))
  add(build(irunif(1, count = numeric(0))))
  add(build(irunif(1, count = "")))

  set.seed(1)
  it <- irunif(1, count = NA_real_)
  add(step(it))
  set.seed(1)
  it <- irunif(1, count = NaN)
  add(step(it))
  it <- irunif(1, count = 0)
  add(step(it))
  it <- irunif(1, count = -1)
  add(step(it))
  it <- irunif(1, count = -Inf)
  add(step(it))

  set.seed(1)
  it <- irunif(1, count = 1.5)
  add(step(it), step(it), step(it))

  set.seed(1)
  it <- irunif(1, count = Inf)
  add(step(it), step(it), step(it))

  set.seed(1)
  it <- irunif(1)
  add(step(it), step(it))

  set.seed(1)
  it <- irunif(count = 2)
  add(step(it), step(it), step(it))

  set.seed(1)
  it <- irunif(n = "a", count = 1)
  add(step(it), step(it))

  set.seed(1)
  it <- irunif(1, coun = 3)
  add(step(it), step(it))

  set.seed(1)
  p <- irunif(1, count = 2)
  q <- irunif(1, count = 1)
  add(step(p), step(q), step(p), step(q), step(p))

  set.seed(1)
  base <- irunif(1, count = 1)
  same <- if (identical(base, iter(base))) "SAME" else "DIFF"
  add(same, step(base), step(base))

  set.seed(1)
  it <- irunif(1, count = c(1))
  add(step(it), step(it))

  set.seed(1)
  it <- irunif(1, count = 1)
  add(step(it), step(it), step(it))

  paste(parts, collapse = "|")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
