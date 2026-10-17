.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))

json_str <- function(s) {
  bytes <- as.integer(charToRaw(enc2utf8(s)))
  parts <- character(length(bytes))
  for (i in seq_along(bytes)) {
    b <- bytes[[i]]
    parts[[i]] <- if (b == 34) paste0("\\", '"')
      else if (b == 92) paste0("\\", "\\")
      else if (b == 10) paste0("\\", "n")
      else if (b == 13) paste0("\\", "r")
      else if (b == 9) paste0("\\", "t")
      else if (b < 32 || b == 127) sprintf("\\u%04x", b)
      else intToUtf8(b)
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

json_cell <- function(x) {
  if (is.character(x) || is.factor(x)) {
    if (length(x) == 0 || is.na(x[[1]])) return("null")
    return(json_str(as.character(x[[1]])))
  }
  if (is.logical(x)) {
    if (length(x) == 0 || is.na(x[[1]])) return("null")
    return(if (isTRUE(x[[1]])) "true" else "false")
  }
  "null"
}

dir <- tempfile()
dir.create(dir)
writeLines(c(
  "Package: toydeps",
  "Version: 0.0.1",
  "Imports: remotes"
), file.path(dir, "DESCRIPTION"))

one <- function() {
  dev_package_deps(dir, repos = "https://cloud.r-project.org", type = "source")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

rows <- character(nrow(value))
for (i in seq_len(nrow(value))) {
  rows[[i]] <- paste0(
    '{"package":', json_str(value$package[[i]]),
    ',"installed":', json_cell(value$installed[[i]]),
    ',"available":', json_cell(value$available[[i]]),
    ',"diff":', format(value$diff[[i]], scientific = FALSE, trim = TRUE),
    ',"is_cran":', if (isTRUE(value$is_cran[[i]])) "true" else "false",
    "}"
  )
}
body <- if (length(rows) == 0) "" else paste(rows, collapse = ",")
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', body, median(elapsed) * 1000))
