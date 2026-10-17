.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

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

flat <- function(x) {
  fmt <- function(v) {
    if (is.na(v)) return("NA")
    if (is.complex(v)) return(sprintf("%.16g+%.16gi", Re(v), Im(v)))
    if (is.logical(v)) return(if (v) "TRUE" else "FALSE")
    if (is.character(v)) return(json_str(v))
    sprintf("%.16g", as.numeric(v))
  }
  if (is.matrix(x)) {
    x <- as.vector(x)
  }
  if (length(x) == 0) {
    return(character(0))
  }
  vapply(x, fmt, "")
}

one <- function() {
  x <- c(1, 2, 3, NA, 6, 7, 8, NA, NA)
  c(
    flat(na.replace(x, 999)),
    flat(na.replace(x, median, na.rm = TRUE)),
    flat(na.replace(c(1L, 2L, NA, 4L), 0L)),
    flat(na.replace(c(TRUE, NA, FALSE), FALSE)),
    flat(na.replace(c("a", NA, "c"), "999")),
    flat(na.replace(matrix(c(1, NA, 3, 4), 2, 2), 0)),
    flat(na.replace(c(1 + 1i, NA), 0)),
    flat(na.replace(c(1, NaN, 3), 0))
  )
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(paste(value, collapse = "|")), median(elapsed) * 1000))
