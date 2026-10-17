suppressPackageStartupMessages(library(pbapply))
stopifnot(packageVersion("pbapply") == "1.7-5")
stopifnot(packageDescription("pbapply")$Version == "1.7-5")

json_str <- function(s) {
  chars <- strsplit(enc2utf8(s), "")[[1]]
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

times <- list(
  NULL, 0, 0.4, 0.5, 0.6, 15, 59.5, 60, 65, 90.5, 119.5,
  3599, 3600, 6005, 86399, 86400, 86401, 90061, 1e6, 1e10,
  2147483647 * 86400, 2147483647 * 86400 - 1,
  -1, -15, -59.5, -60, -61, -3600, -86400, -90061, -1e10,
  Inf, -Inf
)

one <- function() vapply(times, getTimeAsString, "")

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(vapply(value, json_str, ""), collapse = ","),
  median(elapsed) * 1000
))
