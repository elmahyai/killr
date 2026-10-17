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

fmt <- function(v) {
  if (length(v) == 0) return("")
  if (length(v) == 1) {
    if (is.na(v)) return("NA")
    if (is.logical(v)) return(if (v) "TRUE" else "FALSE")
    if (is.character(v)) return(json_str(v))
    if (is.complex(v)) {
      if (is.na(v)) return("NA")
      return(paste0(format(Re(v), digits = 16), "+", format(Im(v), digits = 16), "i"))
    }
    return(format(v, digits = 16))
  }
  paste(vapply(v, function(item) fmt(item), ""), collapse = ";")
}

flat <- function(x) fmt(x)

one <- function() {
  chr_vec <- c("a", "d", "d", "h", "h", NA, NA)
  num_vec <- c(2, 3, 3, 4, 4, NA, NA)
  tie_num <- c(1, 1, 2, 2)
  c(
    flat(stat_mode(chr_vec)),
    flat(stat_mode(chr_vec, na.rm = FALSE)),
    flat(stat_mode(chr_vec, na.rm = FALSE, ties = "first")),
    flat(stat_mode(chr_vec, na.rm = FALSE, ties = "last")),
    flat(stat_mode(num_vec)),
    flat(stat_mode(num_vec, na.rm = FALSE)),
    flat(stat_mode(num_vec, na.rm = FALSE, ties = "first")),
    flat(stat_mode(num_vec, na.rm = FALSE, ties = "last")),
    flat(stat_mode(tie_num, ties = "missing")),
    flat(stat_mode(tie_num, ties = "first")),
    flat(stat_mode(tie_num, ties = "last")),
    flat(stat_mode(tie_num, ties = "all")),
    flat(stat_mode(c(TRUE, TRUE))),
    flat(stat_mode(c(FALSE, FALSE, TRUE, TRUE))),
    flat(stat_mode(c(NA_real_))),
    flat(stat_mode(2)),
    flat(stat_mode(NA)),
    flat(stat_mode("a")),
    flat(stat_mode(c(NA, NA, NA))),
    flat(stat_mode(double(0))),
    flat(stat_mode(complex(0))),
    flat(stat_mode(integer(0))),
    flat(stat_mode(character(0))),
    flat(stat_mode(c(1L, 2L, 2L))),
    flat(stat_mode(c(1 + 1i, 2 + 2i, 2 + 2i)))
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
