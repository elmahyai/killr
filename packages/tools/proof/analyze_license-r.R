suppressPackageStartupMessages(library(tools))

summarize <- function(r) {
  fc <- function(v) {
    if (is.null(v)) return("NULL")
    if (length(v) == 1L && is.na(v)) return("NA")
    if (is.logical(v)) return(if (v) "T" else "F")
    if (is.character(v)) return(paste(v, collapse = "\1"))
    if (is.data.frame(v)) {
      return(paste(vapply(seq_len(nrow(v)), function(i) {
        paste0(v$components[i], ",", if (isTRUE(v$extensible[i])) "T" else "F")
      }, ""), collapse = "\3"))
    }
    if (is.list(v)) return(paste(vapply(v, fc, ""), collapse = "\2"))
    "?"
  }
  paste(vapply(r, fc, ""), collapse = "|")
}

one <- function() {
  specs <- c(
    "GPL-2",
    "LGPL (>= 2.0, < 3) | Mozilla Public License",
    "GPL-2 | file LICENCE",
    "GPL (>= 2) | BSD_3_clause + file LICENSE",
    "Artistic-2.0 | AGPL-3 + file LICENSE"
  )
  paste0(paste(vapply(specs, function(x) summarize(analyze_license(x)), ""), collapse = "\n"), "\n")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
