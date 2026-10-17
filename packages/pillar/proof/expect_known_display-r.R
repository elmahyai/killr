.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cli.unicode = TRUE)
suppressPackageStartupMessages(library(pillar))

json_str <- function(s) {
  s <- enc2utf8(as.character(s))
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  paste0('"', s, '"')
}

df <- structure(
  data.frame(
    a = 1:3,
    b = c("x", "yy", "zzz"),
    c = c(TRUE, FALSE, NA),
    stringsAsFactors = FALSE
  ),
  class = c("tbl", "data.frame")
)

one <- function() {
  tryCatch(expect_known_display(), error = function(e) conditionMessage(e))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_str(value), median(elapsed) * 1000))
