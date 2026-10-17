suppressPackageStartupMessages(library(stringi))
ver <- as.character(packageVersion("stringi"))
if (ver != "1.8.9") stop(paste("expected stringi 1.8.9, got", ver))

json_string <- function(s) {
  cps <- utf8ToInt(s)
  if (length(cps) == 0) return("\"\"")
  parts <- character(length(cps))
  for (i in seq_along(cps)) {
    cp <- cps[[i]]
    if (cp == 34) parts[[i]] <- "\\\""
    else if (cp == 92) parts[[i]] <- "\\\\"
    else if (cp == 8) parts[[i]] <- "\\b"
    else if (cp == 12) parts[[i]] <- "\\f"
    else if (cp == 10) parts[[i]] <- "\\n"
    else if (cp == 13) parts[[i]] <- "\\r"
    else if (cp == 9) parts[[i]] <- "\\t"
    else if (cp < 32) parts[[i]] <- sprintf("\\u%04x", as.integer(cp))
    else parts[[i]] <- intToUtf8(cp)
  }
  paste0("\"", paste(parts, collapse = ""), "\"")
}

json_chars <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- character(length(x))
  for (i in seq_along(x)) {
    if (is.na(x[[i]])) parts[[i]] <- "null" else parts[[i]] <- json_string(x[[i]])
  }
  paste0("[", paste(parts, collapse = ","), "]")
}

json_rows <- function(m) {
  nr <- nrow(m)
  nc <- ncol(m)
  if (nr == 0) return("[]")
  rows <- character(nr)
  for (i in seq_len(nr)) {
    if (nc == 0) rows[[i]] <- "[]" else rows[[i]] <- json_chars(m[i, ])
  }
  paste0("[", paste(rows, collapse = ","), "]")
}

json_value <- function(x) {
  if (is.matrix(x)) return(json_rows(x))
  if (is.list(x)) {
    keys <- names(x)
    parts <- character(length(x))
    for (i in seq_along(x)) {
      parts[[i]] <- paste0(json_string(keys[[i]]), ":", json_value(x[[i]]))
    }
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  if (is.character(x)) return(json_chars(x))
  stop(paste("unsupported", paste(class(x), collapse = ",")))
}


long <- rep(c("test", NA), 4000)
one <- function() {
  list(
    default = stri_replace_na(c("test", NA)),
    xx = stri_replace_na(c("test", NA, ""), "xx"),
    blank = stri_replace_na(c("test", NA), ""),
    na_repl = stri_replace_na(c("a", NA), NA),
    first = suppressWarnings(stri_replace_na(c("a", NA), c("x", "y"))),
    long = stri_replace_na(long, "zz")
  )
}

dir.create("/home/ahmed/killr_projects/killr/packages/stringi/docs/output", recursive = TRUE, showWarnings = FALSE)
writeLines("stri_replace_na(c(\"test\", NA)) returns \"test\" and \"NA\".", "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_replace_na-r.txt", useBytes = TRUE)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(
  "{\"value\":", json_value(value),
  ",\"median_ms\":", sprintf("%.17g", median(elapsed) * 1000),
  "}\n"
))
