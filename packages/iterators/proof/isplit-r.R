suppressPackageStartupMessages(library(iterators))

fmt_double <- function(v) {
  if (is.na(v) && !is.nan(v)) return("NA")
  if (is.nan(v)) return("NaN")
  if (is.infinite(v)) return(if (v > 0) "Inf" else "-Inf")
  sprintf("%a", v)
}

fmt_atomic <- function(x) {
  if (is.null(x)) return("NULL")
  kind <- typeof(x)
  if (length(x) == 0) {
    body <- ""
  } else if (kind == "character") {
    body <- paste(ifelse(is.na(x), "NA", x), collapse = ",")
  } else if (kind == "logical") {
    body <- paste(ifelse(is.na(x), "NA", ifelse(x, "TRUE", "FALSE")), collapse = ",")
  } else if (kind == "integer") {
    shown <- character(length(x))
    for (i in seq_along(x)) {
      shown[[i]] <- if (is.na(x[[i]])) "NA" else sprintf("%d", x[[i]])
    }
    body <- paste(shown, collapse = ",")
  } else if (kind == "double") {
    body <- paste(vapply(x, fmt_double, ""), collapse = ",")
  } else {
    body <- paste(as.character(x), collapse = ",")
  }
  out <- paste0(kind, ":", body)
  if (!is.null(names(x))) {
    nms <- names(x)
    nms[is.na(nms)] <- "NA"
    out <- paste0(out, ";names=", paste(nms, collapse = ","))
  }
  out
}

fmt_factor <- function(f) {
  if (length(f) == 0) {
    codes <- ""
  } else {
    codes <- paste(ifelse(is.na(f), "NA", as.character(as.integer(f))), collapse = ",")
  }
  paste0("factor:", codes, "/", paste(levels(f), collapse = ","))
}

fmt_df <- function(df) {
  cols <- character()
  for (nm in names(df)) {
    cols <- c(cols, paste0(nm, "=", fmt_atomic(df[[nm]])))
  }
  paste0("df:", paste(row.names(df), collapse = ","), "|", paste(cols, collapse = "|"))
}

fmt_list <- function(x) {
  nms <- names(x)
  parts <- character()
  if (length(x) == 0) return("list:")
  for (i in seq_along(x)) {
    body <- fmt_value(x[[i]])
    if (is.null(nms)) {
      parts <- c(parts, paste0("[", body, "]"))
    } else {
      nm <- nms[[i]]
      if (is.na(nm)) nm <- "NA"
      parts <- c(parts, paste0("[", nm, "=", body, "]"))
    }
  }
  paste0("list:", paste(parts, collapse = ""))
}

fmt_value <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.factor(x)) return(fmt_factor(x))
  if (is.data.frame(x)) return(fmt_df(x))
  if (is.list(x)) return(fmt_list(x))
  fmt_atomic(x)
}

fmt_group <- function(g) {
  key <- g$key
  bodies <- vapply(key, fmt_atomic, "")
  if (is.null(names(key))) {
    k <- paste0("[", bodies, "]", collapse = "")
  } else {
    nms <- names(key)
    nms[is.na(nms)] <- "NA"
    k <- paste0("[", nms, "=", bodies, "]", collapse = "")
  }
  paste0("V(", fmt_value(g$value), ")K(", k, ")")
}

take <- function(it, k = 24) {
  out <- character()
  for (i in seq_len(k)) {
    w <- character()
    hit <- withCallingHandlers(
      tryCatch(list(v = nextElem(it)), error = function(e) list(e = conditionMessage(e))),
      warning = function(w0) {
        w <<- c(w, conditionMessage(w0))
        invokeRestart("muffleWarning")
      }
    )
    if (length(w)) out <- c(out, paste0("W:", w))
    if (!is.null(hit$e)) {
      out <- c(out, hit$e)
      break
    }
    out <- c(out, fmt_group(hit$v))
  }
  out
}

err <- function(expr) {
  tryCatch({
    force(expr)
    "OK"
  }, error = function(e) conditionMessage(e))
}

step <- function(it) {
  hit <- tryCatch(list(v = nextElem(it)), error = function(e) list(e = conditionMessage(e)))
  if (!is.null(hit$e)) hit$e else fmt_group(hit$v)
}

