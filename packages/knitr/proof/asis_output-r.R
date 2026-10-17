suppressPackageStartupMessages(library(knitr))
stopifnot(as.character(packageVersion("knitr")) == "1.52")
json_str <- function(s) {
  if (length(s) != 1 || is.na(s)) return("null")
  chars <- strsplit(enc2utf8(s), "", fixed = TRUE)[[1]]
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- utf8ToInt(chars[[i]])
    parts[[i]] <- if (cp == 34) paste0("\\", '"')
      else if (cp == 92) paste0("\\", "\\")
      else if (cp == 10) paste0("\\", "n")
      else if (cp == 13) paste0("\\", "r")
      else if (cp == 9) paste0("\\", "t")
      else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
      else chars[[i]]
  }
  paste0('"', paste(parts, collapse = ""), '"')
}
json_vec <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(x, json_str, character(1)), collapse = ","), "]")
}
one <- function() asis_output("hello", meta = list(id = "fig1"), cacheable = FALSE)
value <- one()
cls <- attr(value, "class", exact = TRUE)
meta <- attr(value, "knit_meta", exact = TRUE)
cache <- attr(value, "knit_cacheable", exact = TRUE)
cache_word <- if (isTRUE(cache)) "TRUE" else if (identical(cache, FALSE)) "FALSE" else "NA"
meta_parts <- character(length(meta))
for (i in seq_along(meta)) {
  meta_parts[[i]] <- paste0(json_str(names(meta)[[i]]), ":", json_str(as.character(meta[[i]])))
}
cache_json <- if (identical(cache, FALSE)) "false" else if (isTRUE(cache)) "true" else "null"
writeLines(
  paste0(
    "asis_output(\"hello\", meta = list(id = \"fig1\"), cacheable = FALSE) returns ",
    as.vector(value),
    " with class ",
    paste(cls, collapse = " "),
    ", meta id ",
    meta[["id"]],
    ", and cacheable ",
    cache_word,
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/asis_output-r.txt"
)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":{"typeof":%s,"value":%s,"attributes":%s,"class":%s,"knit_meta":{%s},"knit_cacheable":%s},"median_ms":%.17g}\n',
  json_str(typeof(value)),
  json_str(as.vector(value)),
  json_vec(names(attributes(value))),
  json_vec(cls),
  paste(meta_parts, collapse = ","),
  cache_json,
  median(elapsed) * 1000
))
