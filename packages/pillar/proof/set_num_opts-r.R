.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(pillar, lib.loc = "/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5"))

json_str <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}

atom <- function(v) {
  if (is.na(v)) "NA" else as.character(v)
}

encode <- function(x) {
  paste(
    paste(vapply(as.vector(x), atom, ""), collapse = ","),
    typeof(x),
    paste(class(x), collapse = "/"),
    format(attr(x, "pillar", exact = TRUE)),
    vctrs::vec_ptype_abbr(x),
    sep = ";"
  )
}

one <- function() {
  paste(
    encode(set_num_opts(c(1, 2), sigfig = 2)),
    encode(set_num_opts(1:2, sigfig = 2)),
    sep = " || "
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
  '{"value":%s,"median_ms":%.17g}\n',
  json_str(value),
  median(elapsed) * 1000
))
