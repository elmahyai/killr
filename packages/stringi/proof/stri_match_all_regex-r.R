.libPaths(c(path.expand("~/R/library"), .libPaths()))
stringi_189 <- function(lib) {
  desc <- file.path(lib, "stringi", "DESCRIPTION")
  if (!file.exists(desc)) return(FALSE)
  any(grepl("^Version:[[:space:]]*1\\.8\\.9[[:space:]]*$", readLines(desc, warn = FALSE)))
}
good <- Filter(stringi_189, .libPaths())
if (length(good)) .libPaths(unique(c(good[[1]], .libPaths())))
suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

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
  if (is.character(x)) {
    if (is.na(x)) "null" else esc(x)
  } else if (is.logical(x)) {
    if (is.na(x)) "null" else if (isTRUE(x)) "true" else "false"
  } else if (is.numeric(x)) {
    if (is.na(x)) "null" else as.character(x)
  } else {
    stop("atom")
  }
}

vec <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) atom(x[[i]]), ""), collapse = ","), "]")
}

encode <- function(x) {
  if (is.null(x)) return("null")
  if (is.matrix(x)) {
    if (nrow(x) == 0) return("[]")
    rows <- lapply(seq_len(nrow(x)), function(i) vec(x[i, ]))
    return(paste0("[", paste(rows, collapse = ","), "]"))
  }
  if (is.list(x)) {
    if (length(x) == 0) return("[]")
    parts <- vapply(seq_along(x), function(i) encode(x[[i]]), "")
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  vec(x)
}

one <- function() {
  base <- c("The 12 foxes and 7 dogs ran.", "no digits here", "99", NA_character_, "", "a😀b12")
  texts <- rep(base, 70)
  stri_match_all_regex(texts, "(\\d+)")
}

stopifnot(identical(unname(c(stri_match_all_regex("a=b", "([a-z])=([a-z])")[[1]])), c("a=b", "a", "b")))
sentence <- 'stri_match_all_regex("a=b", "([a-z])=([a-z])") returns a=b, a, b.'
out <- '/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_match_all_regex-r.txt'
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(sentence, out)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encode(value), median(elapsed) * 1000))
