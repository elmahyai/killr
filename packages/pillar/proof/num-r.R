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
    encode(num(c(1, 2.5, NA))),
    encode(num(c(1, 2), sigfig = 4, label = "kg")),
    encode(num(1, digits = 2, notation = "sci")),
    encode(num(1, notation = "si", fixed_exponent = -3, scale = 10, label = "m")),
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
