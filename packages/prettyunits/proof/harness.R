# Shared proof harness for the R side of prettyunits 1.2.0.
#
# Each proof script sources this file, defines one() that returns the R
# result for its case, and calls run_proof(name, one). The untimed call
# is one(); then 20 timed calls are made with Sys.time(). The median in
# milliseconds and the encoded result go to docs/output/<name>-r.txt.

.proof_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- sub("^--file=", "", args[grepl("^--file=", args)])
  normalizePath(dirname(file_arg[1]))
})

.json_str <- function(s) {
  s <- gsub("\\\\", "\\\\\\\\", s)
  s <- gsub("\"", "\\\\\"", s)
  paste0("\"", s, "\"")
}

# Numbers: NA -> null, NaN and Inf as tagged objects, otherwise %.17g.
.enc_num <- function(v) {
  if (is.na(v) && !is.nan(v)) return("null")
  if (is.nan(v)) return("{\"special\":\"NaN\"}")
  if (is.infinite(v)) {
    return(if (v > 0) "{\"special\":\"Inf\"}" else "{\"special\":\"-Inf\"}")
  }
  sprintf("%.17g", v)
}

# Encodes NULL, atomic vectors (length one as a scalar, otherwise an array),
# lists (arrays), and named lists or data frames (objects).
enc <- function(x) {
  if (is.null(x)) return("null")
  if (is.factor(x)) x <- as.character(x)
  if (is.list(x)) {
    items <- vapply(seq_along(x), function(i) enc(x[[i]]), "")
    if (!is.null(names(x))) {
      keys <- vapply(names(x), .json_str, "")
      return(paste0("{", paste0(keys, ":", items, collapse = ","), "}"))
    }
    return(paste0("[", paste(items, collapse = ","), "]"))
  }
  if (is.character(x)) {
    items <- vapply(x, function(s) if (is.na(s)) "null" else .json_str(s), "",
                    USE.NAMES = FALSE)
  } else if (is.logical(x)) {
    items <- vapply(x, function(b) if (is.na(b)) "null" else if (b) "true" else "false",
                    "", USE.NAMES = FALSE)
  } else {
    items <- vapply(as.numeric(x), .enc_num, "", USE.NAMES = FALSE)
  }
  if (length(x) == 1) return(items)
  paste0("[", paste(items, collapse = ","), "]")
}

# Error marker shared with the Python side.
try_val <- function(expr) tryCatch(expr, error = function(e) "__error__")

run_proof <- function(name, one) {
  value <- one()
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    one()
    elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
  }
  out <- file.path(.proof_dir, "..", "docs", "output", paste0(name, "-r.txt"))
  writeLines(
    c(sprintf("median_ms %.17g", median(elapsed) * 1000),
      paste0("result ", enc(value))),
    out
  )
  cat(readLines(out), sep = "\n")
  invisible(value)
}
