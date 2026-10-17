.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

writeLines(
  "stri_sub_all_replace(\"hello\", from = 0, length = 3, replacement = \"Q\") returns Qlo.",
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_sub_all_replace-r.txt"
)

json_chars <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- ifelse(is.na(x), "null", paste0("\"", x, "\""))
  paste0("[", paste(parts, collapse = ","), "]")
}

one <- function() {
  list(
    from0 = stri_sub_all_replace("hello", from = 0, length = 3, replacement = "Q"),
    neg = stri_sub_all_replace("hello", from = 2, length = -3, replacement = "XX"),
    pieces = stri_sub_all_replace("a b c", from = c(1, 3, 5), to = c(1, 3, 5), replacement = c("A", "B", "C")),
    omit = stri_sub_all_replace("abcdef", from = c(1, NA), to = c(2, 4), replacement = c("A", "B"), omit_na = TRUE),
    keep_na = stri_sub_all_replace("abcdef", from = c(1, NA), to = c(2, 4), replacement = c("A", "B"))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":{\"from0\":%s,\"neg\":%s,\"pieces\":%s,\"omit\":%s,\"keep_na\":%s},\"median_ms\":%.17g}\n",
  json_chars(value$from0),
  json_chars(value$neg),
  json_chars(value$pieces),
  json_chars(value$omit),
  json_chars(value$keep_na),
  median(elapsed) * 1000
))
