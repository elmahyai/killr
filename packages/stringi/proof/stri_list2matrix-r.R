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


even <- list(c("a", "b"), c("c", "d"), c("e", "f"))
uneven <- list("a", c("b", "c"))
big <- lapply(1:2000, function(i) {
  if (i %% 2 == 0) c(paste0("a", i), paste0("b", i)) else c(paste0("a", i), NA_character_)
})
one <- function() {
  list(
    even = stri_list2matrix(even),
    even_byrow = stri_list2matrix(even, byrow = TRUE),
    uneven = stri_list2matrix(uneven),
    uneven_fill = stri_list2matrix(uneven, fill = ""),
    uneven_nmin = stri_list2matrix(uneven, fill = "", n_min = 5),
    byrow_nmin = stri_list2matrix(uneven, byrow = TRUE, fill = "", n_min = 5),
    by_row = stri_list2matrix(list(c("a", "b"), c("c", "d")), byrow = FALSE, by_row = TRUE),
    by_row_off = stri_list2matrix(list(c("a", "b"), c("c", "d")), byrow = TRUE, by_row = FALSE),
    numbers = stri_list2matrix(list(1:2, c(TRUE, FALSE))),
    pad = stri_list2matrix(list(c("a", "b"), "c"), n_min = 4, fill = "*"),
    empty_nmin = stri_list2matrix(list(), n_min = 2),
    empty_byrow = stri_list2matrix(list(), n_min = 2, byrow = TRUE),
    empty_cols = stri_list2matrix(list(character(0), character(0))),
    big = stri_list2matrix(big, fill = "*", n_min = 3),
    big_byrow = stri_list2matrix(big, byrow = TRUE, fill = "*", n_min = 3)
  )
}

dir.create("/home/ahmed/killr_projects/killr/packages/stringi/docs/output", recursive = TRUE, showWarnings = FALSE)
writeLines("stri_list2matrix(list(c(\"a\", \"b\"), c(\"c\", \"d\"), c(\"e\", \"f\"))) returns rows (a, c, e) and (b, d, f).", "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_list2matrix-r.txt", useBytes = TRUE)
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