one <- function() {
  x <- c(10, 20, 30, 40, 50)
  f <- factor(c("b", "a", "b", "a", "b"), levels = c("b", "a", "c"))
  p <- isplit(c(10L, 20L, 30L, 40L), c("a", "b", "a", "b"))
  q <- isplit(c(10L, 20L, 30L, 40L), c("a", "b", "a", "b"))
  base <- isplit(c(5L, 6L), c("a", "b"))
  same <- if (identical(base, iter(base))) "SAME" else "DIFF"
  df <- data.frame(
    p = c(1L, 2L, 3L, 4L),
    q = c("w", "x", "w", "x"),
    row.names = c("r1", "r2", "r3", "r4"),
    stringsAsFactors = FALSE
  )
  ff <- factor(c("x", "w", "x", "w"), levels = c("w", "x", "y"))
  narrow <- data.frame(p = c(1L, 2L))
  paste(c(
    take(isplit(x, f, drop = FALSE)),
    take(isplit(x, f, drop = TRUE)),
    take(isplit(c(1, 2, 3, 4), c("b", "a", "b", "a"))),
    take(isplit(c(9L, 8L, 7L, 6L), c(1L, NA, 2L, 1L))),
    take(isplit(c(9, 8, 7, 6, 5), c(1, NA, NaN, 1, 2))),
    take(isplit(c(9L, 8L, 7L, 6L), c(TRUE, FALSE, NA, TRUE))),
    take(isplit(c(9, 8, 7), c(-0, 0, 1))),
    take(isplit(c(1, 2, 3), c(Inf, -Inf, Inf))),
    take(isplit(c(7, 8, 9), c(10, 2, 10))),
    take(isplit(1:6, c("b", "A", "a", "B", "10", "2"))),
    take(isplit(c(7, 8, 9), c(1 + 2^-52, 1, 2))),
    take(isplit(c(a = 1L, b = 2L, c = 3L, d = 4L), c("z", "y", "z", "y"))),
    take(isplit(list(a = 10L, b = 20L, c = 30L, d = 40L), c("u", "v", "u", "v"))),
    take(isplit(matrix(1:6, nrow = 2), c("a", "b"))),
    take(isplit(c(10, 20, 30, 40), matrix(c("a", "b", "a", "b"), nrow = 2))),
    take(isplit(factor(c("p", "q", "p", "q")), c("a", "b", "a", "b"))),
    take(isplit(x, list(g = c("u", "u", "v", "v", "u"), h = c(2, 1, 2, 1, 2)))),
    take(isplit(1:4, list(c("a", "b", "a", "b"), g = c(1, 1, 2, 2)))),
    take(isplit(c(1, 2, 3, 4), data.frame(a = c("u", "u", "v", "v"), b = c(1, 2, 1, 2)))),
    take(isplit(df, df$q)),
    take(isplit(df, ff, drop = FALSE)),
    take(isplit(df, ff, drop = TRUE)),
    take(isplit(narrow, c("a", "b", "a", "a"))),
    take(isplit(numeric(0), factor(c("a", "b")))),
    take(isplit(integer(0), factor(character(0), levels = c("a", "b")))),
    take(isplit(NULL, "a")),
    take(isplit(1:2, c("a", "b", "a"))),
    take(isplit(1:3, c("a", "b"))),
    take(isplit(1:4, list(c("a", "b", "a", "b"), c("u", "v")))),
    take(isplit(1:6, list(c("a", "b", "a"), c("u", "v", "w", "x")))),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), drop = 0)),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), drop = 2)),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), drop = NA)),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), drop = logical(0))),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), drop = "TRUE")),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), drop = c(TRUE, FALSE))),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), dr = TRUE)),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), TRUE)),
    take(isplit(c(1L, 2L), factor(c("a", "a"), levels = c("a", "b")), foo = 1)),
    take(isplit(1:3, NULL)),
    take(isplit(1:3, c(NA, NA, NA))),
    take(isplit(1:3, character(0))),
    take(isplit(f = c("a", "b"))),
    step(p), step(q), step(p),
    same,
    take(base),
    err(isplit(1:3, list())),
    err(isplit(1:3)),
    err(isplit()),
    err(isplit(c(1L, 2L), c("a", "b"), d = 1, dr = 2))
  ), collapse = "||")
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
