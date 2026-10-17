.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

MATCH <- FALSE

esc <- function(x) {
  x <- enc2utf8(x)
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\t", "\\t", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

atom <- function(x) {
  if (length(x) != 1) stop("atom length")
  if (is.character(x)) {
    if (is.na(x)) "null" else esc(x)
  } else if (is.logical(x)) {
    if (is.na(x)) "null" else if (isTRUE(x)) "true" else "false"
  } else if (is.numeric(x)) {
    if (is.na(x)) "null" else if (is.integer(x)) as.character(x) else sprintf("%.17g", x)
  } else {
    stop("atom type")
  }
}

encode_matrix <- function(m) {
  if (nrow(m) == 0) {
    rows <- "[]"
  } else {
    lines <- lapply(seq_len(nrow(m)), function(i) {
      if (ncol(m) == 0) return("[]")
      cells <- vapply(seq_len(ncol(m)), function(j) atom(m[i, j]), "")
      paste0("[", paste(cells, collapse = ","), "]")
    })
    rows <- paste0("[", paste(lines, collapse = ","), "]")
  }
  if (!MATCH) return(rows)
  cn <- colnames(m)
  if (is.null(cn)) {
    cnj <- "null"
  } else if (length(cn) == 0) {
    cnj <- "[]"
  } else {
    cnj <- paste0("[", paste(vapply(cn, esc, ""), collapse = ","), "]")
  }
  paste0("{\"colnames\":", cnj, ",\"ncol\":", ncol(m), ",\"rows\":", rows, "}")
}

encode <- function(x) {
  if (is.null(x)) return("null")
  if (is.matrix(x)) return(encode_matrix(x))
  if (is.list(x)) {
    nms <- names(x)
    if (is.null(nms)) {
      if (length(x) == 0) return("[]")
      parts <- vapply(seq_along(x), function(i) encode(x[[i]]), "")
      return(paste0("[", paste(parts, collapse = ","), "]"))
    }
    parts <- vapply(seq_along(x), function(i) {
      paste0(esc(nms[[i]]), ":", encode(x[[i]]))
    }, "")
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) atom(x[[i]]), ""), collapse = ","), "]")
}

shopping_list <- c("apples x4", "bag of flour", "bag of sugar", "milk x2")
example <- capture.output(print(str_extract(shopping_list, "([a-z]+) of ([a-z]+)", group = 1)))
out_path <- "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_extract-r.txt"
dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
writeLines(example, out_path)

one <- function() {
  shopping <- rep(c("apples x4", "bag of flour", "bag of sugar", "milk x2", NA_character_, ""), 70)
  list(
    digit = str_extract(shopping, "\\d"),
    word = str_extract(shopping, "[a-z]+"),
    group1 = str_extract(shopping, "([a-z]+) of ([a-z]+)", group = 1),
    group2 = str_extract(shopping, "([a-z]+) of ([a-z]+)", group = 2),
    fixed = str_extract(rep(c("x.x", "ab"), 40), fixed(".")),
    coll = str_extract(c("\u0131", "I"), coll("I", ignore_case = TRUE, locale = "tr")),
    empty = str_extract(rep("a b c", 20), ""),
    bound = str_extract(rep("a b c", 40), boundary("word")),
    casefold = str_extract(rep(c("Cat", "dog"), 20), regex("[a-z]+", ignore_case = TRUE)),
    both = str_extract("abc", "(a)", group = c(1, 0)),
    empty_in = str_extract(character(), "a")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0("{\"value\":", encode(value), ",\"median_ms\":", sprintf("%.17g", median(elapsed) * 1000), "}\n"))
