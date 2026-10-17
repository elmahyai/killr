.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
ver <- as.character(packageVersion("stringi"))
if (ver != "1.8.9") stop(paste("expected stringi 1.8.9, got", ver))

json_chars <- function(x) {
  if (length(x) == 0) return("[]")
  shown <- ifelse(is.na(x), NA_character_, enc2utf8(x))
  shown <- gsub("\\", "\\\\", shown, fixed = TRUE)
  shown <- gsub('"', '\\"', shown, fixed = TRUE)
  parts <- ifelse(is.na(x), "null", paste0('"', shown, '"'))
  paste0("[", paste(parts, collapse = ","), "]")
}

json_value <- function(x) {
  if (is.list(x) && !is.null(names(x))) {
    keys <- names(x)
    parts <- character(length(x))
    for (i in seq_along(x)) {
      parts[[i]] <- paste0('"', keys[[i]], '":', json_chars(x[[i]]))
    }
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  json_chars(x)
}

items <- c(
  list(c("a", NA), character(0), c("", "b")),
  lapply(1:4000, function(i) c("k", as.character(i)))
)
one <- function() list(
  rows = stri_c_list(items, sep = "-"),
  collapsed = stri_c_list(items, sep = "-", collapse = "|")
)

dir.create("/home/ahmed/killr_projects/killr/packages/stringi/docs/output", recursive = TRUE, showWarnings = FALSE)
writeLines("stri_c_list(list(c(\"a\", \"b\"), character(0), c(\"c\", NA)), sep = \"-\") returns c(\"a-b\", NA).", "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_c_list-r.txt", useBytes = TRUE)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(
  '{"value":', json_value(value),
  ',"median_ms":', sprintf("%.17g", median(elapsed) * 1000),
  '}\n'
))
